using System.Threading.Channels;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using TraderCockpit.MarketData.Dhan;
using TraderCockpit.MarketData.Domain;
using TraderCockpit.MarketData.Repositories;

namespace TraderCockpit.MarketData.Services;

/// <summary>
/// Long-running hosted service that drains the <see cref="Channel{SyncRequest}"/>
/// and processes each item with bounded parallelism.
///
/// For each <see cref="SyncRequest"/> it:
///   1. Splits the date range into 30-day chunks (Dhan API limit).
///   2. Calls <see cref="DhanClient"/> for each chunk.
///   3. Bulk-inserts the result via <see cref="IPriceDataRepository.BulkInsertAsync"/>.
///   4. Updates the <c>sync_jobs</c> row to Completed or Failed.
/// </summary>
public sealed class IngestionBackgroundService(
    Channel<SyncRequest>        syncChannel,
    DhanClient                  dhanClient,
    IPriceDataRepository        priceDataRepo,
    ISyncJobRepository          syncJobRepo,
    IOptions<DhanOptions>       options,
    ILogger<IngestionBackgroundService> logger) : BackgroundService
{
    private static readonly TimeSpan BatchWindow = TimeSpan.FromDays(30);

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        logger.LogInformation("IngestionBackgroundService started.");

        var parallelOptions = new ParallelOptions
        {
            MaxDegreeOfParallelism = options.Value.MaxConcurrency,
            CancellationToken      = stoppingToken,
        };

        await Parallel.ForEachAsync(
            syncChannel.Reader.ReadAllAsync(stoppingToken),
            parallelOptions,
            ProcessAsync);
    }

    private async ValueTask ProcessAsync(SyncRequest req, CancellationToken ct)
    {
        await syncJobRepo.UpdateInProgressAsync(req.JobId, ct);
        logger.LogInformation(
            "Starting sync [{JobId}] {Symbol} {From:yyyy-MM-dd}→{To:yyyy-MM-dd}",
            req.JobId, req.Symbol, req.FromTime, req.ToTime);

        int totalBars = 0;

        try
        {
            var cursor = req.FromTime.Date;

            while (cursor <= req.ToTime && !ct.IsCancellationRequested)
            {
                var batchEnd = cursor.Add(BatchWindow);
                if (batchEnd > req.ToTime) batchEnd = req.ToTime;

                var bars = await dhanClient.GetIntradayAsync(
                    req.DhanSecurityId, req.ExchangeSegment, cursor, batchEnd, ct);

                if (bars.Count > 0)
                {
                    await priceDataRepo.BulkInsertAsync(req.SymbolId, bars, ct);
                    totalBars += bars.Count;
                    logger.LogDebug(
                        "[{Symbol}] inserted {Count} bars for {From:yyyy-MM-dd}→{To:yyyy-MM-dd}",
                        req.Symbol, bars.Count, cursor, batchEnd);
                }

                cursor = batchEnd.AddDays(1);

                // Respect per-worker rate limit between batches.
                await Task.Delay(options.Value.DelayBetweenCallsMs, ct);
            }

            await syncJobRepo.UpdateCompletedAsync(req.JobId, totalBars, ct);
            logger.LogInformation(
                "Completed sync [{JobId}] {Symbol}: {TotalBars} bars ingested.",
                req.JobId, req.Symbol, totalBars);
        }
        catch (Exception ex) when (ex is not OperationCanceledException)
        {
            logger.LogError(ex, "Sync failed [{JobId}] {Symbol}", req.JobId, req.Symbol);
            await syncJobRepo.UpdateFailedAsync(req.JobId, ex.Message, ct);
        }
    }
}
