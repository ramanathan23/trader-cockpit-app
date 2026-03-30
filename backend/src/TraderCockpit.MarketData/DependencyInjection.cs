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
        // Make Dapper map snake_case columns → PascalCase properties automatically.
        DefaultTypeMap.MatchNamesWithUnderscores = true;

        // ── TimescaleDB connection ────────────────────────────────────────────
        var connString = configuration.GetConnectionString("TimescaleDb")
            ?? throw new InvalidOperationException("Missing connection string 'TimescaleDb'.");

        services.AddSingleton(NpgsqlDataSource.Create(connString));

        // ── Dhan API client ───────────────────────────────────────────────────
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

        // ── Work queue (unbounded channel — writes from SyncManager, reads from BackgroundService) ─
        services.AddSingleton(Channel.CreateUnbounded<SyncRequest>(
            new UnboundedChannelOptions { SingleReader = false, SingleWriter = false }));

        // ── Repositories ──────────────────────────────────────────────────────
        services.AddScoped<ISymbolRepository,   SymbolRepository>();
        services.AddScoped<IPriceDataRepository, PriceDataRepository>();
        services.AddScoped<ISyncJobRepository,  SyncJobRepository>();

        // ── Services ──────────────────────────────────────────────────────────
        services.AddHttpClient();   // default IHttpClientFactory for DhanSecurityIdSeeder

        services.AddScoped<SyncManager>();
        services.AddScoped<SymbolSeeder>();
        services.AddScoped<DhanSecurityIdSeeder>();
        services.AddSingleton<DatabaseInitializer>();
        services.AddHostedService<IngestionBackgroundService>();

        return services;
    }
}
