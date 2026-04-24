/** All shared types for the Admin panel — single source of truth. */

export type StepStatus = 'idle' | 'running' | 'ok' | 'error';

export type AdminSection =
  | 'full-sync'
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
