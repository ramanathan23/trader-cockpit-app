using TraderCockpit.MarketData.Domain;

namespace TraderCockpit.MarketData.Repositories;

/// <summary>
/// Persistence contract for <see cref="SyncJob"/> rows in the <c>sync_jobs</c> table.
/// All writes reflect the lifecycle state-machine defined on <see cref="SyncJob"/>.
/// </summary>
public interface ISyncJobRepository
{
    /// <summary>
    /// Inserts a new job in <see cref="SyncJobStatus.Pending"/> state and returns it.
    /// </summary>
    Task<SyncJob> CreateAsync(
        int symbolId, string symbol, DateTime from, DateTime to,
        CancellationToken ct = default);

    /// <summary>
    /// Returns the job with the given <paramref name="id"/>, or <c>null</c> if not found.
    /// </summary>
    Task<SyncJob?> GetByIdAsync(Guid id, CancellationToken ct = default);

    /// <summary>
    /// Returns the most recent 500 jobs ordered newest-first.
    /// </summary>
    Task<IReadOnlyList<SyncJob>> GetAllAsync(CancellationToken ct = default);

    /// <summary>
    /// Transitions the job to <see cref="SyncJobStatus.InProgress"/> and stamps <c>updated_at</c>.
    /// </summary>
    Task UpdateInProgressAsync(Guid id, CancellationToken ct = default);

    /// <summary>
    /// Transitions the job to <see cref="SyncJobStatus.Completed"/> and records
    /// the final bar count.
    /// </summary>
    Task UpdateCompletedAsync(Guid id, int barsFetched, CancellationToken ct = default);

    /// <summary>
    /// Transitions the job to <see cref="SyncJobStatus.Failed"/> and records
    /// the error message.
    /// </summary>
    Task UpdateFailedAsync(Guid id, string errorMessage, CancellationToken ct = default);

    /// <summary>
    /// Returns <c>true</c> when any job is currently
    /// <see cref="SyncJobStatus.Pending"/> or <see cref="SyncJobStatus.InProgress"/>.
    /// Used to prevent concurrent sync runs.
    /// </summary>
    Task<bool> HasActiveJobsAsync(CancellationToken ct = default);

    /// <summary>
    /// Marks all <see cref="SyncJobStatus.Pending"/> and <see cref="SyncJobStatus.InProgress"/>
    /// jobs as <see cref="SyncJobStatus.Failed"/>.
    /// </summary>
    /// <remarks>
    /// Called once at startup to clear jobs that were in-flight when the process last
    /// terminated.  Their in-memory <see cref="System.Threading.Channels.Channel{T}"/> work
    /// items were lost; the jobs would otherwise block every new sync attempt forever.
    /// After reconciliation, <c>price_data_1m</c> already contains whatever bars were
    /// successfully inserted before the crash, so the next sync will resume incrementally
    /// from the latest stored bar.
    /// </remarks>
    /// <returns>Number of rows updated (0 if the app shut down cleanly).</returns>
    Task<int> ReconcileStuckJobsAsync(CancellationToken ct = default);

    /// <summary>
    /// Truncates the <c>sync_jobs</c> table.
    /// Intended for the reset endpoint; not for routine use.
    /// </summary>
    Task ResetAllAsync(CancellationToken ct = default);
}
