using TraderCockpit.Application.Common;
using TraderCockpit.Domain.Repositories;
using TraderCockpit.Domain.ValueObjects;

namespace TraderCockpit.Application.Trades.Commands;

public sealed class CloseTradeUseCase(ITradeRepository repository)
    : IUseCase<CloseTradeRequest, CloseTradeResponse>
{
    public async Task<CloseTradeResponse> ExecuteAsync(CloseTradeRequest request, CancellationToken ct = default)
    {
        var trade = await repository.GetByIdAsync(request.TradeId, ct)
            ?? throw new KeyNotFoundException($"Trade {request.TradeId} not found.");

        trade.Close(new Money(request.ExitPrice, request.Currency));
        await repository.SaveChangesAsync(ct);

        return new CloseTradeResponse(trade.Id, trade.Status.ToString(), trade.PnL());
    }
}
