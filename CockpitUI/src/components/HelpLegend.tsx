'use client';

import { memo } from 'react';
import { signalColor } from '@/domain/signal';

// ── Data ──────────────────────────────────────────────────────────────────────

const SIGNAL_ROWS = [
  { key: 'OPEN_DRIVE_ENTRY',    label: 'DRIVE',    desc: 'Open drive — price breaks pre-market range at open on momentum' },
  { key: 'VOLUME_SPIKE',        label: 'SPIKE',    desc: 'Volume spike — unusual institutional activity vs 20-day avg' },
  { key: 'ABS_STRENGTH',        label: 'ABS',      desc: 'Absorption — large sell orders absorbed at support; bullish reversal build-up' },
  { key: 'EXHAUSTION_REVERSAL', label: 'EXHAUST',  desc: 'Exhaustion — climactic price move on extreme volume; trend likely to reverse' },
  { key: 'FADE_SETUP',          label: 'FADE',     desc: 'Fade — overbought/oversold counter-trend entry as order flow thins out' },
  { key: 'ORB_BREAKOUT',        label: 'BREAKOUT', desc: 'Breakouts — ORB, Prev Day High/Low, 52-wk highs/lows, range breaks' },
  { key: 'VWAP_BREAKOUT',       label: 'VWAP',     desc: 'VWAP cross — price reclaiming or breaking Volume-Weighted Avg Price' },
  { key: 'CAMARILLA_R3_BREAK',  label: 'CAM',      desc: 'Camarilla pivot — H3/L3 reversals or H4/L4 momentum breakouts' },
] as const;

const METRIC_ROWS = [
  { key: '52H',  desc: '% price is below its 52-week high (0% = at record; negative = below high)' },
  { key: '52L',  desc: '% price is above its 52-week low (positive = healthier; further from lows)' },
  { key: 'ATR',  desc: 'Average True Range (14-day) — daily volatility in ₹; use for stop sizing' },
  { key: 'ADV',  desc: 'Avg Daily Value traded (20-day, ₹Cr) — liquidity. 5=small, 25=mid, 100=large' },
  { key: 'Δ%',   desc: "Price change vs yesterday's close (today's momentum)" },
  { key: 'Vol',  desc: 'Volume ratio vs 20-day avg (2× = twice normal; highlights institutional flow)' },
];

const LEVEL_ROWS = [
  { key: 'E',  color: '#e8933a', desc: 'Entry zone — place buy order in this price range' },
  { key: 'SL', color: '#f23d55', desc: 'Stop Loss — exit immediately if price falls through this level' },
  { key: 'T1', color: '#0dbd7d', desc: 'Target 1 — first partial profit-taking zone' },
];

const PHASE_ROWS = [
  { key: 'DRIVE WINDOW',   time: '9:15–9:45',  color: '#2d7ee8', desc: 'High-momentum open; best for trend-following entries' },
  { key: 'EXECUTION',      time: '9:45–11:30', color: '#0dbd7d', desc: 'Primary session — signals are most reliable here' },
  { key: 'DEAD ZONE',      time: '11:30–2:30', color: '#5a7796', desc: 'Low conviction chop — reduce size, be very selective' },
  { key: 'CLOSE MOMENTUM', time: '2:30–3:15',  color: '#e8933a', desc: 'Late institutional flows; directional move resumes' },
  { key: 'SESSION END',    time: '3:15–3:30',  color: '#f23d55', desc: 'Last-minute flows; avoid initiating new positions' },
];

// ── Section wrapper ───────────────────────────────────────────────────────────

const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <div className="flex flex-col gap-2 min-w-0 shrink-0">
    <span
      className="text-[9px] font-black tracking-[0.18em] uppercase text-ghost"
    >
      {title}
    </span>
    <div className="flex flex-col gap-1.5">{children}</div>
  </div>
);

const Divider = () => (
  <div className="w-px self-stretch bg-border shrink-0" />
);

// ── Component ─────────────────────────────────────────────────────────────────

