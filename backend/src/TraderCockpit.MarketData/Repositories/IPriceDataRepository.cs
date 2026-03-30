using TraderCockpit.MarketData.Domain;

namespace TraderCockpit.MarketData.Repositories;

public interface IPriceDataRepository
{
    /// <summary>Returns the UTC timestamp of the latest stored bar for <paramref name="symbolId"/>, or null if none.</summary>
    Task<DateTime?> GetLatestTimeAsync(int symbolId, CancellationToken ct = default);

    /// <summary>
    /// Bulk-inserts bars using <c>NpgsqlBinaryImporter</c> (fastest possible path).
    /// Duplicates are silently skipped via <c>ON CONFLICT DO NOTHING</c> via a staging approach.
    /// </summary>
    Task BulkInsertAsync(int symbolId, IReadOnlyList<OhlcvBar> bars, CancellationToken ct = default);

    /// <summary>Query OHLCV bars from the appropriate continuous-aggregate view.</summary>
    Task<IReadOnlyList<OhlcvBar>> GetBarsAsync(
        int symbolId, string timeframe, DateTime from, DateTime to,
        CancellationToken ct = default);
}
