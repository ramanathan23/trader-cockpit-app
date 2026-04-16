// Daily chart domain — OHLC bar type for candlestick rendering.

export interface OHLCBar {
  time:   string; // YYYY-MM-DD
  open:   number;
  high:   number;
  low:    number;
  close:  number;
  volume: number;
}
