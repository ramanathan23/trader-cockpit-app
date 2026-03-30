using TraderCockpit.Application.Common;
using TraderCockpit.Domain.Entities;
using TraderCockpit.Domain.Repositories;
using TraderCockpit.Domain.ValueObjects;

namespace TraderCockpit.Application.Trades.Commands;

public sealed class OpenTradeUseCase(ITradeRepository repository)
    : IUseCase<OpenTradeRequest, OpenTradeResponse>
{
    public async Task<OpenTradeResponse> ExecuteAsync(OpenTradeRequest request, CancellationToken ct = default)
    {
        var direction = Enum.Parse<TradeDirection>(request.Direction, ignoreCase: true);
        var trade = Trade.Open(
            new Ticker(request.Symbol),
            direction,
            request.Quantity,
            new Money(request.EntryPrice, request.Currency),
            request.Notes);

        await repository.AddAsync(trade, ct);
        await repository.SaveChangesAsync(ct);

        return new OpenTradeResponse(trade.Id, trade.Ticker.Symbol, trade.Status.ToString());
    }
}