export const HelpLegend = memo(() => (
  <div
    className="shrink-0 px-4 py-3 bg-panel border-b border-border"
  >
    <div className="help-legend">
    {/* ── Signal types ─────────────────────────────── */}
    <Section title="Signal categories">
      <div className="help-section-grid">
        {SIGNAL_ROWS.map(r => {
          const c = signalColor(r.key as Parameters<typeof signalColor>[0]);
          return (
            <div key={r.key} className="flex items-baseline gap-2 min-w-0">
              <span
                className="text-[9px] font-black shrink-0 w-14"
                style={{ color: c }}
              >
                {r.label}
              </span>
              <span className="text-[11px] leading-snug text-dim">
                {r.desc}
              </span>
            </div>
          );
        })}
      </div>
    </Section>

    <Divider />

    {/* ── Card metrics ──────────────────────────────── */}
    <Section title="Card metrics">
      <div className="flex flex-col gap-1.5">
        {METRIC_ROWS.map(r => (
          <div key={r.key} className="flex items-baseline gap-2">
            <span
              className="num text-[9px] font-black w-7 shrink-0"
              style={{ color: 'rgb(var(--fg))' }}
            >
              {r.key}
            </span>
            <span className="text-[11px] leading-snug text-dim">
              {r.desc}
            </span>
          </div>
        ))}
      </div>
    </Section>

    <Divider />

    {/* ── Trade levels ──────────────────────────────── */}
    <Section title="Trade levels">
      <div className="flex flex-col gap-1.5">
        {LEVEL_ROWS.map(r => (
          <div key={r.key} className="flex items-baseline gap-2">
            <span
              className="num text-[9px] font-black w-5 shrink-0"
              style={{ color: r.color }}
            >
              {r.key}
            </span>
            <span className="text-[11px] leading-snug text-dim">
              {r.desc}
            </span>
          </div>
        ))}
        <div className="flex items-baseline gap-2 pt-1 border-t border-border">
          <span className="num text-[9px] font-black w-5 shrink-0" style={{ color: '#0dbd7d' }}>▲</span>
          <span className="text-[11px] leading-snug text-dim">Bullish: price above key moving averages</span>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="num text-[9px] font-black w-5 shrink-0" style={{ color: '#f23d55' }}>▼</span>
          <span className="text-[11px] leading-snug text-dim">Bearish: price below key moving averages</span>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-[9px] font-semibold w-5 shrink-0 text-ghost">▲▲</span>
          <span className="text-[11px] leading-snug text-dim">15m and 1h aligned — higher conviction signal</span>
        </div>
      </div>
    </Section>

    <Divider />

    {/* ── Market phases ─────────────────────────────── */}
    <Section title="Market phases">
      <div className="flex flex-col gap-1.5">
        {PHASE_ROWS.map(r => (
          <div key={r.key} className="flex items-baseline gap-2">
            <span
              className="text-[9px] font-black shrink-0 w-28"
              style={{ color: r.color }}
            >
              {r.key}
            </span>
            <span className="num text-[9px] shrink-0 w-16 text-ghost">
              {r.time}
            </span>
            <span className="text-[11px] leading-snug text-dim">
              {r.desc}
            </span>
          </div>
        ))}
      </div>
    </Section>

    <Divider />

    {/* ── Liquidity tiers ───────────────────────────── */}
    <Section title="Value filter (ADV)">
      <div className="flex flex-col gap-1.5">
        {[
          { label: 'All',    cr: 'No filter',    desc: 'Show all stocks regardless of liquidity' },
          { label: '5Cr+',   cr: '₹5 Cr+',       desc: 'Filters very illiquid, hard-to-trade stocks' },
          { label: '25Cr+',  cr: '₹25 Cr+',      desc: 'Mid-cap liquidity — decent spreads' },
          { label: '100Cr+', cr: '₹100 Cr+',     desc: 'Large cap — safer fills, smaller impact' },
          { label: '500Cr+', cr: '₹500 Cr+',     desc: 'Index-grade mega-caps only' },
        ].map(r => (
          <div key={r.label} className="flex items-baseline gap-2">
            <span className="num text-[9px] font-black w-12 shrink-0" style={{ color: '#e8933a' }}>
              {r.label}
            </span>
            <span className="num text-[9px] w-14 shrink-0 text-ghost">
              {r.cr}
            </span>
            <span className="text-[11px] leading-snug text-dim">
              {r.desc}
            </span>
          </div>
        ))}
      </div>
    </Section>
    </div>
  </div>
));

HelpLegend.displayName = 'HelpLegend';
