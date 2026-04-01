using Dapper;
using Npgsql;
using TraderCockpit.MarketData.Domain;

namespace TraderCockpit.MarketData.Repositories;

public sealed class SyncRunRepository(NpgsqlDataSource db) : ISyncRunRepository
{
    public async Task<SyncRun> CreateAsync(int totalSymbols, CancellationToken ct = default)
    {
        const string sql = """
            INSERT INTO sync_runs (total_symbols)
            VALUES (@TotalSymbols)
            RETURNING *
            """;
        await using var conn = await db.OpenConnectionAsync(ct);
        return await conn.QuerySingleAsync<SyncRun>(sql, new { TotalSymbols = totalSymbols });
    }

    public async Task<SyncRun?> GetByIdAsync(Guid id, CancellationToken ct = default)
    {
        const string sql = "SELECT * FROM sync_runs WHERE id = @Id";
        await using var conn = await db.OpenConnectionAsync(ct);
        return await conn.QuerySingleOrDefaultAsync<SyncRun>(sql, new { Id = id });
    }

    public async Task<IReadOnlyList<SyncRun>> GetAllAsync(CancellationToken ct = default)
    {
        const string sql = "SELECT * FROM sync_runs ORDER BY started_at DESC LIMIT 100";
        await using var conn = await db.OpenConnectionAsync(ct);
        return (await conn.QueryAsync<SyncRun>(sql)).AsList();
    }

    public async Task UpdateProgressAsync(
        Guid id, int updated, int skipped, int failed, string currentSymbol,
        CancellationToken ct = default)
    {
        const string sql = """
            UPDATE sync_runs
            SET symbols_updated = @Updated,
                symbols_skipped = @Skipped,
                symbols_failed  = @Failed,
                current_symbol  = @CurrentSymbol
            WHERE id = @Id
            """;
        await using var conn = await db.OpenConnectionAsync(ct);
        await conn.ExecuteAsync(sql, new { Id = id, Updated = updated, Skipped = skipped, Failed = failed, CurrentSymbol = currentSymbol });
    }

    public async Task UpdateCompletedAsync(
        Guid id, int updated, int skipped, int failed, CancellationToken ct = default)
    {
        const string sql = """
            UPDATE sync_runs
            SET status          = 'Completed',
                symbols_updated = @Updated,
                symbols_skipped = @Skipped,
                symbols_failed  = @Failed,
                current_symbol  = NULL,
                finished_at     = NOW()
            WHERE id = @Id
            """;
        await using var conn = await db.OpenConnectionAsync(ct);
        await conn.ExecuteAsync(sql, new { Id = id, Updated = updated, Skipped = skipped, Failed = failed });
    }

    public async Task UpdateFailedAsync(Guid id, string errorMessage, CancellationToken ct = default)
    {
        const string sql = """
            UPDATE sync_runs
            SET status        = 'Failed',
                error_message = @ErrorMessage,
                current_symbol = NULL,
                finished_at   = NOW()
            WHERE id = @Id
            """;
        await using var conn = await db.OpenConnectionAsync(ct);
        await conn.ExecuteAsync(sql, new { Id = id, ErrorMessage = errorMessage });
    }

    public async Task<bool> HasActiveRunAsync(CancellationToken ct = default)
    {
        const string sql = "SELECT EXISTS (SELECT 1 FROM sync_runs WHERE status = 'InProgress')";
        await using var conn = await db.OpenConnectionAsync(ct);
        return await conn.ExecuteScalarAsync<bool>(sql);
    }

    public async Task<int> ReconcileStuckRunsAsync(CancellationToken ct = default)
    {
        const string sql = """
            UPDATE sync_runs
            SET status        = 'Failed',
                error_message = 'Process restarted while run was in progress. Trigger POST /sync to resume.',
                finished_at   = NOW()
            WHERE status = 'InProgress'
            """;
        await using var conn = await db.OpenConnectionAsync(ct);
        return await conn.ExecuteAsync(sql);
    }

    public async Task ResetAllAsync(CancellationToken ct = default)
    {
        const string sql = "TRUNCATE TABLE sync_runs";
        await using var conn = await db.OpenConnectionAsync(ct);
        await conn.ExecuteAsync(new CommandDefinition(sql, commandTimeout: 0, cancellationToken: ct));
    }
}
