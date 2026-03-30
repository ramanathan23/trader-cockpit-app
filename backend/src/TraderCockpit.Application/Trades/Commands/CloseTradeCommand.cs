namespace TraderCockpit.Application.Trades.Commands;

public sealed record CloseTradeRequest(Guid TradeId, decimal ExitPrice, string Currency);
public sealed record CloseTradeResponse(Guid TradeId, string Status, decimal PnL);
