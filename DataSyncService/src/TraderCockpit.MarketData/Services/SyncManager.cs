using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using TraderCockpit.MarketData.Dhan;
using TraderCockpit.MarketData.Domain;
using TraderCockpit.MarketData.Repositories;

namespace TraderCockpit.MarketData.Services;

// ── Trigger result ────────────────────────────────────────────────────────────

public enum SyncTriggerStatus { Started, AlreadyRunning, NoSymbols }

public sealed record SyncTriggerResult(SyncTriggerStatus Status, Guid? RunId = null)
{
    public static SyncTriggerResult Started(Guid runId)    => new(SyncTriggerStatus.Started, runId);
    public static SyncTriggerResult AlreadyRunning()       => new(SyncTriggerStatus.AlreadyRunning);
    public static SyncTriggerResult NoSymbols()            => new(SyncTriggerStatus.NoSymbols);
}

// ── Service ───────────────────────────────────────────────────────────────────

/// <summary>
/// Orchestrates full-universe data sync runs — both 1-minute and daily timeframes.
///
/// Per symbol on each run:
///   1-minute (intraday):
///     • No data → backfill <see cref="DhanOptions.Backfill1mYears"/> years (default 1).
///     • Latest bar within <see cref="StaleThresholdMinutes"/> → skip.
///     • Otherwise → incremental from (latest + 1 min).
///     Batched in 75-day windows (Dhan intraday cap ~90 days).
///
///   Daily (EOD):
///     • No data → backfill <see cref="DhanOptions.BackfillDailyYears"/> years (default 5).
///     • Latest bar is today → skip.
///     • Otherwise → incremental from (latest + 1 day).
///     Batched in 1-year windows (Dhan historical cap).
///
/// One <see cref="SyncRun"/> row tracks the entire run.
/// Per-symbol errors are counted but do not abort the run.
/// </summary>
public sealed class SyncManager(
    ISymbolRepository    symbolRepo,
    IPriceDataRepository priceDataRepo,
    ISyncRunRepository   syncRunRepo,
    DhanClient           dhanClient,
    IOptions<DhanOptions> options,
    ILogger<SyncManager> logger)
{
    private const int StaleThresholdMinutes = 15;

    /// <summary>Maximum date span per Dhan intraday API call (~90-day cap; use 75 for headroom).</summary>
    private static readonly TimeSpan IntradayBatchWindow = TimeSpan.FromDays(75);

    /// <summary>Maximum date span per Dhan historical (daily) API call (~1-year cap).</summary>
    private static readonly TimeSpan DailyBatchWindow = TimeSpan.FromDays(365);

    // ── Public trigger ────────────────────────────────────────────────────────

    /// <summary>
    /// Checks guards synchronously, creates a SyncRun row, then fires the
    /// full processing loop as a background task. Returns immediately.
    /// </summary>
    public async Task<SyncTriggerResult> TriggerAsync(CancellationToken ct = default)
    {
        if (await syncRunRepo.HasActiveRunAsync(ct))
        {
            logger.LogWarning("Sync rejected — a run is already InProgress.");
            return SyncTriggerResult.AlreadyRunning();
        }

        var symbols = await symbolRepo.GetSyncableAsync(ct);
        if (symbols.Count == 0)
        {
            logger.LogWarning(
                "No syncable symbols found. " +
                "Ensure dhan_security_id is populated via POST /api/market-data/symbols/{symbol}/security-id.");
            return SyncTriggerResult.NoSymbols();
        }

        var run = await syncRunRepo.CreateAsync(symbols.Count, ct);

        logger.LogInformation(
            "Sync run {RunId} started — {Total} syncable symbols " +
            "(1m backfill: {M}yr, daily backfill: {D}yr).",
            run.Id, symbols.Count,
            options.Value.Backfill1mYears, options.Value.BackfillDailyYears);

        // Fire and forget — HTTP response is returned immediately.
        _ = ExecuteRunAsync(run.Id, symbols);

        return SyncTriggerResult.Started(run.Id);
    }

    // ── Background execution ──────────────────────────────────────────────────

    private async Task ExecuteRunAsync(Guid runId, IReadOnlyList<MarketSymbol> symbols)
    {
        int updated = 0, skipped = 0, failed = 0;

        try
        {
            await Parallel.ForEachAsync(
                symbols,
                new ParallelOptions { MaxDegreeOfParallelism = options.Value.MaxConcurrency },
                async (sym, ct) =>
                {
                    var result = await ProcessSymbolAsync(sym, ct);

                    switch (result)
                    {
                        case SymbolOutcome.Updated: Interlocked.Increment(ref updated); break;
                        case SymbolOutcome.Skipped: Interlocked.Increment(ref skipped); break;
                        case SymbolOutcome.Failed:  Interlocked.Increment(ref failed);  break;
                    }

                    try
                    {
                        await syncRunRepo.UpdateProgressAsync(
                            runId,
                            Volatile.Read(ref updated),
                            Volatile.Read(ref skipped),
                            Volatile.Read(ref failed),
                            sym.Symbol,
                            ct);
                    }
                    catch (Exception ex)
                    {
                        logger.LogWarning(ex, "Progress update failed for {Symbol} — continuing.", sym.Symbol);
                    }
                });

            await syncRunRepo.UpdateCompletedAsync(runId, updated, skipped, failed);

            logger.LogInformation(
                "Sync run {RunId} completed — updated: {U}, skipped: {S}, failed: {F}.",
                runId, updated, skipped, failed);
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Sync run {RunId} failed unexpectedly.", runId);
            await syncRunRepo.UpdateFailedAsync(runId, ex.Message, CancellationToken.None);
        }
    }

    // ── Per-symbol logic ──────────────────────────────────────────────────────

    private async Task<SymbolOutcome> ProcessSymbolAsync(MarketSymbol sym, CancellationToken ct)
    {
        try
        {
            var now = DateTime.UtcNow;
            bool any1mData    = false;
            bool anyDailyData = false;

            // ── 1-minute data ─────────────────────────────────────────────────
            var latest1m = await priceDataRepo.GetLatestTimeAsync(sym.Id, ct);

            if (latest1m is null || now - latest1m.Value >= TimeSpan.FromMinutes(StaleThresholdMinutes))
            {
                var from1m = latest1m is null
                    ? now.AddYears(-options.Value.Backfill1mYears)
                    : latest1m.Value.AddMinutes(1);

                int bars1m = await IngestIntradayBatchesAsync(sym, from1m, now, ct);
                any1mData = bars1m > 0;

                logger.LogDebug("{Symbol} 1m — {Bars} bars ({From:yyyy-MM-dd} → {To:yyyy-MM-dd}).",
                    sym.Symbol, bars1m, from1m, now);
            }
            else
            {
                logger.LogDebug("{Symbol} 1m is current (latest: {Latest:u}) — skipping.", sym.Symbol, latest1m.Value);
            }

            // ── Daily (EOD) data ──────────────────────────────────────────────
            var latestDaily = await priceDataRepo.GetLatestDailyTimeAsync(sym.Id, ct);

            if (latestDaily is null || now.Date > latestDaily.Value.Date)
            {
                var fromDaily = latestDaily is null
                    ? now.AddYears(-options.Value.BackfillDailyYears)
                    : latestDaily.Value.AddDays(1);

                int barsDaily = await IngestDailyBatchesAsync(sym, fromDaily, now, ct);
                anyDailyData = barsDaily > 0;

                logger.LogDebug("{Symbol} daily — {Bars} bars ({From:yyyy-MM-dd} → {To:yyyy-MM-dd}).",
                    sym.Symbol, barsDaily, fromDaily, now);
            }
            else
            {
                logger.LogDebug("{Symbol} daily is current (latest: {Latest:u}) — skipping.", sym.Symbol, latestDaily.Value);
            }

            return (any1mData || anyDailyData) ? SymbolOutcome.Updated : SymbolOutcome.Skipped;
        }
        catch (Exception ex) when (ex is not OperationCanceledException || !ct.IsCancellationRequested)
        {
            logger.LogError(ex, "Sync failed for {Symbol}.", sym.Symbol);
            return SymbolOutcome.Failed;
        }
    }

    // ── 1-minute batch ingestion (75-day windows) ─────────────────────────────

    /// <summary>
    /// Iterates the date range in 75-day batches, inserting 1m bars for each.
    /// Handles DH-905 (no data) by binary-searching for the listing date on
    /// the first pass, then stopping when the gap is reached on later passes.
    /// </summary>
    private async Task<int> IngestIntradayBatchesAsync(
        MarketSymbol sym, DateTime from, DateTime to, CancellationToken ct)
    {
        int      totalBars    = 0;
        DateTime cursor       = from.Date;
        bool     listingFound = false;

        while (cursor <= to && !ct.IsCancellationRequested)
        {
            var batchEnd = Min(cursor.Add(IntradayBatchWindow), to);

            IReadOnlyList<OhlcvBar> bars;
            try
            {
                bars = await dhanClient.GetIntradayAsync(
                    sym.DhanSecurityId!, sym.ExchangeSegment, cursor, batchEnd, ct);

                listingFound = true;
            }
            catch (DhanNoDataException)
            {
                if (listingFound)
                {
                    logger.LogDebug("[{Symbol}] 1m: no data after {Cursor:yyyy-MM-dd} — done.", sym.Symbol, cursor);
                    break;
                }

                // Haven't seen any data yet — binary-search for listing date.
                logger.LogDebug("[{Symbol}] 1m: DH-905 on first batch — searching for listing date.", sym.Symbol);
                var listingDate = await FindListingDateAsync(sym, batchEnd, to, ct);

                if (listingDate is null)
                {
                    logger.LogDebug("[{Symbol}] 1m: no data found in backfill range — skipping.", sym.Symbol);
                    break;
                }

                cursor       = listingDate.Value;
                listingFound = true;
                continue;
            }

            if (bars.Count > 0)
            {
                await priceDataRepo.BulkInsertAsync(sym.Id, bars, ct);
                totalBars += bars.Count;
            }

            cursor = batchEnd.AddDays(1);
        }

        return totalBars;
    }

    // ── Daily batch ingestion (1-year windows) ────────────────────────────────

    /// <summary>
    /// Iterates the date range in 1-year batches, inserting daily EOD bars for each.
    /// </summary>
    private async Task<int> IngestDailyBatchesAsync(
        MarketSymbol sym, DateTime from, DateTime to, CancellationToken ct)
    {
        int      totalBars = 0;
        DateTime cursor    = from.Date;

        while (cursor <= to && !ct.IsCancellationRequested)
        {
            var batchEnd = Min(cursor.Add(DailyBatchWindow), to);

            IReadOnlyList<OhlcvBar> bars;
            try
            {
                bars = await dhanClient.GetHistoricalAsync(
                    sym.DhanSecurityId!, sym.ExchangeSegment, cursor, batchEnd, ct);
            }
            catch (DhanNoDataException)
            {
                logger.LogDebug("[{Symbol}] daily: no data for {Cursor:yyyy-MM-dd}–{End:yyyy-MM-dd} — skipping batch.",
                    sym.Symbol, cursor, batchEnd);
                cursor = batchEnd.AddDays(1);
                continue;
            }

            if (bars.Count > 0)
            {
                await priceDataRepo.BulkInsertDailyAsync(sym.Id, bars, ct);
                totalBars += bars.Count;
            }

            cursor = batchEnd.AddDays(1);
        }

        return totalBars;
    }

    // ── Listing-date binary search (1m only) ──────────────────────────────────

    /// <summary>
    /// Binary-searches [lo, hi] for the earliest 75-day window containing 1m data.
    /// O(log(range / IntradayBatchWindow)) API calls — ~3–4 calls for a 1-year range.
    /// </summary>
    private async Task<DateTime?> FindListingDateAsync(
        MarketSymbol sym, DateTime lo, DateTime hi, CancellationToken ct)
    {
        if (lo >= hi) return null;

        if ((hi - lo) <= IntradayBatchWindow)
        {
            try
            {
                var bars = await dhanClient.GetIntradayAsync(
                    sym.DhanSecurityId!, sym.ExchangeSegment, lo, hi, ct);
                return bars.Count > 0 ? lo : null;
            }
            catch (DhanNoDataException) { return null; }
        }

        var mid    = lo.AddDays((hi - lo).TotalDays / 2);
        var midEnd = Min(mid.Add(IntradayBatchWindow), hi);

        bool hasData;
        try
        {
            var bars = await dhanClient.GetIntradayAsync(
                sym.DhanSecurityId!, sym.ExchangeSegment, mid, midEnd, ct);
            hasData = bars.Count > 0;
        }
        catch (DhanNoDataException) { hasData = false; }

        return hasData
            ? await FindListingDateAsync(sym, lo, mid, ct) ?? mid
            : await FindListingDateAsync(sym, midEnd, hi, ct);
    }

    private static DateTime Min(DateTime a, DateTime b) => a < b ? a : b;

    private enum SymbolOutcome { Updated, Skipped, Failed }
}
