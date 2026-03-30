using TraderCockpit.Domain.Common;
using TraderCockpit.Domain.ValueObjects;

namespace TraderCockpit.Domain.Events;

public sealed record TradeClosedEvent(
    Guid TradeId,
    string Symbol,
    Money ExitPrice,
    decimal PnL
) : IDomainEvent
{
    public Guid EventId { get; } = Guid.NewGuid();
    public DateTime OccurredAt { get; } = DateTime.UtcNow;
}
