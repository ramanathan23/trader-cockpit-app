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
            // daily reads from the raw hypertable (directly fetched from Dhan historical API)
            // rather than the continuous aggregate derived from 1m data.
            ["daily"] = "price_data_daily_raw",
        }.ToFrozenDictionary(StringComparer.OrdinalIgnoreCase);

    public async Task<DateTime?> GetLatestTimeAsync(int symbolId, CancellationToken ct = default)
    {
        // ORDER BY time DESC LIMIT 1 uses the uix_price_data_1m_time_symbol index efficiently
        // on TimescaleDB hypertables. MAX(time) triggers a full cross-chunk scan and is much slower.
        const string sql = """
            SELECT time FROM price_data_1m
            WHERE symbol_id = @SymbolId
            ORDER BY time DESC
            LIMIT 1
            """;
        await using var conn = await db.OpenConnectionAsync(ct);
        return await conn.ExecuteScalarAsync<DateTime?>(sql, new { SymbolId = symbolId });
    }

    public async Task<DateTime?> GetLatestDailyTimeAsync(int symbolId, CancellationToken ct = default)
    {
        const string sql = """
            SELECT time FROM price_data_daily_raw
            WHERE symbol_id = @SymbolId
            ORDER BY time DESC
            LIMIT 1
            """;
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
        await using var tx = await conn.BeginTransactionAsync(ct);

        // Stage into a temp table so we can use ON CONFLICT on the final insert.
        // ON COMMIT DROP requires an explicit transaction to behave correctly.
        await using (var cmd = conn.CreateCommand())
        {
            cmd.Transaction = tx;
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
        // CommandTimeout = 0 (unlimited) — large 5-year backfills (~130K rows) into a
        // TimescaleDB hypertable can exceed the default 30s Npgsql command timeout.
        await using (var cmd = conn.CreateCommand())
        {
            cmd.Transaction   = tx;
            cmd.CommandTimeout = 0;
            cmd.CommandText   = """
                INSERT INTO price_data_1m (time, symbol_id, open, high, low, close, volume)
                SELECT time, symbol_id, open, high, low, close, volume FROM tmp_price_import
                ON CONFLICT (time, symbol_id) DO NOTHING
                """;
            await cmd.ExecuteNonQueryAsync(ct);
        }

        await tx.CommitAsync(ct);
    }

    public async Task BulkInsertDailyAsync(int symbolId, IReadOnlyList<OhlcvBar> bars, CancellationToken ct = default)
    {
        if (bars.Count == 0) return;

        await using var conn = await db.OpenConnectionAsync(ct);
        await using var tx   = await conn.BeginTransactionAsync(ct);

        await using (var cmd = conn.CreateCommand())
        {
            cmd.Transaction = tx;
            cmd.CommandText = """
                CREATE TEMP TABLE tmp_daily_import (
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

        await using (var importer = await conn.BeginBinaryImportAsync(
            "COPY tmp_daily_import (time, symbol_id, open, high, low, close, volume) FROM STDIN (FORMAT BINARY)", ct))
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

        await using (var cmd = conn.CreateCommand())
        {
            cmd.Transaction    = tx;
            cmd.CommandTimeout = 0;
            cmd.CommandText    = """
                INSERT INTO price_data_daily_raw (time, symbol_id, open, high, low, close, volume)
                SELECT time, symbol_id, open, high, low, close, volume FROM tmp_daily_import
                ON CONFLICT (time, symbol_id) DO NOTHING
                """;
            await cmd.ExecuteNonQueryAsync(ct);
        }

        await tx.CommitAsync(ct);
    }

    public async Task ResetAsync(CancellationToken ct = default)
    {
        await using var conn = await db.OpenConnectionAsync(ct);
        // commandTimeout: 0 = unlimited — TRUNCATE on a large hypertable can be slow.
        // Truncate both price tables in one statement so they share the same lock cycle.
        await conn.ExecuteAsync(new CommandDefinition(
            "TRUNCATE TABLE price_data_1m, price_data_daily_raw",
            commandTimeout: 0, cancellationToken: ct));
    }

    public async Task<IReadOnlyList<OhlcvBar>> GetBarsAsync(
        int symbolId, string timeframe, DateTime from, DateTime to,
        CancellationToken ct = default)
    {
        if (!_viewMap.TryGetValue(timeframe, out var view))
            throw new ArgumentException($"Unknown timeframe '{timeframe}'. Valid: 1m, 5m, 15m, daily.", nameof(timeframe));

        // price_data_1m and price_data_daily_raw use "time"; the continuous aggregate
        // views (5m, 15m) use "bucket".
        var timeCol = (timeframe == "1m" || timeframe == "daily") ? "time" : "bucket";
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
