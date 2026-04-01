using System.Threading.RateLimiting;
using Dapper;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Npgsql;
using TraderCockpit.MarketData.Dhan;
using TraderCockpit.MarketData.Database;
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

        var connString = configuration.GetConnectionString("TimescaleDb")
            ?? throw new InvalidOperationException("Missing connection string 'TimescaleDb'.");

        var dataSourceBuilder = new NpgsqlDataSourceBuilder(connString);
        dataSourceBuilder.ConnectionStringBuilder.CommandTimeout = 300; // 5 min — heavy parallel writes
        services.AddSingleton(dataSourceBuilder.Build());

        // Dhan API client + rate limiter
        services.Configure<DhanOptions>(configuration.GetSection(DhanOptions.SectionName));

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
            http.Timeout     = TimeSpan.FromSeconds(300); // 5 min — large 90-day batches can be slow
            http.DefaultRequestHeaders.Add("access-token", opts.AccessToken);
            http.DefaultRequestHeaders.Add("client-id",    opts.ClientId);
        });

        // Repositories — singleton because they are stateless wrappers around the
        // singleton NpgsqlDataSource and are used by background tasks that outlive
        // the HTTP request scope.
        services.AddSingleton<ISymbolRepository,   SymbolRepository>();
        services.AddSingleton<IPriceDataRepository, PriceDataRepository>();
        services.AddSingleton<ISyncRunRepository,   SyncRunRepository>();

        // SyncManager orchestrates runs; singleton for the same background-task reason.
        services.AddSingleton<SyncManager>();

        // Startup services
        services.AddHttpClient();   // default IHttpClientFactory for DhanSecurityIdSeeder
        services.AddScoped<SymbolSeeder>();
        services.AddScoped<DhanSecurityIdSeeder>();
        services.AddSingleton<DatabaseInitializer>();

        return services;
    }
}
