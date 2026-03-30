using Dapper;
using Npgsql;
using TraderCockpit.MarketData.Domain;

namespace TraderCockpit.MarketData.Repositories;

public sealed class SymbolRepository(NpgsqlDataSource db) : ISymbolRepository
{
    public async Task UpsertManyAsync(IEnumerable<MarketSymbol> symbols, CancellationToken ct = default)
    {
        const string sql = """
            INSERT INTO symbols (symbol, company_name, series, isin, exchange_segment)
            VALUES (@Symbol, @CompanyName, @Series, @Isin, @ExchangeSegment)
            ON CONFLICT (symbol) DO UPDATE SET
                company_name     = EXCLUDED.company_name,
                series           = EXCLUDED.series,
                isin             = EXCLUDED.isin,
                updated_at       = NOW()
            """;

        await using var conn = await db.OpenConnectionAsync(ct);
        await conn.ExecuteAsync(sql, symbols);
    }

    public async Task<IReadOnlyList<MarketSymbol>> GetActiveAsync(CancellationToken ct = default)
    {
        const string sql = "SELECT * FROM symbols WHERE is_active = TRUE ORDER BY symbol";
        await using var conn = await db.OpenConnectionAsync(ct);
        return (await conn.QueryAsync<MarketSymbol>(sql)).AsList();
    }

    public async Task<IReadOnlyList<MarketSymbol>> GetSyncableAsync(CancellationToken ct = default)
    {
        const string sql = """
            SELECT * FROM symbols
            WHERE is_active = TRUE AND dhan_security_id IS NOT NULL
            ORDER BY symbol
            """;
        await using var conn = await db.OpenConnectionAsync(ct);
        return (await conn.QueryAsync<MarketSymbol>(sql)).AsList();
    }

    public async Task SetDhanSecurityIdAsync(string symbol, string dhanSecurityId, CancellationToken ct = default)
    {
        const string sql = """
            UPDATE symbols
            SET dhan_security_id = @DhanSecurityId, updated_at = NOW()
            WHERE symbol = @Symbol
            """;
        await using var conn = await db.OpenConnectionAsync(ct);
        await conn.ExecuteAsync(sql, new { Symbol = symbol, DhanSecurityId = dhanSecurityId });
    }

    public async Task<int> BulkSetDhanSecurityIdBySymbolAsync(
        IDictionary<string, string> symbolToSecurityId, CancellationToken ct = default)
    {
        if (symbolToSecurityId.Count == 0) return 0;

        var symbols     = symbolToSecurityId.Keys.ToArray();
        var securityIds = symbolToSecurityId.Values.ToArray();

        // unnest the two arrays in lockstep and UPDATE matching rows,
        // skipping rows where the value is already correct.
        const string sql = """
            UPDATE symbols s
            SET    dhan_security_id = u.security_id,
                   updated_at       = NOW()
            FROM   unnest(@Symbols::text[], @SecurityIds::text[]) AS u(symbol, security_id)
            WHERE  s.symbol = u.symbol
              AND  s.dhan_security_id IS DISTINCT FROM u.security_id
            """;

        await using var conn = await db.OpenConnectionAsync(ct);
        return await conn.ExecuteAsync(sql, new { Symbols = symbols, SecurityIds = securityIds });
    }
}
