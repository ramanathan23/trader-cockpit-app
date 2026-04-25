import type { Dashboard } from './accountTypes';
import { money } from './accountFmt';

type Point = { date: string; value: number; raw: number };

const W = 760;
const H = 150;
const PL = 34;
const PR = 62;
const PT = 12;
const PB = 28;
const IW = W - PL - PR;
const IH = H - PT - PB;

export function ActivityBars({ daily }: { daily: Dashboard['daily'] }) {
  const rows = daily.slice(-28);
  const totals = rows.reduce(
    (acc, row) => {
      acc.trades += row.trades ?? 0;
      acc.wins += row.wins ?? 0;
      acc.losses += row.losses ?? 0;
      acc.executions += row.executions;
      return acc;
    },
    { trades: 0, wins: 0, losses: 0, executions: 0 },
  );
  const winRate = totals.trades ? Math.round((totals.wins / totals.trades) * 100) : 0;
  const maxTrades = Math.max(1, ...rows.map(row => row.trades ?? 0));
  const tradeLine = rows.map(row => ({ date: row.date, raw: row.trades ?? 0, value: ((row.trades ?? 0) / maxTrades) * 100 }));
  const winLine = rows.map(row => ({ date: row.date, raw: row.wins ?? 0, value: row.win_pct ?? 0 }));
  const lossLine = rows.map(row => ({ date: row.date, raw: row.losses ?? 0, value: row.loss_pct ?? 0 }));
  const last = rows[rows.length - 1];

  return (
    <div className="rounded-lg border border-border bg-panel p-3">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <span className="block text-[12px] font-black text-fg">Trades vs Win/Loss Since Apr 2026</span>
          <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-[10px] text-ghost">
            <Legend color="bg-accent" label={`Trades, scaled to peak ${money(maxTrades)}`} />
            <Legend color="bg-bull" label="Win %" />
            <Legend color="bg-bear" label="Loss %" />
          </div>
        </div>
        <div className="grid grid-cols-3 gap-3 text-right">
          <Metric value={money(totals.trades)} label="trades" />
          <Metric value={`${winRate}%`} label="win rate" tone="text-bull" />
          <Metric value={money(totals.executions)} label="fills" />
        </div>
      </div>

      {rows.length ? (
        <div className="h-40">
          <svg viewBox={`0 0 ${W} ${H}`} className="h-full w-full" role="img" aria-label="Trades, win percentage, and loss percentage line chart">
            {[0, 50, 100].map(tick => {
              const y = yFor(tick);
              return (
                <g key={tick}>
                  <line x1={PL} x2={W - PR} y1={y} y2={y} stroke="rgb(var(--border))" strokeWidth="1" opacity={tick === 0 ? 0.9 : 0.55} />
                  <text x={PL - 8} y={y + 3} textAnchor="end" className="fill-ghost num text-[9px]">{tick}</text>
                </g>
              );
            })}

            <Line points={tradeLine} color="rgb(var(--accent))" />
            <Line points={winLine} color="rgb(var(--bull))" />
            <Line points={lossLine} color="rgb(var(--bear))" />

            {rows.map((row, idx) => {
              const show = idx === 0 || idx === rows.length - 1 || idx % 4 === 0;
              if (!show) return null;
              return (
                <text key={row.date} x={xFor(idx, rows.length)} y={H - 8} textAnchor="middle" className="fill-ghost num text-[9px]">
                  {row.date.slice(8, 10)}
                </text>
              );
            })}

            <EndpointLabel point={tradeLine[tradeLine.length - 1]} count={rows.length} text={`${last?.trades ?? 0} trades`} color="rgb(var(--accent))" lane={0} />
            <EndpointLabel point={winLine[winLine.length - 1]} count={rows.length} text={`${last?.win_pct ?? 0}% win`} color="rgb(var(--bull))" lane={1} />
            <EndpointLabel point={lossLine[lossLine.length - 1]} count={rows.length} text={`${last?.loss_pct ?? 0}% loss`} color="rgb(var(--bear))" lane={2} />

            {rows.map((row, idx) => (
              <circle key={row.date} cx={xFor(idx, rows.length)} cy={yFor(row.win_pct ?? 0)} r="7" fill="transparent">
                <title>{row.date}: {row.trades ?? 0} trades, {row.wins ?? 0} wins, {row.losses ?? 0} losses</title>
              </circle>
            ))}
          </svg>
        </div>
      ) : (
        <div className="flex h-40 items-center justify-center rounded border border-dashed border-border text-[11px] text-ghost">
          No closed trades synced yet.
        </div>
      )}

      <div className="mt-1 flex justify-end gap-3 text-[10px]">
        <span className="num text-bull">{totals.wins} wins</span>
        <span className="num text-bear">{totals.losses} losses</span>
      </div>
    </div>
  );
}

function Line({ points, color }: { points: Point[]; color: string }) {
  const d = points.map((point, idx) => `${idx === 0 ? 'M' : 'L'} ${xFor(idx, points.length)} ${yFor(point.value)}`).join(' ');
  return <path d={d} fill="none" stroke={color} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />;
}

function EndpointLabel({ point, count, text, color, lane }: { point?: Point; count: number; text: string; color: string; lane: number }) {
  if (!point) return null;
  const x = W - PR + 8;
  const y = Math.max(PT + 10 + lane * 16, Math.min(H - PB - 6, yFor(point.value)));
  return (
    <g>
      <line x1={xFor(count - 1, count)} x2={x - 3} y1={yFor(point.value)} y2={y} stroke={color} strokeWidth="1" opacity="0.5" />
      <text x={x} y={y + 3} className="num text-[9px] font-black" fill={color}>{text}</text>
    </g>
  );
}

function xFor(idx: number, count: number) {
  if (count <= 1) return PL + IW;
  return PL + (idx / (count - 1)) * IW;
}

function yFor(value: number) {
  return PT + (1 - Math.max(0, Math.min(100, value)) / 100) * IH;
}

function Legend({ color, label }: { color: string; label: string }) {
  return <span className="inline-flex items-center gap-1"><span className={`h-1.5 w-3 rounded-full ${color}`} />{label}</span>;
}

function Metric({ value, label, tone = 'text-fg' }: { value: string; label: string; tone?: string }) {
  return (
    <span>
      <span className={`num block text-[13px] font-black ${tone}`}>{value}</span>
      <span className="block text-[10px] text-ghost">{label}</span>
    </span>
  );
}
