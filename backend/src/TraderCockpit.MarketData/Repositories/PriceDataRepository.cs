using System.Collections.Frozen;
using Dapper;
using Npgsql;
using NpgsqlTypes;
using TraderCockpit.MarketData.Domain;

namespace TraderCockpit.MarketData.Repositories;

public sealed class PriceDataRepository(NpgsqlDataSource db) : IPriceDataRepository
{
    private static readonly FrozenDictionary<string, string> _viewMap =
        new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
        {
            ["1m"]    = "price_data_1m",
            ["5m"]    = "price_data_5m",
            ["15m"]   = "price_data_15m",
            ["daily"] = "price_data_daily",
        }.ToFrozenDictionary(StringComparer.OrdinalIgnoreCase);

    public async Task<DateTime?> GetLatestTimeAsync(int symbolId, CancellationToken ct = default)
    {
        const string sql = "SELECT MAX(time) FROM price_data_1m WHERE symbol_id = @SymbolId";
        await using var conn = await db.OpenConnectionAsync(ct);
        return await conn.ExecuteScalarAsync<DateTime?>(sql, new { SymbolId = symbolId });
    }

    /// <summary>
    /// Uses <c>NpgsqlBinaryImporter</c> (COPY protocol) for maximum throughput,
    /// then moves rows from a temp table with ON CONFLICT DO NOTHING to handle
    /// any re-ingested overlap without violating the unique index.
    /// </summary>
    public async Task BulkInsertAsync(int symbolId, IReadOnlyList<OhlcvBar> bars, CancellationToken ct = default)
    {
        if (bars.Count == 0) return;

        await using var conn = await db.OpenConnectionAsync(ct);

        // Stage into a temp table so we can use ON CONFLICT on the final insert.
        await using (var cmd = conn.CreateCommand())
        {
            cmd.CommandText = """
                CREATE TEMP TABLE tmp_price_import (
                    time      TIMESTAMPTZ   NOT NULL,
                    symbol_id INTEGER       NOT NULL,
                    open      NUMERIC(14,4) NOT NULL,
                    high      NUMERIC(14,4) NOT NULL,
                    low       NUMERIC(14,4) NOT NULL,
                    close     NUMERIC(14,4) NOT NULL,
                    volume    BIGINT        NOT NULL
                ) ON COMMIT DROP
                """;
            await cmd.ExecuteNonQueryAsync(ct);
        }

        // Binary COPY into temp — fastest possible write path.
        await using (var importer = await conn.BeginBinaryImportAsync(
            "COPY tmp_price_import (time, symbol_id, open, high, low, close, volume) FROM STDIN (FORMAT BINARY)", ct))
        {
            foreach (var bar in bars)
            {
                await importer.StartRowAsync(ct);
                await importer.WriteAsync(bar.Time,   NpgsqlDbType.TimestampTz, ct);
                await importer.WriteAsync(symbolId,   NpgsqlDbType.Integer,     ct);
                await importer.WriteAsync(bar.Open,   NpgsqlDbType.Numeric,     ct);
                await importer.WriteAsync(bar.High,   NpgsqlDbType.Numeric,     ct);
                await importer.WriteAsync(bar.Low,    NpgsqlDbType.Numeric,     ct);
                await importer.WriteAsync(bar.Close,  NpgsqlDbType.Numeric,     ct);
                await importer.WriteAsync(bar.Volume, NpgsqlDbType.Bigint,      ct);
            }
            await importer.CompleteAsync(ct);
        }

        // Move from temp → hypertable, skipping any existing rows.
        await using (var cmd = conn.CreateCommand())
        {
            cmd.CommandText = """
                INSERT INTO price_data_1m (time, symbol_id, open, high, low, close, volume)
                SELECT time, symbol_id, open, high, low, close, volume FROM tmp_price_import
                ON CONFLICT (time, symbol_id) DO NOTHING
                """;
            await cmd.ExecuteNonQueryAsync(ct);
        }
    }

    public async Task ResetAsync(CancellationToken ct = default)
    {
        await using var conn = await db.OpenConnectionAsync(ct);
        await conn.ExecuteAsync("TRUNCATE TABLE price_data_1m");
    }

    public async Task<IReadOnlyList<OhlcvBar>> GetBarsAsync(
        int symbolId, string timeframe, DateTime from, DateTime to,
        CancellationToken ct = default)
    {
        if (!_viewMap.TryGetValue(timeframe, out var view))
            throw new ArgumentException($"Unknown timeframe '{timeframe}'. Valid: 1m, 5m, 15m, daily.", nameof(timeframe));

        // The bucket/time column name differs per view.
        var timeCol = timeframe == "1m" ? "time" : "bucket";
        var sql = $"""
            SELECT {timeCol} AS time, open, high, low, close, volume
            FROM   {view}
            WHERE  symbol_id = @SymbolId
              AND  {timeCol} BETWEEN @From AND @To
            ORDER BY {timeCol}
            """;

        await using var conn = await db.OpenConnectionAsync(ct);
        return (await conn.QueryAsync<OhlcvBar>(sql, new { SymbolId = symbolId, From = from, To = to })).AsList();
    }
}
