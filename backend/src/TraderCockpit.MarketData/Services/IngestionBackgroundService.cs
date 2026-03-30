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
/// and ingests historical OHLCV bars into TimescaleDB.
/// </summary>
/// <remarks>
/// <para>
/// Parallelism is bounded by <see cref="DhanOptions.MaxConcurrency"/>; a global
/// token-bucket rate limiter inside <see cref="DhanClient"/> ensures the Dhan API
/// rate limit is never exceeded regardless of concurrency.
/// </para>
/// <para>
/// Each <see cref="SyncRequest"/> is processed by <see cref="ProcessAsync"/>, which
/// delegates the batch-iteration loop to <see cref="IngestBatchesAsync"/> so that
/// job lifecycle management (InProgress → Completed | Failed) stays in one place.
/// </para>
/// </remarks>
public sealed class IngestionBackgroundService(
    Channel<SyncRequest>                syncChannel,
    DhanClient                          dhanClient,
    IPriceDataRepository                priceDataRepo,
    ISyncJobRepository                  syncJobRepo,
    IOptions<DhanOptions>               options,
    ILogger<IngestionBackgroundService> logger) : BackgroundService
{
    /// <summary>
    /// Maximum date span sent in a single Dhan API call.
    /// Dhan's intraday endpoint caps requests at approximately 90 days.
    /// </summary>
    private static readonly TimeSpan BatchWindow = TimeSpan.FromDays(90);

    /// <summary>
    /// When no data exists yet for a symbol (DH-905 from the start of the backfill),
    /// jump forward by this amount to locate the listing date faster.
    /// </summary>
    private static readonly TimeSpan ListingSearchStep = TimeSpan.FromDays(30 * 6); // ~6 months

    // ── BackgroundService entry-point ─────────────────────────────────────────

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        logger.LogInformation("IngestionBackgroundService started.");

        await Parallel.ForEachAsync(
            syncChannel.Reader.ReadAllAsync(stoppingToken),
            new ParallelOptions
            {
                MaxDegreeOfParallelism = options.Value.MaxConcurrency,
                CancellationToken      = stoppingToken,
            },
            ProcessAsync);
    }

    // ── Job lifecycle wrapper ─────────────────────────────────────────────────

    /// <summary>
    /// Marks the job InProgress, delegates to <see cref="IngestBatchesAsync"/>,
    /// then updates the job to Completed or Failed.
    /// </summary>
    private async ValueTask ProcessAsync(SyncRequest req, CancellationToken ct)
    {
        await syncJobRepo.UpdateInProgressAsync(req.JobId, ct);

        logger.LogInformation(
            "Sync started [{JobId}] {Symbol}  {From:yyyy-MM-dd} → {To:yyyy-MM-dd}",
            req.JobId, req.Symbol, req.FromTime, req.ToTime);

        try
        {
            int totalBars = await IngestBatchesAsync(req, ct);

            await syncJobRepo.UpdateCompletedAsync(req.JobId, totalBars, ct);

            logger.LogInformation(
                "Sync completed [{JobId}] {Symbol} — {TotalBars} bars ingested.",
                req.JobId, req.Symbol, totalBars);
        }
        catch (Exception ex) when (ex is not OperationCanceledException)
        {
            logger.LogError(ex, "Sync failed [{JobId}] {Symbol}", req.JobId, req.Symbol);
            await syncJobRepo.UpdateFailedAsync(req.JobId, ex.Message, ct);
        }
    }

    // ── Batch iteration ───────────────────────────────────────────────────────

    /// <summary>
    /// Iterates over the full date range in <see cref="BatchWindow"/>-sized chunks,
    /// fetching and inserting bars for each.
    /// </summary>
    /// <returns>Total number of bars written to the database.</returns>
    /// <remarks>
    /// <para>
    /// <b>DH-905 handling (no-data windows):</b><br/>
    /// Dhan returns error code DH-905 when no data exists for the requested range.
    /// Two scenarios arise:
    /// <list type="bullet">
    ///   <item>
    ///     <b>Pre-listing gap (totalBars == 0):</b> We haven't found the listing date yet.
    ///     Advance the cursor by <see cref="ListingSearchStep"/> to skip ahead faster.
    ///   </item>
    ///   <item>
    ///     <b>Post-listing gap (totalBars &gt; 0):</b> We've consumed all available data.
    ///     Stop immediately.
    ///   </item>
    /// </list>
    /// </para>
    /// </remarks>
    private async Task<int> IngestBatchesAsync(SyncRequest req, CancellationToken ct)
    {
        int      totalBars = 0;
        DateTime cursor    = req.FromTime.Date;

        while (cursor <= req.ToTime && !ct.IsCancellationRequested)
        {
            var batchEnd = Min(cursor.Add(BatchWindow), req.ToTime);

            IReadOnlyList<OhlcvBar> bars;
            try
            {
                bars = await dhanClient.GetIntradayAsync(
                    req.DhanSecurityId, req.ExchangeSegment, cursor, batchEnd, ct);
            }
            catch (DhanNoDataException ex)
            {
                if (totalBars > 0)
                {
                    // All available history has been consumed; no more data ahead.
                    logger.LogInformation(
                        "[{Symbol}] No data after {Cursor:yyyy-MM-dd} — ingestion complete.",
                        req.Symbol, cursor);
                    break;
                }

                // Listing date not yet reached; jump forward to find it.
                logger.LogDebug(
                    "[{Symbol}] DH-905 for {From:yyyy-MM-dd}–{To:yyyy-MM-dd}, no data yet — advancing {Step} days.",
                    req.Symbol, ex.From, ex.To, ListingSearchStep.Days);

                cursor = cursor.Add(ListingSearchStep);
                await Task.Delay(options.Value.DelayBetweenCallsMs, ct);
                continue;
            }

            if (bars.Count > 0)
            {
                await priceDataRepo.BulkInsertAsync(req.SymbolId, bars, ct);
                totalBars += bars.Count;

                logger.LogDebug(
                    "[{Symbol}] +{Count} bars  {From:yyyy-MM-dd} → {To:yyyy-MM-dd}  (total: {Total})",
                    req.Symbol, bars.Count, cursor, batchEnd, totalBars);
            }

            cursor = batchEnd.AddDays(1);

            // Respect the per-worker inter-call delay to stay within Dhan's rate limit.
            await Task.Delay(options.Value.DelayBetweenCallsMs, ct);
        }

        return totalBars;
    }

    // ── Utilities ─────────────────────────────────────────────────────────────

    /// <summary>Returns the earlier of two <see cref="DateTime"/> values.</summary>
    private static DateTime Min(DateTime a, DateTime b) => a < b ? a : b;
}
