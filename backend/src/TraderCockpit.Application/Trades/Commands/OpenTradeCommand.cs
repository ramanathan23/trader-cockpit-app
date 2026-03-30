using TraderCockpit.Domain.Entities;

namespace TraderCockpit.Application.Trades.Commands;

public sealed record OpenTradeRequest(
    string Symbol,
    string Direction,
    decimal Quantity,
    decimal EntryPrice,
    string Currency,
    string Notes = "");

public sealed record OpenTradeResponse(Guid TradeId, string Symbol, string Status);
