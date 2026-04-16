// Option chain domain — types for option chain display.

export interface OptionStrike {
  strike_price: number;
  // Call side
  call_ltp:     number | null;
  call_iv:      number | null;
  call_delta:   number | null;
  call_theta:   number | null;
  call_gamma:   number | null;
  call_vega:    number | null;
  call_oi:      number | null;
  call_volume:  number | null;
  call_bid:     number | null;
  call_ask:     number | null;
  // Put side
  put_ltp:      number | null;
  put_iv:       number | null;
  put_delta:    number | null;
  put_theta:    number | null;
  put_gamma:    number | null;
  put_vega:     number | null;
  put_oi:       number | null;
  put_volume:   number | null;
  put_bid:      number | null;
  put_ask:      number | null;
}

export interface OptionChainResponse {
  symbol:       string;
  expiry:       string;
  spot_price:   number;
  strikes:      OptionStrike[];
}

export interface ExpiryListResponse {
  symbol:   string;
  expiries: string[];
}
