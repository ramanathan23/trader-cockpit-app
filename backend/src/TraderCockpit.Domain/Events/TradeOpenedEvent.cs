using TraderCockpit.Domain.Common;
using TraderCockpit.Domain.Entities;
using TraderCockpit.Domain.ValueObjects;

namespace TraderCockpit.Domain.Events;

public sealed record TradeOpenedEvent(
    Guid TradeId,
    string Symbol,
    TradeDirection Direction,
    decimal Quantity,
    Money EntryPrice
) : IDomainEvent
{
    public Guid EventId { get; } = Guid.NewGuid();
    public DateTime OccurredAt { get; } = DateTime.UtcNow;
}
