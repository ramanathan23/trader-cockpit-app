using TraderCockpit.MarketData.Domain;

namespace TraderCockpit.MarketData.Repositories;

public interface ISymbolRepository
{
    Task UpsertManyAsync(IEnumerable<MarketSymbol> symbols, CancellationToken ct = default);
    Task<IReadOnlyList<MarketSymbol>> GetActiveAsync(CancellationToken ct = default);
    Task<IReadOnlyList<MarketSymbol>> GetSyncableAsync(CancellationToken ct = default);  // IsActive + DhanSecurityId IS NOT NULL
    Task SetDhanSecurityIdAsync(string symbol, string dhanSecurityId, CancellationToken ct = default);

    /// <summary>
    /// Bulk-updates <c>dhan_security_id</c> by matching on trading symbol.
    /// Returns the number of rows actually changed.
    /// </summary>
    Task<int> BulkSetDhanSecurityIdBySymbolAsync(
        IDictionary<string, string> symbolToSecurityId, CancellationToken ct = default);
}
