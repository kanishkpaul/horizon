import * as d3 from "d3";
import { useEffect, useRef, useState, type ReactNode } from "react";

// ------------------------------------------------------------------ sizing + tooltip
export function useWidth<T extends HTMLElement>(fallback = 600) {
  const ref = useRef<T>(null);
  const [w, setW] = useState(fallback);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setW(el.clientWidth || fallback));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  return [ref, w] as const;
}

export function useTip() {
  const [tip, setTip] = useState<{ x: number; y: number; body: ReactNode } | null>(null);
  const node = tip ? (
    <div className="tooltip" style={{ left: Math.min(tip.x + 14, window.innerWidth - 330), top: tip.y + 14 }}>{tip.body}</div>
  ) : null;
  return { show: (e: React.MouseEvent, body: ReactNode) => setTip({ x: e.clientX, y: e.clientY, body }), hide: () => setTip(null), node };
}

// ------------------------------------------------------------------ distribution preview
function lgamma(x: number): number {
  const c = [76.18009172947146, -86.50532032941677, 24.01409824083091, -1.231739572450155, 0.1208650973866179e-2, -0.5395239384953e-5];
  let y = x, tmp = x + 5.5;
  tmp -= (x + 0.5) * Math.log(tmp);
  let ser = 1.000000000190015;
  for (const k of c) ser += k / ++y;
  return -tmp + Math.log((2.5066282746310005 * ser) / x);
}
export function density(dist: string): { xs: number[]; ys: number[]; discrete?: boolean } | null {
  const m = dist.match(/^\s*(\w+)\s*\(([^)]*)\)/);
  if (!m) return null;
  const k = m[1];
  const a = m[2].split(",").map(Number);
  const grid = (lo: number, hi: number) => d3.range(0, 121).map((i) => lo + ((hi - lo) * i) / 120);
  if (k === "beta") {
    const xs = grid(0.001, 0.999);
    const lb = lgamma(a[0]) + lgamma(a[1]) - lgamma(a[0] + a[1]);
    return { xs, ys: xs.map((x) => Math.exp((a[0] - 1) * Math.log(x) + (a[1] - 1) * Math.log(1 - x) - lb)) };
  }
  if (k === "normal") {
    const xs = grid(a[0] - 3.5 * a[1], a[0] + 3.5 * a[1]);
    return { xs, ys: xs.map((x) => Math.exp(-0.5 * ((x - a[0]) / a[1]) ** 2)) };
  }
  if (k === "lognormal") {
    const s = Math.log(a[1]);
    const xs = grid(a[0] * Math.exp(-3 * s), a[0] * Math.exp(3 * s));
    return { xs, ys: xs.map((x) => Math.exp(-0.5 * ((Math.log(x) - Math.log(a[0])) / s) ** 2) / x) };
  }
  if (k === "triangular") {
    const [lo, mo, hi] = a;
    const xs = grid(lo, hi);
    return { xs, ys: xs.map((x) => (x < mo ? (x - lo) / (mo - lo || 1) : (hi - x) / (hi - mo || 1))) };
  }
  if (k === "bernoulli") return { xs: [0, 1], ys: [1 - a[0], a[0]], discrete: true };
  if (k === "fixed") return { xs: [a[0]], ys: [1], discrete: true };
  return null;
}

export function DistPreview({ dist, height = 90 }: { dist: string; height?: number }) {
  const [ref, w] = useWidth<HTMLDivElement>(400);
  const d = density(dist);
  if (!d) return null;
  const m = { l: 8, r: 8, t: 6, b: 18 };
  const x = d3.scaleLinear().domain(d3.extent(d.xs) as [number, number]).range([m.l, w - m.r]);
  const y = d3.scaleLinear().domain([0, d3.max(d.ys) || 1]).range([height - m.b, m.t]);
  return (
    <div ref={ref} className="chart">
      <svg width={w} height={height} role="img" aria-label={`Distribution ${dist}`}>
        {d.discrete ? d.xs.map((xv, i) => (
          <rect key={i} x={d.xs.length === 1 ? w / 2 - 10 : m.l + i * ((w - m.l - m.r) / 2) + 20} width={40}
            y={y(d.ys[i])} height={height - m.b - y(d.ys[i])} rx={3} fill="var(--s1)" />
        )) : (
          <path d={d3.area<number>().x((_, i) => x(d.xs[i])).y0(height - m.b).y1((v) => y(v)).curve(d3.curveBasis)(d.ys) || ""}
            fill="var(--s1)" fillOpacity={0.18} stroke="var(--s1)" strokeWidth={2} />
        )}
        <g className="axis" transform={`translate(0,${height - m.b})`}>
          <line x1={m.l} x2={w - m.r} />
          {(d.discrete ? d.xs : x.ticks(5)).map((t) => <text key={t} x={d.discrete && d.xs.length === 2 ? m.l + d.xs.indexOf(t) * ((w - m.l - m.r) / 2) + 40 : x(t)} y={13} textAnchor="middle">{d3.format("~g")(t)}</text>)}
        </g>
      </svg>
    </div>
  );
}

