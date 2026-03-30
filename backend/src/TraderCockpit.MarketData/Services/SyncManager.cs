using System.Threading.Channels;
using Microsoft.Extensions.Logging;
using TraderCockpit.MarketData.Domain;
using TraderCockpit.MarketData.Repositories;

namespace TraderCockpit.MarketData.Services;

// ── Result types ──────────────────────────────────────────────────────────────

/// <summary>
/// Reasons a single-symbol sync was not enqueued.
/// Lets callers produce precise HTTP responses without string-matching log messages.
/// </summary>
public enum SyncSkipReason
{
    /// <summary>Another job is currently Pending or InProgress.</summary>
    AlreadyRunning,

    /// <summary>The ticker was not found, or its <c>dhan_security_id</c> is not mapped.</summary>
    SymbolNotFound,

    /// <summary>The symbol's data is already current; no new window to fetch.</summary>
    AlreadyUpToDate,
}

/// <summary>Result of <see cref="SyncManager.EnqueueSymbolSyncAsync"/>.</summary>
public sealed record SymbolSyncResult(
    bool            IsEnqueued,
    Guid?           JobId  = null,
    SyncSkipReason? Reason = null)
{
    public static SymbolSyncResult Enqueued(Guid jobId)        => new(true,  JobId: jobId);
    public static SymbolSyncResult Skipped(SyncSkipReason why) => new(false, Reason: why);
}

// ── Service ───────────────────────────────────────────────────────────────────

