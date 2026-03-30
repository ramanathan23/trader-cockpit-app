using Dapper;
using Npgsql;
using TraderCockpit.MarketData.Domain;

namespace TraderCockpit.MarketData.Repositories;

public sealed class SyncJobRepository(NpgsqlDataSource db) : ISyncJobRepository
{
    public async Task<SyncJob> CreateAsync(
        int symbolId, string symbol, DateTime from, DateTime to,
        CancellationToken ct = default)
    {
        const string sql = """
            INSERT INTO sync_jobs (symbol_id, symbol, status, from_time, to_time)
            VALUES (@SymbolId, @Symbol, 'Pending', @From, @To)
            RETURNING *
            """;
        await using var conn = await db.OpenConnectionAsync(ct);
        return await conn.QuerySingleAsync<SyncJob>(sql,
            new { SymbolId = symbolId, Symbol = symbol, From = from, To = to });
    }

    public async Task<SyncJob?> GetByIdAsync(Guid id, CancellationToken ct = default)
    {
        const string sql = "SELECT * FROM sync_jobs WHERE id = @Id";
        await using var conn = await db.OpenConnectionAsync(ct);
        return await conn.QuerySingleOrDefaultAsync<SyncJob>(sql, new { Id = id });
    }

    public async Task<IReadOnlyList<SyncJob>> GetAllAsync(CancellationToken ct = default)
    {
        const string sql = "SELECT * FROM sync_jobs ORDER BY created_at DESC LIMIT 500";
        await using var conn = await db.OpenConnectionAsync(ct);
        return (await conn.QueryAsync<SyncJob>(sql)).AsList();
    }

    public async Task UpdateInProgressAsync(Guid id, CancellationToken ct = default)
    {
        const string sql = """
            UPDATE sync_jobs SET status = 'InProgress', updated_at = NOW() WHERE id = @Id
            """;
        await using var conn = await db.OpenConnectionAsync(ct);
        await conn.ExecuteAsync(sql, new { Id = id });
    }

    public async Task UpdateCompletedAsync(Guid id, int barsFetched, CancellationToken ct = default)
    {
        const string sql = """
            UPDATE sync_jobs
            SET status = 'Completed', bars_fetched = @BarsFetched, updated_at = NOW()
            WHERE id = @Id
            """;
        await using var conn = await db.OpenConnectionAsync(ct);
        await conn.ExecuteAsync(sql, new { Id = id, BarsFetched = barsFetched });
    }

    public async Task UpdateFailedAsync(Guid id, string errorMessage, CancellationToken ct = default)
    {
        const string sql = """
            UPDATE sync_jobs
            SET status = 'Failed', error_message = @ErrorMessage, updated_at = NOW()
            WHERE id = @Id
            """;
        await using var conn = await db.OpenConnectionAsync(ct);
        await conn.ExecuteAsync(sql, new { Id = id, ErrorMessage = errorMessage });
    }

    public async Task<bool> HasActiveJobsAsync(CancellationToken ct = default)
    {
        const string sql = """
            SELECT EXISTS (
                SELECT 1 FROM sync_jobs
                WHERE status IN ('Pending', 'InProgress')
            )
            """;
        await using var conn = await db.OpenConnectionAsync(ct);
        return await conn.ExecuteScalarAsync<bool>(sql);
    }

    /// <inheritdoc/>
    public async Task<int> ReconcileStuckJobsAsync(CancellationToken ct = default)
    {
        // Jobs left Pending or InProgress means the process died before they completed.
        // Their in-memory SyncRequest was lost with the process; mark them Failed so the
        // HasActiveJobsAsync guard no longer blocks new sync attempts.
        // The next POST /sync will recalculate their window from MAX(time) in price_data_1m,
        // resuming incrementally from whatever bars were already inserted.
        const string sql = """
            UPDATE sync_jobs
            SET    status        = 'Failed',
                   error_message = 'Job was in-flight when the app stopped. Trigger a new sync to resume from the last saved bar.',
                   updated_at    = NOW()
            WHERE  status IN ('Pending', 'InProgress')
            """;
        await using var conn = await db.OpenConnectionAsync(ct);
        return await conn.ExecuteAsync(sql);
    }

    public async Task ResetAllAsync(CancellationToken ct = default)
    {
        const string sql = "TRUNCATE TABLE sync_jobs";
        await using var conn = await db.OpenConnectionAsync(ct);
        await conn.ExecuteAsync(sql);
    }
}
