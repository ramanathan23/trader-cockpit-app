/** All shared types for the Admin panel — single source of truth. */

export type StepStatus = 'idle' | 'running' | 'ok' | 'error';

export type AdminSection =
  | 'full-sync'
  | 'zerodha'
  | 'token'
  | 'config-scorer'
  | 'config-datasync'
  | 'config-livefeed'
  | 'config-modeling';

export interface NavItem {
  key: AdminSection;
  label: string;
  caption: string;
  group?: string;
}

export type FieldType = 'int' | 'float' | 'bool' | 'string';

export interface FieldDef {
  key: string;
  label: string;
  type: FieldType;
  group?: string;
  min?: number;
  max?: number;
  step?: number;
}

export interface ServiceConfigDef {
  id: string;
  name: string;
  endpoint: string;
  fields: FieldDef[];
}

export interface ZerodhaAccountStatus {
  account_id: string;
  client_id: string;
  display_name?: string | null;
  broker: string;
  login_url: string;
  status: 'connected' | 'expired' | 'not_connected' | 'login_required' | 'error';
  strategy_capital?: number | null;
  has_credentials?: boolean;
  login_time?: string | null;
  expires_at?: string | null;
  last_error?: string | null;
}

/** Per-step state tracked during pipeline execution. */
export type PipelineState = Record<string, {
  status: StepStatus;
  message: string | null;
  startedAt: number | null;
  elapsedMs: number | null;
}>;

/** Pre-fetched service configs passed from server to avoid a round-trip on load. */
export type InitialConfigs = {
  scorer:   Record<string, unknown> | null;
  datasync: Record<string, unknown> | null;
  livefeed: Record<string, unknown> | null;
  modeling: Record<string, unknown> | null;
};
