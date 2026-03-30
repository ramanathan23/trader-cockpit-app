using Microsoft.EntityFrameworkCore;
using TraderCockpit.Domain.Entities;

namespace TraderCockpit.Infrastructure.Persistence;

public sealed class AppDbContext(DbContextOptions<AppDbContext> options) : DbContext(options)
{
    public DbSet<Trade> Trades => Set<Trade>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<Trade>(b =>
        {
            b.HasKey(t => t.Id);
            b.OwnsOne(t => t.Ticker);
            b.OwnsOne(t => t.EntryPrice);
            b.OwnsOne(t => t.ExitPrice);
        });
    }
}
