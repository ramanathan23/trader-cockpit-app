using System.Net.Http.Json;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using TraderCockpit.MarketData.Domain;

namespace TraderCockpit.MarketData.Dhan;

/// <summary>
/// Thin async wrapper around the Dhan v2 intraday charts API.
/// Rate-limiting is handled by the caller (IngestionBackgroundService).
/// </summary>
public sealed class DhanClient(
    HttpClient                  http,
    IOptions<DhanOptions>       options,
    ILogger<DhanClient>         logger)
{
    private readonly DhanOptions _opts = options.Value;

    /// <summary>
    /// Fetches 1-minute OHLCV bars for <paramref name="securityId"/> between
    /// <paramref name="from"/> and <paramref name="to"/> (inclusive, UTC).
    /// Dhan caps each request at ~30 days; the caller is responsible for batching.
    /// </summary>
    public async Task<IReadOnlyList<OhlcvBar>> GetIntradayAsync(
        string           securityId,
        string           exchangeSegment,
        DateTime         from,
        DateTime         to,
        CancellationToken ct = default)
    {
        var request = new IntradayRequest
        {
            SecurityId      = securityId,
            ExchangeSegment = exchangeSegment,
            FromDate        = from.ToString("yyyy-MM-dd"),
            ToDate          = to.ToString("yyyy-MM-dd"),
        };

        using var response = await http.PostAsJsonAsync(
            "/v2/charts/intraday", request, ct);

        if (!response.IsSuccessStatusCode)
        {
            var body = await response.Content.ReadAsStringAsync(ct);
            logger.LogWarning(
                "Dhan API {Status} for {SecurityId} [{From}–{To}]: {Body}",
                (int)response.StatusCode, securityId, from.ToString("D"), to.ToString("D"), body);
            response.EnsureSuccessStatusCode();   // rethrows as HttpRequestException
        }

        var payload = await response.Content
            .ReadFromJsonAsync<IntradayResponse>(ct);

        if (payload is null || payload.Timestamp.Length == 0)
            return [];

        var bars = new OhlcvBar[payload.Timestamp.Length];
        for (int i = 0; i < bars.Length; i++)
        {
            bars[i] = new OhlcvBar(
                Time:   DateTimeOffset.FromUnixTimeSeconds(payload.Timestamp[i]).UtcDateTime,
                Open:   payload.Open[i],
                High:   payload.High[i],
                Low:    payload.Low[i],
                Close:  payload.Close[i],
                Volume: payload.Volume[i]);
        }

        return bars;
    }
}
