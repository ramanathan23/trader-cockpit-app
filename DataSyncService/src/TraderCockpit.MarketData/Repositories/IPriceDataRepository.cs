using TraderCockpit.MarketData.Domain;

namespace TraderCockpit.MarketData.Repositories;

/// <summary>
/// Persistence contract for 1-minute OHLCV bars stored in the TimescaleDB
/// hypertable <c>price_data_1m</c> and its continuous-aggregate views.
/// </summary>
public interface IPriceDataRepository
{
    /// <summary>
    /// Returns the UTC timestamp of the latest stored 1-minute bar for <paramref name="symbolId"/>,
    /// or <c>null</c> if the symbol has no 1m data yet.
    /// </summary>
    Task<DateTime?> GetLatestTimeAsync(int symbolId, CancellationToken ct = default);

    /// <summary>
    /// Returns the UTC timestamp of the latest stored daily bar in
    /// <c>price_data_daily_raw</c> for <paramref name="symbolId"/>,
    /// or <c>null</c> if the symbol has no daily data yet.
    /// </summary>
    Task<DateTime?> GetLatestDailyTimeAsync(int symbolId, CancellationToken ct = default);

    /// <summary>
    /// Bulk-inserts 1-minute OHLCV bars into <c>price_data_1m</c> using the
    /// PostgreSQL COPY protocol. Existing rows are silently skipped.
    /// </summary>
    Task BulkInsertAsync(
        int symbolId, IReadOnlyList<OhlcvBar> bars,
        CancellationToken ct = default);

    /// <summary>
    /// Bulk-inserts daily OHLCV bars into <c>price_data_daily_raw</c> using the
    /// PostgreSQL COPY protocol. Existing rows are silently skipped.
    /// </summary>
    Task BulkInsertDailyAsync(
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
