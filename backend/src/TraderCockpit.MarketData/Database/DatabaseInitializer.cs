using System.Reflection;
using Dapper;
using Microsoft.Extensions.Logging;
using Npgsql;

namespace TraderCockpit.MarketData.Database;

/// <summary>
/// Reads the embedded <c>schema.sql</c> and runs it against TimescaleDB on startup.
/// All statements use <c>IF NOT EXISTS</c> / <c>if_not_exists =&gt; TRUE</c>, so
/// re-running is safe (idempotent).
/// </summary>
public sealed class DatabaseInitializer(
    NpgsqlDataSource          db,
    ILogger<DatabaseInitializer> logger)
{
    public async Task InitializeAsync(CancellationToken ct = default)
    {
        logger.LogInformation("Running TimescaleDB schema initializer...");

        var sql = ReadEmbeddedSchema();

        await using var conn = await db.OpenConnectionAsync(ct);

        // Dapper's Execute handles multi-statement scripts separated by semicolons
        // when the underlying provider supports it (Npgsql does).
        await conn.ExecuteAsync(sql);

        logger.LogInformation("Schema initialization complete.");
    }

    private static string ReadEmbeddedSchema()
    {
        using var stream = Assembly.GetExecutingAssembly()
            .GetManifestResourceStream("TraderCockpit.MarketData.Database.schema.sql")
            ?? throw new InvalidOperationException(
                "Embedded resource 'TraderCockpit.MarketData.Database.schema.sql' not found.");

        using var reader = new StreamReader(stream);
        return reader.ReadToEnd();
    }
}
