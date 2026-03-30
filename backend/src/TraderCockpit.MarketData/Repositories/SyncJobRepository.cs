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
}
