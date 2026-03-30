using TraderCockpit.MarketData.Domain;

namespace TraderCockpit.MarketData.Repositories;

/// <summary>
/// Persistence contract for <see cref="MarketSymbol"/> rows in the <c>symbols</c> table.
/// </summary>
public interface ISymbolRepository
{
    /// <summary>
    /// Upserts all symbols using <c>INSERT … ON CONFLICT (symbol) DO UPDATE</c>.
    /// Safe to call repeatedly; does not touch <c>dhan_security_id</c>.
    /// </summary>
    Task UpsertManyAsync(IEnumerable<MarketSymbol> symbols, CancellationToken ct = default);

    /// <summary>
    /// Returns all active symbols (<c>is_active = TRUE</c>), regardless of whether
    /// their <c>dhan_security_id</c> has been mapped.
    /// </summary>
    Task<IReadOnlyList<MarketSymbol>> GetActiveAsync(CancellationToken ct = default);

    /// <summary>
    /// Returns active symbols that have a non-null <c>dhan_security_id</c> —
    /// i.e. those eligible for data ingestion (see <see cref="MarketSymbol.CanBeSynced"/>).
    /// </summary>
    Task<IReadOnlyList<MarketSymbol>> GetSyncableAsync(CancellationToken ct = default);

    /// <summary>
    /// Updates the <c>dhan_security_id</c> for a single symbol by its ticker.
    /// </summary>
    Task SetDhanSecurityIdAsync(
        string symbol, string dhanSecurityId, CancellationToken ct = default);

    /// <summary>
    /// Bulk-updates <c>dhan_security_id</c> by matching on trading symbol.
    /// Uses PostgreSQL <c>unnest()</c> for efficiency; skips no-op updates via
    /// <c>IS DISTINCT FROM</c>.
    /// </summary>
    /// <returns>Number of rows actually changed.</returns>
    Task<int> BulkSetDhanSecurityIdBySymbolAsync(
        IDictionary<string, string> symbolToSecurityId, CancellationToken ct = default);
}
