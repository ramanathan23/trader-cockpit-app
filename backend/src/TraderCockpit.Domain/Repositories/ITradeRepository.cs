using TraderCockpit.Domain.Entities;

namespace TraderCockpit.Domain.Repositories;

public interface ITradeRepository
{
    Task<Trade?> GetByIdAsync(Guid id, CancellationToken ct = default);
    Task<IReadOnlyList<Trade>> GetAllAsync(CancellationToken ct = default);
    Task AddAsync(Trade trade, CancellationToken ct = default);
    Task SaveChangesAsync(CancellationToken ct = default);
}
