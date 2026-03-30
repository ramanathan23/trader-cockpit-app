namespace TraderCockpit.Domain.ValueObjects;

public sealed record Ticker
{
    public string Symbol { get; }

    public Ticker(string symbol)
    {
        if (string.IsNullOrWhiteSpace(symbol)) throw new ArgumentException("Ticker symbol cannot be empty.");
        Symbol = symbol.ToUpperInvariant();
    }

    public override string ToString() => Symbol;
}
