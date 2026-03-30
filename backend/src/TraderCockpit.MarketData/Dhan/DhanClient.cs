using System.Net.Http.Json;
using System.Threading.RateLimiting;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using TraderCockpit.MarketData.Domain;

namespace TraderCockpit.MarketData.Dhan;

/// <summary>
/// Thin async wrapper around the Dhan v2 intraday charts API.
/// Enforces a global token-bucket rate limit and retries on 429 with
/// exponential backoff.
/// </summary>
public sealed class DhanClient(
    HttpClient                  http,
    RateLimiter                 rateLimiter,
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
        string            securityId,
        string            exchangeSegment,
        DateTime          from,
        DateTime          to,
        CancellationToken ct = default)
    {
        var request = new IntradayRequest
        {
            SecurityId      = securityId,
            ExchangeSegment = exchangeSegment,
            FromDate        = from.ToString("yyyy-MM-dd"),
            ToDate          = to.ToString("yyyy-MM-dd"),
        };

        int attempt = 0;
        while (true)
        {
            // Acquire a token before every attempt.
            using var lease = await rateLimiter.AcquireAsync(permitCount: 1, ct);

            using var response = await http.PostAsJsonAsync(
                "/v2/charts/intraday", request, ct);

            if (response.IsSuccessStatusCode)
            {
                var payload = await response.Content
                    .ReadFromJsonAsync<IntradayResponse>(ct);

                if (payload is null || payload.Timestamp.Length == 0)
                    return [];

                var bars = new OhlcvBar[payload.Timestamp.Length];
                for (int i = 0; i < bars.Length; i++)
                {
                    bars[i] = new OhlcvBar(
                        Time:   DateTimeOffset.FromUnixTimeSeconds((long)payload.Timestamp[i]).UtcDateTime,
                        Open:   payload.Open[i],
                        High:   payload.High[i],
                        Low:    payload.Low[i],
                        Close:  payload.Close[i],
                        Volume: (long)payload.Volume[i]);
                }
                return bars;
            }

            var body = await response.Content.ReadAsStringAsync(ct);

            if ((int)response.StatusCode == 429 && attempt < _opts.MaxRetries)
            {
                var backoff = TimeSpan.FromMilliseconds(_opts.RetryBackoffMs * (1 << attempt));
                logger.LogWarning(
                    "Dhan 429 for {SecurityId} (attempt {Attempt}/{Max}). Backing off {Backoff}s.",
                    securityId, attempt + 1, _opts.MaxRetries, backoff.TotalSeconds);
                await Task.Delay(backoff, ct);
                attempt++;
                continue;
            }

            // DH-905 = no data for this date range (symbol listed after requested start, or gap).
            if ((int)response.StatusCode == 400)
            {
                var err = System.Text.Json.JsonSerializer.Deserialize<DhanErrorResponse>(body);
                if (err?.ErrorCode == "DH-905")
                    throw new DhanNoDataException(securityId, from, to);
            }

            logger.LogWarning(
                "Dhan API {Status} for {SecurityId} [{From}–{To}]: {Body}",
                (int)response.StatusCode, securityId, from.ToString("D"), to.ToString("D"), body);
            response.EnsureSuccessStatusCode();
        }
    }
}
