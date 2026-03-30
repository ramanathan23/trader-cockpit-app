using TraderCockpit.MarketData.Domain;

namespace TraderCockpit.MarketData.Repositories;

/// <summary>
/// Persistence contract for 1-minute OHLCV bars stored in the TimescaleDB
/// hypertable <c>price_data_1m</c> and its continuous-aggregate views.
/// </summary>
public interface IPriceDataRepository
{
    /// <summary>
    /// Returns the UTC timestamp of the latest stored bar for <paramref name="symbolId"/>,
    /// or <c>null</c> if the symbol has no data yet.
    /// Used by <c>SyncManager</c> to determine incremental vs. full backfill.
    /// </summary>
    Task<DateTime?> GetLatestTimeAsync(int symbolId, CancellationToken ct = default);

    /// <summary>
    /// Bulk-inserts OHLCV bars using the PostgreSQL COPY (binary) protocol for
    /// maximum throughput. Rows that already exist are silently skipped via a
    /// temp-table staging approach with <c>ON CONFLICT DO NOTHING</c>.
    /// </summary>
    Task BulkInsertAsync(
        int symbolId, IReadOnlyList<OhlcvBar> bars,
        CancellationToken ct = default);

    /// <summary>
    /// Queries bars from the appropriate continuous-aggregate view for the
    /// requested <paramref name="timeframe"/>.
    /// </summary>
    /// <param name="symbolId">Database primary key of the symbol.</param>
    /// <param name="timeframe">One of <c>1m</c>, <c>5m</c>, <c>15m</c>, <c>daily</c>.</param>
    /// <param name="from">Inclusive start of the query window (UTC).</param>
    /// <param name="to">Inclusive end of the query window (UTC).</param>
    /// <exception cref="ArgumentException">Thrown for an unrecognised timeframe string.</exception>
    Task<IReadOnlyList<OhlcvBar>> GetBarsAsync(
        int symbolId, string timeframe, DateTime from, DateTime to,
        CancellationToken ct = default);

    /// <summary>
    /// Truncates <c>price_data_1m</c>. Continuous aggregates are refreshed lazily.
    /// Intended for the reset endpoint only.
    /// </summary>
    Task ResetAsync(CancellationToken ct = default);
}
