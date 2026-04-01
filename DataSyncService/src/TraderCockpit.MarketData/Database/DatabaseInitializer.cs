using System.Reflection;
using Dapper;
using Microsoft.Extensions.Logging;
using Npgsql;

namespace TraderCockpit.MarketData.Database;

/// <summary>
/// Reads the embedded schema.sql and runs each statement individually against
/// TimescaleDB on startup. Running statements one-by-one avoids deadlocks caused
/// by TimescaleDB acquiring internal locks across multiple DDL operations in a
/// single multi-statement batch.
/// All statements use IF NOT EXISTS / if_not_exists => TRUE so re-running is safe.
/// </summary>
public sealed class DatabaseInitializer(
    NpgsqlDataSource             db,
    ILogger<DatabaseInitializer> logger)
{
    public async Task InitializeAsync(CancellationToken ct = default)
    {
        logger.LogInformation("Running TimescaleDB schema initializer...");

        var statements = SplitStatements(ReadEmbeddedSchema());

        await using var conn = await db.OpenConnectionAsync(ct);

        foreach (var sql in statements)
        {
            await conn.ExecuteAsync(sql);
        }

        logger.LogInformation("Schema initialization complete ({Count} statements).", statements.Count);
    }

    /// <summary>
    /// Splits a SQL script on semicolons, discarding empty / whitespace-only segments.
    /// </summary>
    private static IReadOnlyList<string> SplitStatements(string script)
        => script
            .Split(';', StringSplitOptions.RemoveEmptyEntries)
            .Select(s => s.Trim())
            .Where(s => s.Length > 0)
            .ToList();

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