// ------------------------------------------------------------------ histogram (one series)
export function Histogram({ hist, color = "var(--s1)", height = 120, fmt = (v: number) => d3.format("~g")(v), label }: {
  hist: any; color?: string; height?: number; fmt?: (v: number) => string; label?: string;
}) {
  const [ref, w] = useWidth<HTMLDivElement>(300);
  const tip = useTip();
  if (!hist) return null;
  const m = { l: 6, r: 6, t: 8, b: 18 };
  const n = hist.counts.reduce((a: number, b: number) => a + b, 0) || 1;
  const bins: { lo: number; hi: number; c: number; label: string }[] = hist.values
    ? hist.values.map((v: number, i: number) => ({ lo: v, hi: v, c: hist.counts[i], label: fmt(v) }))
    : hist.counts.map((c: number, i: number) => ({ lo: hist.edges[i], hi: hist.edges[i + 1], c, label: `${fmt(hist.edges[i])}–${fmt(hist.edges[i + 1])}` }));
  const bw = (w - m.l - m.r) / bins.length;
  const y = d3.scaleLinear().domain([0, d3.max(bins, (b) => b.c) || 1]).range([height - m.b, m.t]);
  return (
    <div ref={ref} className="chart">
      <svg width={w} height={height} role="img" aria-label={label || "Distribution across simulated worlds"}>
        {bins.map((b, i) => (
          <g key={i} onMouseMove={(e) => tip.show(e, <><b>{b.label}</b><div className="num">{(100 * b.c / n).toFixed(1)}% of worlds</div></>)} onMouseLeave={tip.hide}>
            <rect x={m.l + i * bw} y={m.t} width={bw} height={height - m.b - m.t} fill="transparent" />
            <rect x={m.l + i * bw + 1} y={y(b.c)} width={Math.max(1, bw - 2)} height={Math.max(0, height - m.b - y(b.c))} rx={Math.min(3, bw / 3)} fill={color} />
          </g>
        ))}
        <line x1={m.l} x2={w - m.r} y1={height - m.b} y2={height - m.b} stroke="var(--rule)" />
        {hist.values
          ? bins.filter((_, i) => bins.length <= 12 || i % Math.ceil(bins.length / 8) === 0).map((b) => {
              const i = bins.indexOf(b);
              return <text key={i} x={m.l + i * bw + bw / 2} y={height - 4} textAnchor="middle">{b.label}</text>;
            })
          : [0, bins.length - 1].map((i) => <text key={i} x={i === 0 ? m.l : w - m.r} y={height - 4} textAnchor={i === 0 ? "start" : "end"}>{fmt(i === 0 ? bins[0].lo : bins[i].hi)}</text>)}
      </svg>
      {tip.node}
    </div>
  );
}

