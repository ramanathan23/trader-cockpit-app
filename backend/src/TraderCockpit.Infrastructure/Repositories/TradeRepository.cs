using Microsoft.EntityFrameworkCore;
using TraderCockpit.Domain.Entities;
using TraderCockpit.Domain.Repositories;
using TraderCockpit.Infrastructure.Persistence;

namespace TraderCockpit.Infrastructure.Repositories;

public sealed class TradeRepository(AppDbContext db) : ITradeRepository
{
    public Task<Trade?> GetByIdAsync(Guid id, CancellationToken ct = default) =>
        db.Trades.FirstOrDefaultAsync(t => t.Id == id, ct);

    public async Task<IReadOnlyList<Trade>> GetAllAsync(CancellationToken ct = default) =>
        await db.Trades.ToListAsync(ct);

    public async Task AddAsync(Trade trade, CancellationToken ct = default) =>
        await db.Trades.AddAsync(trade, ct);

    public Task SaveChangesAsync(CancellationToken ct = default) =>
        db.SaveChangesAsync(ct);
}
