'use client';

import type { FieldDef } from './adminTypes';

interface ConfigFieldProps {
  def: FieldDef;
  value: unknown;
  onChange: (key: string, val: unknown) => void;
}

/** Renders a single config field — toggle for bool, number input for int/float, text for string. */
export function ConfigField({ def, value, onChange }: ConfigFieldProps) {
  if (def.type === 'bool') {
    return (
      <div className="col-span-2 flex items-center justify-between rounded-lg border border-border bg-base/40 px-3 py-2.5">
        <span className="text-[11px] text-ghost">{def.label}</span>
        <button
          type="button"
          role="switch"
          aria-checked={!!value}
          onClick={() => onChange(def.key, !value)}
          className={`relative h-4 w-7 shrink-0 rounded-full transition-colors ${value ? 'bg-accent' : 'bg-border'}`}
        >
          <span className={`absolute left-0 top-0.5 h-3 w-3 rounded-full bg-white shadow transition-transform ${value ? 'translate-x-3.5' : 'translate-x-0.5'}`} />
        </button>
      </div>
    );
  }

  if (def.type === 'string') {
    return (
      <div className="flex flex-col gap-1.5">
        <span className="text-[10px] text-ghost">{def.label}</span>
        <input
          type="text"
          className="field h-8 w-full text-[12px]"
          value={String(value ?? '')}
          onChange={e => onChange(def.key, e.target.value)}
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-[10px] text-ghost">{def.label}</span>
      <input
        type="number"
        className="field h-8 w-full num text-[12px]"
        value={value as number}
        min={def.min}
        max={def.max}
        step={def.step ?? (def.type === 'int' ? 1 : 0.01)}
        onChange={e => {
          const raw = def.type === 'int' ? parseInt(e.target.value, 10) : parseFloat(e.target.value);
          onChange(def.key, isNaN(raw) ? value : raw);
        }}
      />
    </div>
  );
}
