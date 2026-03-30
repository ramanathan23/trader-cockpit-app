using System.Threading.Channels;
using System.Threading.RateLimiting;
using Dapper;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Npgsql;
using TraderCockpit.MarketData.Dhan;
using TraderCockpit.MarketData.Database;
using TraderCockpit.MarketData.Domain;
using TraderCockpit.MarketData.Repositories;
using TraderCockpit.MarketData.Services;

namespace TraderCockpit.MarketData;

public static class DependencyInjection
{
    public static IServiceCollection AddMarketData(
        this IServiceCollection services,
        IConfiguration          configuration)
    {
        // Make Dapper map snake_case columns to PascalCase properties automatically.
        DefaultTypeMap.MatchNamesWithUnderscores = true;

        // TimescaleDB connection pool (singleton — one pool for the process lifetime).
        var connString = configuration.GetConnectionString("TimescaleDb")
            ?? throw new InvalidOperationException("Missing connection string 'TimescaleDb'.");

        services.AddSingleton(NpgsqlDataSource.Create(connString));

        // Dhan API client
        services.Configure<DhanOptions>(configuration.GetSection(DhanOptions.SectionName));

        // Global token-bucket rate limiter shared across all workers.
        services.AddSingleton<RateLimiter>(sp =>
        {
            var opts = configuration
                .GetSection(DhanOptions.SectionName)
                .Get<DhanOptions>() ?? new();

            return new TokenBucketRateLimiter(new TokenBucketRateLimiterOptions
            {
                TokenLimit           = opts.RateLimitPerSecond,
                ReplenishmentPeriod  = TimeSpan.FromSeconds(1),
                TokensPerPeriod      = opts.RateLimitPerSecond,
                QueueProcessingOrder = QueueProcessingOrder.OldestFirst,
                QueueLimit           = int.MaxValue,
                AutoReplenishment    = true,
            });
        });

        services.AddHttpClient<DhanClient>((sp, http) =>
        {
            var opts = configuration
                .GetSection(DhanOptions.SectionName)
                .Get<DhanOptions>() ?? new();

            http.BaseAddress = new Uri(opts.BaseUrl);
            http.DefaultRequestHeaders.Add("access-token", opts.AccessToken);
            http.DefaultRequestHeaders.Add("client-id",    opts.ClientId);
        });

        // Work queue: SyncManager writes, IngestionBackgroundService workers read.
        services.AddSingleton(Channel.CreateUnbounded<SyncRequest>(
            new UnboundedChannelOptions { SingleReader = false, SingleWriter = false }));

        // Repositories are singletons because they are stateless wrappers around the
        // singleton NpgsqlDataSource (open/close a connection per method call, hold no
        // per-request state). Singleton lifetime is required so that SyncManager's
        // background scheduling task — which outlives the HTTP request scope — can
        // safely call repository methods without hitting a disposed scope error.
        services.AddSingleton<ISymbolRepository,   SymbolRepository>();
        services.AddSingleton<IPriceDataRepository, PriceDataRepository>();
        services.AddSingleton<ISyncJobRepository,  SyncJobRepository>();

        // Singleton for the same reason: ScheduleAllAsync runs after the HTTP request
        // scope is disposed.
        services.AddSingleton<SyncManager>();

        // Seeders and initializer only run at startup inside an explicit scope.
        services.AddHttpClient();   // default IHttpClientFactory for DhanSecurityIdSeeder
        services.AddScoped<SymbolSeeder>();
        services.AddScoped<DhanSecurityIdSeeder>();
        services.AddSingleton<DatabaseInitializer>();

        services.AddHostedService<IngestionBackgroundService>();

        return services;
    }
}