/// <summary>
/// Decides what data each symbol needs and enqueues <see cref="SyncRequest"/> items
/// into the ingestion channel. The actual fetching and writing is done by
/// <see cref="IngestionBackgroundService"/>.
/// </summary>
/// <remarks>
/// <b>Full sync is fire-and-forget:</b> <see cref="EnqueueFullSyncAsync"/> performs
/// two fast guard queries on the caller's thread, returns a count of syncable symbols,
/// then schedules the per-symbol DB work (GetLatestTime + CreateJob + WriteToChannel)
/// as a background <see cref="Task"/>. The HTTP response is sent immediately; callers
/// poll <c>GET /api/market-data/sync</c> for job status.
/// </remarks>
public sealed class SyncManager(
    ISymbolRepository    symbolRepo,
    IPriceDataRepository priceDataRepo,
    ISyncJobRepository   syncJobRepo,
    Channel<SyncRequest> syncChannel,
    ILogger<SyncManager> logger)
{
    /// <summary>How far back to backfill when a symbol has no data yet.</summary>
    private const int BackfillYears = 5;

    // ── Public API ────────────────────────────────────────────────────────────

    /// <summary>
    /// Validates the request synchronously, then schedules all per-symbol work in
    /// the background so the caller gets an immediate response.
    /// </summary>
    /// <returns>
    /// Number of syncable symbols found (jobs will be created in background),
    /// <c>0</c> if none are ready, or <c>-1</c> if a sync is already running.
    /// </returns>
    public async Task<int> EnqueueFullSyncAsync(CancellationToken ct = default)
    {
        // ── Guard checks — fast, run on the request thread ───────────────────
        if (await syncJobRepo.HasActiveJobsAsync(ct))
        {
            logger.LogWarning("Full sync rejected — a sync is already in progress.");
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

        // ── Schedule per-symbol work in background — caller returns now ──────
        // Each symbol requires GetLatestTime + CreateJob + WriteToChannel.
        // Running this serially for 2,278 symbols on the request thread would
        // block the HTTP response for many seconds.
        _ = ScheduleAllAsync(symbols);

        return symbols.Count;
    }

    /// <summary>
    /// Enqueues a sync request for a single symbol. Synchronous — only 3 DB calls,
    /// fast enough to complete on the request thread.
    /// </summary>
    public async Task<SymbolSyncResult> EnqueueSymbolSyncAsync(
        string ticker, CancellationToken ct = default)
    {
        if (await syncJobRepo.HasActiveJobsAsync(ct))
        {
            logger.LogWarning(
                "Symbol sync for '{Ticker}' rejected — a sync is already in progress.", ticker);
            return SymbolSyncResult.Skipped(SyncSkipReason.AlreadyRunning);
        }

        var symbols = await symbolRepo.GetSyncableAsync(ct);
        var sym = symbols.FirstOrDefault(s =>
            string.Equals(s.Symbol, ticker, StringComparison.OrdinalIgnoreCase));

        if (sym is null)
        {
            logger.LogWarning("Symbol '{Ticker}' not found or has no dhan_security_id.", ticker);
            return SymbolSyncResult.Skipped(SyncSkipReason.SymbolNotFound);
        }

        var (fromTime, toTime) = await CalculateSyncWindowAsync(sym.Id, ct);

        if (fromTime >= toTime)
        {
            logger.LogInformation(
                "Symbol '{Ticker}' is already up-to-date (latest bar: {LatestTime}).",
                ticker, fromTime.AddMinutes(-1));
            return SymbolSyncResult.Skipped(SyncSkipReason.AlreadyUpToDate);
        }

        var job = await syncJobRepo.CreateAsync(sym.Id, sym.Symbol, fromTime, toTime, ct);
        await syncChannel.Writer.WriteAsync(BuildRequest(job.Id, sym, fromTime, toTime), ct);

        return SymbolSyncResult.Enqueued(job.Id);
    }

    // ── Background scheduling ─────────────────────────────────────────────────

    /// <summary>
    /// Iterates all symbols, creates their sync jobs, and writes to the channel.
    /// Runs as a fire-and-forget background task — no request context is needed.
    /// Exceptions are caught and logged so the background task never crashes silently.
    /// </summary>
    private async Task ScheduleAllAsync(IReadOnlyList<MarketSymbol> symbols)
    {
        logger.LogInformation(
            "Background scheduling started for {Total} syncable symbols.", symbols.Count);

        int enqueued = 0;
        try
        {
            foreach (var sym in symbols)
            {
                if (await EnqueueAsync(sym, CancellationToken.None))
                    enqueued++;
            }

            logger.LogInformation(
                "Background scheduling complete — {Enqueued}/{Total} jobs created.",
                enqueued, symbols.Count);
        }
        catch (Exception ex)
        {
            logger.LogError(ex,
                "Background scheduling failed after {Enqueued} jobs. " +
                "Trigger a new sync to retry the remaining symbols.", enqueued);
        }
    }

    // ── Private helpers ───────────────────────────────────────────────────────

    private async Task<bool> EnqueueAsync(MarketSymbol sym, CancellationToken ct)
    {
        var (fromTime, toTime) = await CalculateSyncWindowAsync(sym.Id, ct);

        if (fromTime >= toTime)
        {
            logger.LogDebug("{Symbol} is already up-to-date — skipping.", sym.Symbol);
            return false;
        }

        var job = await syncJobRepo.CreateAsync(sym.Id, sym.Symbol, fromTime, toTime, ct);
        await syncChannel.Writer.WriteAsync(BuildRequest(job.Id, sym, fromTime, toTime), ct);

        return true;
    }

    private async Task<(DateTime from, DateTime to)> CalculateSyncWindowAsync(
        int symbolId, CancellationToken ct)
    {
        var latestTime = await priceDataRepo.GetLatestTimeAsync(symbolId, ct);

        var from = latestTime.HasValue
            ? latestTime.Value.AddMinutes(1)
            : DateTime.UtcNow.AddYears(-BackfillYears);

        return (from, to: DateTime.UtcNow);
    }

    private static SyncRequest BuildRequest(
        Guid jobId, MarketSymbol sym, DateTime from, DateTime to)
        => new(
            JobId:           jobId,
            SymbolId:        sym.Id,
            Symbol:          sym.Symbol,
            DhanSecurityId:  sym.DhanSecurityId!,
            ExchangeSegment: sym.ExchangeSegment,
            FromTime:        from,
            ToTime:          to);
}