// ------------------------------------------------------------------ lines over weeks (with crosshair)
export function WeekLines({ series, height = 220, yFmt = d3.format(".0%"), yMax, start, gradWeek, label, xTick }: {
  series: { id: string; name: string; color: string; values: number[]; dashed?: boolean }[];
  height?: number; yFmt?: (v: number) => string; yMax?: number; start: Date; gradWeek?: number; label: string;
  xTick?: (i: number) => string;
}) {
  const [ref, w] = useWidth<HTMLDivElement>(600);
  const [hx, setHx] = useState<number | null>(null);
  const T = Math.max(...series.map((s) => s.values.length), 1);
  const m = { l: 40, r: 120, t: 10, b: 22 };
  const x = d3.scaleLinear().domain([0, T - 1]).range([m.l, w - m.r]);
  const y = d3.scaleLinear().domain([0, yMax ?? Math.max(1e-6, d3.max(series.flatMap((s) => s.values)) || 1)]).nice().range([height - m.b, m.t]);
  const line = d3.line<number>().x((_, i) => x(i)).y((v) => y(v)).curve(d3.curveMonotoneX);
  const dateOf = xTick ?? ((wk: number) => d3.timeFormat("%d %b")(d3.timeDay.offset(start, Math.round(wk * 7))));
  // direct labels at the line ends, de-collided
  const ends = series.map((s) => ({ s, y: y(s.values[s.values.length - 1] ?? 0) })).sort((a, b) => a.y - b.y);
  for (let i = 1; i < ends.length; i++) if (ends[i].y - ends[i - 1].y < 12) ends[i].y = ends[i - 1].y + 12;
  return (
    <div ref={ref} className="chart" style={{ position: "relative" }}>
      <svg width={w} height={height} role="img" aria-label={label}
        onMouseMove={(e) => {
          const r = (e.currentTarget as SVGSVGElement).getBoundingClientRect();
          const wk = Math.round(x.invert(e.clientX - r.left));
          setHx(wk >= 0 && wk < T ? wk : null);
        }} onMouseLeave={() => setHx(null)}>
        <g className="grid">{y.ticks(4).map((t) => <line key={t} x1={m.l} x2={w - m.r} y1={y(t)} y2={y(t)} />)}</g>
        {y.ticks(4).map((t) => <text key={t} x={m.l - 6} y={y(t) + 3} textAnchor="end">{yFmt(t)}</text>)}
        {d3.range(0, T, Math.max(1, Math.round(T / 12))).map((t) => <text key={t} x={x(t)} y={height - 6} textAnchor="middle">{dateOf(t)}</text>)}
        {gradWeek != null && gradWeek < T && (
          <g><line x1={x(gradWeek)} x2={x(gradWeek)} y1={m.t} y2={height - m.b} stroke="var(--ink-3)" strokeDasharray="3 3" />
            <text x={x(gradWeek) + 4} y={m.t + 9} className="lbl" style={{ fontSize: 10.5 }}>graduation</text></g>
        )}
        {series.map((s) => (
          <path key={s.id} d={line(s.values) || ""} fill="none" stroke={s.color} strokeWidth={2} strokeDasharray={s.dashed ? "5 3" : undefined} />
        ))}
        {ends.map(({ s, y: yy }) => (
          <text key={s.id} x={w - m.r + 6} y={yy + 3} className="lbl" style={{ fontSize: 11 }}>{s.name.slice(0, 18)}</text>
        ))}
        {hx != null && (
          <g>
            <line x1={x(hx)} x2={x(hx)} y1={m.t} y2={height - m.b} stroke="var(--ink-3)" />
            {series.map((s) => <circle key={s.id} cx={x(hx)} cy={y(s.values[hx] ?? 0)} r={4} fill={s.color} stroke="var(--panel-2)" strokeWidth={2} />)}
          </g>
        )}
      </svg>
      {hx != null && (
        <div className="tooltip" style={{ position: "absolute", left: Math.min(x(hx) + 12, w - 220), top: 8 }}>
          <div style={{ fontWeight: 600, marginBottom: 2 }}>{xTick ? dateOf(hx) : `Week ${hx} · ${dateOf(hx)}`}</div>
          {[...series].sort((a, b) => (b.values[hx] ?? 0) - (a.values[hx] ?? 0)).map((s) => (
            <div key={s.id} className="row" style={{ gap: 6 }}><i style={{ width: 8, height: 8, background: s.color, borderRadius: 2, display: "inline-block" }} />{s.name}<span className="num" style={{ marginLeft: "auto" }}>{yFmt(s.values[hx] ?? 0)}</span></div>
          ))}
        </div>
      )}
    </div>
  );
}

