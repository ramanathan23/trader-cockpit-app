using System.Collections.Frozen;
using System.Threading.Channels;
using Microsoft.Extensions.Logging;
using TraderCockpit.MarketData.Domain;
using TraderCockpit.MarketData.Repositories;

namespace TraderCockpit.MarketData.Services;

/// <summary>
/// Determines what data each symbol needs and writes <see cref="SyncRequest"/> items
/// into the ingestion channel.  The actual fetching and inserting is done by
/// <see cref="IngestionBackgroundService"/>.
/// </summary>
public sealed class SyncManager(
    ISymbolRepository              symbolRepo,
    IPriceDataRepository           priceDataRepo,
    ISyncJobRepository             syncJobRepo,
    Channel<SyncRequest>           syncChannel,
    ILogger<SyncManager>           logger)
{
    private const int BackfillYears = 5;

    /// <summary>
    /// Queues a sync request for every syncable symbol (i.e., those with a
    /// <c>dhan_security_id</c>).  Symbols missing the ID are logged and skipped.
    /// Returns -1 if a sync is already in progress.
    /// </summary>
    public async Task<int> EnqueueFullSyncAsync(CancellationToken ct = default)
    {
        if (await syncJobRepo.HasActiveJobsAsync(ct))
        {
            logger.LogWarning("EnqueueFullSyncAsync: sync already in progress — skipping.");
            return -1;
        }
        var symbols = await symbolRepo.GetSyncableAsync(ct);

        if (symbols.Count == 0)
        {
            logger.LogWarning(
                "No syncable symbols found. " +
                "Populate dhan_security_id via POST /api/market-data/symbols/{{symbol}}/security-id first.");
            return 0;
        }

        // Fast lookup for logging / dedup
        var symbolLookup = symbols.ToFrozenDictionary(
            s => s.Symbol, StringComparer.OrdinalIgnoreCase);

        int enqueued = 0;
        foreach (var sym in symbolLookup.Values)
        {
            var latestTime = await priceDataRepo.GetLatestTimeAsync(sym.Id, ct);

            var fromTime = latestTime.HasValue
                ? latestTime.Value.AddMinutes(1)                      // incremental
                : DateTime.UtcNow.AddYears(-BackfillYears);           // full backfill

            var toTime = DateTime.UtcNow;

            if (fromTime >= toTime)
            {
                logger.LogDebug("{Symbol} is already up-to-date.", sym.Symbol);
                continue;
            }

            var job = await syncJobRepo.CreateAsync(
                sym.Id, sym.Symbol, fromTime, toTime, ct);

            await syncChannel.Writer.WriteAsync(new SyncRequest(
                JobId:          job.Id,
                SymbolId:       sym.Id,
                Symbol:         sym.Symbol,
                DhanSecurityId: sym.DhanSecurityId!,
                ExchangeSegment: sym.ExchangeSegment,
                FromTime:       fromTime,
                ToTime:         toTime), ct);

            enqueued++;
        }

        logger.LogInformation("SyncManager: enqueued {Count} sync requests.", enqueued);
        return enqueued;
    }

    /// <summary>
    /// Enqueues a sync request for a single symbol by ticker string.
    /// Returns null if the symbol is not found/missing ID, or if sync is already active.
    /// </summary>
    public async Task<Guid?> EnqueueSymbolSyncAsync(string ticker, CancellationToken ct = default)
    {
        if (await syncJobRepo.HasActiveJobsAsync(ct))
        {
            logger.LogWarning("EnqueueSymbolSyncAsync: sync already in progress — skipping '{Ticker}'.", ticker);
            return null;
        }
        var symbols = await symbolRepo.GetSyncableAsync(ct);
        var sym = symbols.FirstOrDefault(s =>
            string.Equals(s.Symbol, ticker, StringComparison.OrdinalIgnoreCase));

        if (sym is null)
        {
            logger.LogWarning("Symbol '{Ticker}' not found or has no dhan_security_id.", ticker);
            return null;
        }

        var latestTime = await priceDataRepo.GetLatestTimeAsync(sym.Id, ct);
        var fromTime   = latestTime.HasValue
            ? latestTime.Value.AddMinutes(1)
            : DateTime.UtcNow.AddYears(-BackfillYears);
        var toTime = DateTime.UtcNow;

        var job = await syncJobRepo.CreateAsync(sym.Id, sym.Symbol, fromTime, toTime, ct);

        await syncChannel.Writer.WriteAsync(new SyncRequest(
            job.Id, sym.Id, sym.Symbol,
            sym.DhanSecurityId!, sym.ExchangeSegment,
            fromTime, toTime), ct);

        return job.Id;
    }
}
