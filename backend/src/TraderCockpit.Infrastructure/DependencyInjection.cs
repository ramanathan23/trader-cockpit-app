using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using TraderCockpit.Application.Common;
using TraderCockpit.Application.Trades.Commands;
using TraderCockpit.Application.Trades.Queries;
using TraderCockpit.Domain.Repositories;
using TraderCockpit.Infrastructure.Persistence;
using TraderCockpit.Infrastructure.Repositories;

namespace TraderCockpit.Infrastructure;

public static class DependencyInjection
{
    public static IServiceCollection AddInfrastructure(this IServiceCollection services)
    {
        services.AddDbContext<AppDbContext>(opt =>
            opt.UseInMemoryDatabase("TraderCockpit"));

        services.AddScoped<ITradeRepository, TradeRepository>();

        return services;
    }

    public static IServiceCollection AddApplication(this IServiceCollection services)
    {
        services.AddScoped<IUseCase<OpenTradeRequest, OpenTradeResponse>, OpenTradeUseCase>();
        services.AddScoped<IUseCase<CloseTradeRequest, CloseTradeResponse>, CloseTradeUseCase>();
        services.AddScoped<IUseCase<GetTradesRequest, GetTradesResponse>, GetTradesUseCase>();

        return services;
    }
}
