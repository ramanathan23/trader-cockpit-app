using TraderCockpit.Domain.Common;
using TraderCockpit.Domain.Events;
using TraderCockpit.Domain.ValueObjects;

namespace TraderCockpit.Domain.Entities;

public enum TradeDirection { Buy, Sell }
public enum TradeStatus { Open, Closed }

public sealed class Trade : Entity
{
    public Ticker Ticker { get; private set; }
    public TradeDirection Direction { get; private set; }
    public decimal Quantity { get; private set; }
    public Money EntryPrice { get; private set; }
    public Money? ExitPrice { get; private set; }
    public TradeStatus Status { get; private set; }
    public DateTime OpenedAt { get; private set; }
    public DateTime? ClosedAt { get; private set; }
    public string Notes { get; private set; }

    private Trade() { Ticker = null!; EntryPrice = null!; Notes = string.Empty; } // EF Core

    public static Trade Open(Ticker ticker, TradeDirection direction, decimal quantity, Money entryPrice, string notes = "")
    {
        if (quantity <= 0) throw new ArgumentException("Quantity must be positive.");

        var trade = new Trade
        {
            Ticker = ticker,
            Direction = direction,
            Quantity = quantity,
            EntryPrice = entryPrice,
            Status = TradeStatus.Open,
            OpenedAt = DateTime.UtcNow,
            Notes = notes
        };

        trade.Raise(new TradeOpenedEvent(trade.Id, ticker.Symbol, direction, quantity, entryPrice));
        return trade;
    }

    public void Close(Money exitPrice)
    {
        if (Status == TradeStatus.Closed) throw new InvalidOperationException("Trade is already closed.");

        ExitPrice = exitPrice;
        Status = TradeStatus.Closed;
        ClosedAt = DateTime.UtcNow;

        Raise(new TradeClosedEvent(Id, Ticker.Symbol, exitPrice, PnL()));
    }

    public decimal PnL()
    {
        if (ExitPrice is null) return 0;
        var diff = ExitPrice.Amount - EntryPrice.Amount;
        return Direction == TradeDirection.Buy ? diff * Quantity : -diff * Quantity;
    }
}
