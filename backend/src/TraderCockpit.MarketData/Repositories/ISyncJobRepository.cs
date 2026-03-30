using TraderCockpit.MarketData.Domain;

namespace TraderCockpit.MarketData.Repositories;

public interface ISyncJobRepository
{
    Task<SyncJob> CreateAsync(int symbolId, string symbol, DateTime from, DateTime to, CancellationToken ct = default);
    Task<SyncJob?> GetByIdAsync(Guid id, CancellationToken ct = default);
    Task<IReadOnlyList<SyncJob>> GetAllAsync(CancellationToken ct = default);
    Task UpdateInProgressAsync(Guid id, CancellationToken ct = default);
    Task UpdateCompletedAsync(Guid id, int barsFetched, CancellationToken ct = default);
    Task UpdateFailedAsync(Guid id, string errorMessage, CancellationToken ct = default);
}