// ------------------------------------------------------------------ dot + range per category
export function DotRange({ rows, fmt = d3.format(".2f"), label, height }: {
  rows: { id: string; name: string; color: string; mean: number; lo: number; hi: number; note?: string; dim?: boolean }[];
  fmt?: (v: number) => string; label: string; height?: number;
}) {
  const [ref, w] = useWidth<HTMLDivElement>(500);
  const tip = useTip();
  const rh = 26;
  const H = height ?? rows.length * rh + 26;
  const m = { l: 168, r: 56, t: 6, b: 20 };
  const lo = d3.min(rows, (r) => r.lo) ?? 0, hi = d3.max(rows, (r) => r.hi) ?? 1;
  const x = d3.scaleLinear().domain([Math.min(0, lo), hi === lo ? hi + 1 : hi]).nice().range([m.l, w - m.r]);
  return (
    <div ref={ref} className="chart">
      <svg width={w} height={H} role="img" aria-label={label}>
        <g className="grid">{x.ticks(5).map((t) => <line key={t} x1={x(t)} x2={x(t)} y1={m.t} y2={H - m.b} />)}</g>
        {x.ticks(5).map((t) => <text key={t} x={x(t)} y={H - 6} textAnchor="middle">{fmt(t)}</text>)}
        {rows.map((r, i) => {
          const cy = m.t + i * rh + rh / 2;
          return (
            <g key={r.id} opacity={r.dim ? 0.45 : 1}
              onMouseMove={(e) => tip.show(e, <><b>{r.name}</b><div className="num">mean {fmt(r.mean)} · 10–90%: {fmt(r.lo)} to {fmt(r.hi)}</div>{r.note && <div>{r.note}</div>}</>)}
              onMouseLeave={tip.hide}>
              <rect x={0} y={cy - rh / 2} width={w} height={rh} fill="transparent" />
              <text x={m.l - 10} y={cy + 4} textAnchor="end" className="lbl">{r.name.slice(0, 24)}</text>
              <line x1={x(r.lo)} x2={x(r.hi)} y1={cy} y2={cy} stroke={r.color} strokeWidth={2} strokeLinecap="round" />
              <circle cx={x(r.mean)} cy={cy} r={5} fill={r.color} stroke="var(--panel-2)" strokeWidth={2} />
              <text x={w - m.r + 8} y={cy + 4} className="num" style={{ fill: "var(--ink-2)" }}>{fmt(r.mean)}</text>
            </g>
          );
        })}
      </svg>
      {tip.node}
    </div>
  );
}

// ------------------------------------------------------------------ tornado
export function Tornado({ rows, base, label }: { rows: { name: string; low: number; high: number; lowV: string; highV: string; flips: boolean; origin?: string }[]; base: number; label: string }) {
  const [ref, w] = useWidth<HTMLDivElement>(600);
  const tip = useTip();
  const rh = 24;
  const H = rows.length * rh + 28;
  const m = { l: 200, r: 30, t: 6, b: 22 };
  const ext = d3.extent([base, ...rows.flatMap((r) => [r.low, r.high])]) as [number, number];
  const x = d3.scaleLinear().domain(ext).nice().range([m.l, w - m.r]);
  return (
    <div ref={ref} className="chart">
      <svg width={w} height={H} role="img" aria-label={label}>
        <g className="grid">{x.ticks(5).map((t) => <line key={t} x1={x(t)} x2={x(t)} y1={m.t} y2={H - m.b} />)}</g>
        {x.ticks(5).map((t) => <text key={t} x={x(t)} y={H - 6} textAnchor="middle">{d3.format(".2f")(t)}</text>)}
        <line x1={x(base)} x2={x(base)} y1={m.t} y2={H - m.b} stroke="var(--ink)" />
        {rows.map((r, i) => {
          const cy = m.t + i * rh + rh / 2;
          const seg = (v: number, col: string) => (
            <rect x={Math.min(x(base), x(v))} y={cy - 7} width={Math.max(1, Math.abs(x(v) - x(base)))} height={14} rx={3} fill={col} />
          );
          return (
            <g key={r.name} onMouseMove={(e) => tip.show(e, <><b>{r.name}</b><div>At 10th pct ({r.lowV}): <span className="num">{r.low.toFixed(3)}</span></div><div>At 90th pct ({r.highV}): <span className="num">{r.high.toFixed(3)}</span></div>{r.flips && <div>⚠ changes which strategy ranks first</div>}</>)} onMouseLeave={tip.hide}>
              <rect x={0} y={cy - rh / 2} width={w} height={rh} fill="transparent" />
              <text x={m.l - 10} y={cy + 4} textAnchor="end" className="lbl">{r.flips ? "⚠ " : ""}{r.name.slice(0, 28)}</text>
              {seg(r.low, "var(--s2)")}
              {seg(r.high, "var(--s1)")}
            </g>
          );
        })}
      </svg>
      <div className="legend" style={{ marginTop: 4 }}><span><i style={{ background: "var(--s2)" }} />parameter at its 10th percentile</span><span><i style={{ background: "var(--s1)" }} />at its 90th percentile</span><span>⚠ the top strategy changes</span></div>
      {tip.node}
    </div>
  );
}

