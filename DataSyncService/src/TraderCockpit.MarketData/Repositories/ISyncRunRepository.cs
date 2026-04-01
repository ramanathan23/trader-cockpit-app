using TraderCockpit.MarketData.Domain;

namespace TraderCockpit.MarketData.Repositories;

/// <summary>
/// Persistence contract for the <c>sync_runs</c> table.
/// One row per full-universe sync trigger.
/// </summary>
public interface ISyncRunRepository
{
    /// <summary>Creates a new InProgress run and returns it.</summary>
    Task<SyncRun> CreateAsync(int totalSymbols, CancellationToken ct = default);

    /// <summary>Returns the run with the given id, or null.</summary>
    Task<SyncRun?> GetByIdAsync(Guid id, CancellationToken ct = default);

    /// <summary>Returns all runs ordered newest-first (limit 100).</summary>
    Task<IReadOnlyList<SyncRun>> GetAllAsync(CancellationToken ct = default);

    /// <summary>
    /// Updates live counters and current symbol during processing.
    /// Called after every symbol so the API shows real-time progress.
    /// </summary>
    Task UpdateProgressAsync(
        Guid   id,
        int    updated,
        int    skipped,
        int    failed,
        string currentSymbol,
        CancellationToken ct = default);

    /// <summary>Marks the run Completed with final counters.</summary>
    Task UpdateCompletedAsync(
        Guid id, int updated, int skipped, int failed,
        CancellationToken ct = default);

    /// <summary>Marks the run Failed with an error message.</summary>
    Task UpdateFailedAsync(Guid id, string errorMessage, CancellationToken ct = default);

    /// <summary>Returns true if any run is currently InProgress.</summary>
    Task<bool> HasActiveRunAsync(CancellationToken ct = default);

    /// <summary>
    /// Marks any InProgress run as Failed at startup.
    /// Called once before the port opens to clear runs left over from a crashed process.
    /// </summary>
    Task<int> ReconcileStuckRunsAsync(CancellationToken ct = default);

    /// <summary>Truncates the sync_runs table. For the reset endpoint only.</summary>
    Task ResetAllAsync(CancellationToken ct = default);
}
