import type { ZerodhaAccountStatus } from '@/components/admin/adminTypes';

export type AccountTab = 'configure' | 'overall' | 'individual';
export type AccountForm = Record<'account_id' | 'client_id' | 'display_name' | 'api_key' | 'api_secret' | 'strategy_capital', string>;
export const EMPTY_FORM: AccountForm = { account_id: '', client_id: '', display_name: '', api_key: '', api_secret: '', strategy_capital: '' };

export type PositionRow = {
  symbol: string; quantity: number; average_price: number; last_price: number;
  pnl: number; unrealised: number; product: string; exchange: string;
};

export type TradeRow = {
  account_id: string; symbol: string; side: string; quantity: number;
  entry_time: string | null; exit_time: string | null; entry_price: number;
  exit_price: number; pnl: number; return_pct: number; result?: string; rr_note?: string | null;
};

export type DashboardAccount = {
  account_id: string; client_id: string; display_name: string | null;
  strategy_capital: number; broker_net: number; cash: number; opening_balance: number;
  utilised: number; realized_pnl: number; unrealized_pnl: number; net_pnl: number;
  return_pct: number; closed_trades: number; win_rate_pct: number; trade_return_pct: number;
  open_exposure: number; utilization_pct: number; open_winners: number; open_losers: number;
  concentration_pct: number; ce_count: number; pe_count: number;
  open_positions_count: number; open_positions: PositionRow[];
  latest_sync: { status: string; finished_at: string | null; orders_count: number; trades_count: number; error_msg: string | null };
};

export type Dashboard = {
  totals: { strategy_capital: number; broker_net: number; realized_pnl: number; unrealized_pnl: number; open_exposure: number; open_positions: number; trades_today: number; orders_today: number };
  accounts: DashboardAccount[];
  daily: { date: string; cashflow: number; executions: number }[];
  sync_note: string;
};

export type AccountState = {
  accounts: ZerodhaAccountStatus[];
  dashboard: Dashboard | null;
  trades: TradeRow[];
  latestDayTrades: TradeRow[];
  message: string | null;
  loading: boolean;
};