// ------------------------------------------------------------------ scatter (two metrics) with Pareto front
export function Scatter({ points, xLabel, yLabel, xFmt = d3.format(".2f"), yFmt = d3.format(".0%"), front = [] }: {
  points: { id: string; name: string; color: string; x: number; y: number; dashed?: boolean }[];
  xLabel: string; yLabel: string; xFmt?: (v: number) => string; yFmt?: (v: number) => string; front?: string[];
}) {
  const [ref, w] = useWidth<HTMLDivElement>(500);
  const tip = useTip();
  const H = 300;
  const m = { l: 48, r: 20, t: 14, b: 36 };
  const x = d3.scaleLinear().domain(d3.extent(points, (p) => p.x) as [number, number]).nice().range([m.l, w - m.r]);
  const y = d3.scaleLinear().domain(d3.extent(points, (p) => p.y) as [number, number]).nice().range([H - m.b, m.t]);
  const fp = points.filter((p) => front.includes(p.id)).sort((a, b) => a.x - b.x);
  return (
    <div ref={ref} className="chart">
      <svg width={w} height={H} role="img" aria-label={`${yLabel} against ${xLabel}`}>
        <g className="grid">{y.ticks(5).map((t) => <line key={t} x1={m.l} x2={w - m.r} y1={y(t)} y2={y(t)} />)}</g>
        {y.ticks(5).map((t) => <text key={t} x={m.l - 6} y={y(t) + 3} textAnchor="end">{yFmt(t)}</text>)}
        {x.ticks(5).map((t) => <text key={t} x={x(t)} y={H - m.b + 14} textAnchor="middle">{xFmt(t)}</text>)}
        <text x={(m.l + w - m.r) / 2} y={H - 4} textAnchor="middle" className="lbl">{xLabel}</text>
        <text transform={`translate(12,${(m.t + H - m.b) / 2}) rotate(-90)`} textAnchor="middle" className="lbl">{yLabel}</text>
        {fp.length > 1 && <path d={d3.line<any>().x((p) => x(p.x)).y((p) => y(p.y))(fp) || ""} fill="none" stroke="var(--ink-3)" strokeDasharray="4 3" />}
        {points.map((p) => (
          <g key={p.id} onMouseMove={(e) => tip.show(e, <><b>{p.name}</b><div className="num">{xLabel}: {xFmt(p.x)}</div><div className="num">{yLabel}: {yFmt(p.y)}</div>{front.includes(p.id) && <div>On the Pareto front</div>}</>)} onMouseLeave={tip.hide}>
            <circle cx={x(p.x)} cy={y(p.y)} r={12} fill="transparent" />
            <circle cx={x(p.x)} cy={y(p.y)} r={front.includes(p.id) ? 6 : 4.5} fill={p.color} stroke="var(--panel-2)" strokeWidth={2} strokeDasharray={p.dashed ? "2 2" : undefined} />
            <text x={x(p.x) + 8} y={y(p.y) - 6} className="lbl" style={{ fontSize: 10.5 }}>{p.name.slice(0, 20)}</text>
          </g>
        ))}
      </svg>
      {tip.node}
    </div>
  );
}

// ------------------------------------------------------------------ dominance matrix (sequential)
export function DominanceTable({ ids, M, names }: { ids: string[]; M: (number | null)[][]; names: Record<string, string> }) {
  const color = d3.scaleSequential((t) => d3.interpolateRgb("transparent", "rgba(42,120,214,0.85)")(t)).domain([0.5, 1]);
  return (
    <div className="scroll">
      <table className="t" style={{ fontSize: 11.5 }}>
        <thead><tr><th>Row beats column in…</th>{ids.map((c) => <th key={c} className="r" title={names[c]}>{(names[c] || c).slice(0, 10)}</th>)}</tr></thead>
        <tbody>
          {ids.map((r, i) => (
            <tr key={r}><td>{names[r] || r}</td>
              {ids.map((c, j) => {
                const v = M[i][j];
                return <td key={c} className="r num" style={{ background: v == null ? "var(--wash)" : v > 0.5 ? color(v) : undefined, color: v != null && v > 0.8 ? "#fff" : undefined }}>
                  {v == null ? "" : `${Math.round(v * 100)}%`}</td>;
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="faint" style={{ fontSize: 11.5, marginTop: 6 }}>Share of simulated worlds in which the row strategy yields higher value than the column strategy (paired on identical worlds).</p>
    </div>
  );
}
