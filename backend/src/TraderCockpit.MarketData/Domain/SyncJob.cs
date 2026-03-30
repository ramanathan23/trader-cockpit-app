namespace TraderCockpit.MarketData.Domain;

// ── Status enumeration ────────────────────────────────────────────────────────

/// <summary>
/// Lifecycle states of a <see cref="SyncJob"/>.
/// Transitions are strictly linear: Pending → InProgress → Completed | Failed.
/// </summary>
public enum SyncJobStatus
{
    /// <summary>Created and waiting in the ingestion channel.</summary>
    Pending,

    /// <summary>A worker has picked up the job and is fetching data.</summary>
    InProgress,

    /// <summary>All batches processed successfully.</summary>
    Completed,

    /// <summary>An unrecoverable error occurred; see <see cref="SyncJob.ErrorMessage"/>.</summary>
    Failed,
}

// ── Aggregate root ────────────────────────────────────────────────────────────

/// <summary>
/// Tracks the progress of a single symbol's data-ingestion run.
/// Persisted in the <c>sync_jobs</c> table and exposed to clients for polling.
/// </summary>
/// <remarks>
/// State transitions are enforced via domain methods rather than direct property
/// mutation, making the lifecycle explicit and preventing illegal state combinations.
/// Setters are <c>set</c> (not <c>init</c>) only where Dapper requires mutability
/// to hydrate DB results; callers should prefer the domain methods.
/// </remarks>
public sealed class SyncJob
{
    // ── Identity ──────────────────────────────────────────────────────────────

    /// <summary>Unique job identifier (UUID primary key).</summary>
    public Guid Id { get; init; }

    /// <summary>Foreign key into <c>symbols</c>. Null for full-sync sentinels.</summary>
    public int? SymbolId { get; init; }

    /// <summary>Ticker string copied at creation time (e.g. <c>RELIANCE</c>).</summary>
    public string Symbol { get; init; } = "";

    // ── Time range ────────────────────────────────────────────────────────────

    /// <summary>Start of the requested data window (inclusive, UTC).</summary>
    public DateTime? FromTime { get; init; }

    /// <summary>End of the requested data window (inclusive, UTC).</summary>
    public DateTime? ToTime { get; init; }

    /// <summary>When this job row was first inserted.</summary>
    public DateTime CreatedAt { get; init; }

    // ── Mutable state (mutated only via domain methods below) ────────────────

    /// <summary>Current lifecycle state. Use <see cref="MarkInProgress"/>, <see cref="MarkCompleted"/>, or <see cref="MarkFailed"/> to advance.</summary>
    public SyncJobStatus Status { get; set; }

    /// <summary>Cumulative count of 1-minute bars written to <c>price_data_1m</c>.</summary>
    public int BarsFetched { get; set; }

    /// <summary>Set when <see cref="Status"/> is <see cref="SyncJobStatus.Failed"/>.</summary>
    public string? ErrorMessage { get; set; }

    /// <summary>Timestamp of the last status change (server-side NOW()).</summary>
    public DateTime UpdatedAt { get; set; }

    // ── Domain methods ────────────────────────────────────────────────────────

    /// <summary>
    /// Advances status from <see cref="SyncJobStatus.Pending"/> to
    /// <see cref="SyncJobStatus.InProgress"/>.
    /// </summary>
    /// <exception cref="InvalidOperationException">
    /// Thrown if the job is not currently in <see cref="SyncJobStatus.Pending"/>.
    /// </exception>
    public void MarkInProgress()
    {
        if (Status != SyncJobStatus.Pending)
            throw new InvalidOperationException(
                $"Cannot transition to InProgress from {Status}.");

        Status    = SyncJobStatus.InProgress;
        UpdatedAt = DateTime.UtcNow;
    }

    /// <summary>
    /// Marks the job as successfully completed with a final bar count.
    /// </summary>
    /// <param name="barsFetched">Total 1-minute bars inserted into the hypertable.</param>
    public void MarkCompleted(int barsFetched)
    {
        Status      = SyncJobStatus.Completed;
        BarsFetched = barsFetched;
        UpdatedAt   = DateTime.UtcNow;
    }

    /// <summary>
    /// Marks the job as failed and records the reason.
    /// </summary>
    /// <param name="errorMessage">Human-readable description of the failure.</param>
    public void MarkFailed(string errorMessage)
    {
        Status       = SyncJobStatus.Failed;
        ErrorMessage = errorMessage;
        UpdatedAt    = DateTime.UtcNow;
    }
}

// ── Channel message ───────────────────────────────────────────────────────────

/// <summary>
/// Immutable work item written to the ingestion channel by <c>SyncManager</c>
/// and consumed by <c>IngestionBackgroundService</c> workers.
/// Contains everything a worker needs without additional DB lookups.
/// </summary>
public sealed record SyncRequest(
    /// <summary>The <see cref="SyncJob.Id"/> this request is tracked under.</summary>
    Guid     JobId,

    /// <summary>Database primary key for the symbol.</summary>
    int      SymbolId,

    /// <summary>Human-readable ticker (e.g. <c>RELIANCE</c>).</summary>
    string   Symbol,

    /// <summary>Dhan's internal numeric ID, used in API calls.</summary>
    string   DhanSecurityId,

    /// <summary>Exchange segment string sent to Dhan (e.g. <c>NSE_EQ</c>).</summary>
    string   ExchangeSegment,

    /// <summary>Inclusive start of the data window (UTC).</summary>
    DateTime FromTime,

    /// <summary>Inclusive end of the data window (UTC).</summary>
    DateTime ToTime
);
