using TraderCockpit.MarketData.Domain;

namespace TraderCockpit.MarketData.Repositories;

public interface ISymbolRepository
{
    Task UpsertManyAsync(IEnumerable<MarketSymbol> symbols, CancellationToken ct = default);
    Task<IReadOnlyList<MarketSymbol>> GetActiveAsync(CancellationToken ct = default);
    Task<IReadOnlyList<MarketSymbol>> GetSyncableAsync(CancellationToken ct = default);  // IsActive + DhanSecurityId IS NOT NULL
    Task SetDhanSecurityIdAsync(string symbol, string dhanSecurityId, CancellationToken ct = default);
}
