using TraderCockpit.Application.Common;
using TraderCockpit.Domain.Entities;
using TraderCockpit.Domain.Repositories;

namespace TraderCockpit.Application.Trades.Queries;

public sealed record TradeDto(
    Guid Id,
    string Symbol,
    string Direction,
    decimal Quantity,
    decimal EntryPrice,
    decimal? ExitPrice,
    string Currency,
    string Status,
    decimal PnL,
    DateTime OpenedAt,
    DateTime? ClosedAt,
    string Notes);

public sealed record GetTradesRequest(string? Status = null);
public sealed record GetTradesResponse(IReadOnlyList<TradeDto> Trades);

public sealed class GetTradesUseCase(ITradeRepository repository)
    : IUseCase<GetTradesRequest, GetTradesResponse>
{
    public async Task<GetTradesResponse> ExecuteAsync(GetTradesRequest request, CancellationToken ct = default)
    {
        var trades = await repository.GetAllAsync(ct);

        var filtered = request.Status is null
            ? trades
            : trades.Where(t => t.Status.ToString().Equals(request.Status, StringComparison.OrdinalIgnoreCase)).ToList();

        var dtos = filtered.Select(t => new TradeDto(
            t.Id,
            t.Ticker.Symbol,
            t.Direction.ToString(),
            t.Quantity,
            t.EntryPrice.Amount,
            t.ExitPrice?.Amount,
            t.EntryPrice.Currency,
            t.Status.ToString(),
            t.PnL(),
            t.OpenedAt,
            t.ClosedAt,
            t.Notes)).ToList();

        return new GetTradesResponse(dtos);
    }
}
