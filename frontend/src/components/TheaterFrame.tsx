import * as d3 from "d3";

/** Pure renderer: (spec, t in weeks) -> SVG frame at 1280×720 logical px.
 *  Used by the interactive theater and, frame by frame, by the video renderer. */
export const FW = 1280, FH = 720;

type Ev = { world: number; week: number; type: string; action: string | null; label: string; stage?: string };

export function laneStates(spec: any, t: number) {
  const out: Record<string, { start?: number; end?: number; missed?: number; results: Ev[] }> = {};
  for (const l of spec.lanes) out[l.id] = { results: [] };
  for (const e of spec.events as Ev[]) {
    if (!e.action || !out[e.action]) continue;
    const s = out[e.action];
    if (e.type === "start") s.start = e.week;
    if (e.type === "complete") s.end = e.week;
    if (e.type === "missed") s.missed = e.week;
    if ((e.type === "outcome" || e.type === "offer") && e.week <= t) s.results.push(e);
  }
  return out;
}

export function sceneAt(spec: any, t: number) {
  let cur = spec.scenes[0];
  for (const s of spec.scenes) if (s.t <= t + 1e-9) cur = s;
  return cur;
}

const GOOD = /accepted|offer|merged|selected|endorsed|award|grant|passes|joint|useful|placement|traction|reply|uptake|used or cited/i;

export function TheaterFrame({ spec, t, onLane, compact = false }: { spec: any; t: number; onLane?: (id: string) => void; compact?: boolean }) {
  const T = spec.horizon_weeks;
  const L = { l: 300, r: 330, t: 92, b: 132 };
  const x = d3.scaleLinear().domain([0, T]).range([L.l, FW - L.r]);
  const lanes = spec.lanes as any[];
  const laneH = Math.min(26, (FH - L.t - L.b) / Math.max(lanes.length, 1));
  const st = laneStates(spec, t);
  const start = new Date(spec.start_date + "T00:00:00+05:30");
  const months = d3.timeMonth.range(d3.timeMonth.ceil(start), d3.timeWeek.offset(start, T));
  const wk = (d: Date) => (d.getTime() - start.getTime()) / (7 * 864e5);
  const scene = sceneAt(spec, t);
  const evNow = (spec.events as Ev[]).filter((e) => e.week <= t);
  const offers = evNow.filter((e) => e.type === "offer");
  const rules = (spec.events as Ev[]).filter((e) => e.type === "rule" || e.type === "exogenous");
  const posSeries: number[] = spec.series.position;
  const tIdx = Math.min(posSeries.length - 1, Math.max(0, Math.floor(t)));
  const fanX = d3.scaleLinear().domain([0, T]).range([FW - L.r + 34, FW - 30]);
  const fanY = d3.scaleLinear().domain([0, 1]).range([FH - L.b - 10, FH - L.b - 150]);
  const counts = {
    papers: evNow.filter((e) => e.type === "outcome" && /Accepted/.test(e.label)).length,
    outputs: evNow.filter((e) => e.type === "complete" && /preprint|arXiv|Release|benchmark|work sample|pilot/i.test(lanes.find((l) => l.id === e.action)?.name || "")).length,
  };
  const dateAt = d3.timeFormat("%d %b %Y")(d3.timeDay.offset(start, Math.round(t * 7)));
  return (
    <svg viewBox={`0 0 ${FW} ${FH}`} width="100%" style={{ display: "block", background: "var(--panel-2)", fontFamily: "var(--sans)" }} role="img"
      aria-label={`Simulated trajectory for ${spec.strategy_name}, world ${spec.world}, at week ${t.toFixed(1)}`}>
      {/* header */}
      <text x={40} y={44} style={{ font: "500 27px var(--serif)", fill: "var(--ink)" }}>{spec.strategy_name}</text>
      <text x={40} y={70} style={{ font: "13px var(--sans)", fill: "var(--ink-2)" }}>
        One simulated world (#{spec.world} of {spec.n_worlds.toLocaleString()}) · value model: {spec.objective} · scenario: {spec.scenario.name}
      </text>
      <text x={FW - 40} y={44} textAnchor="end" style={{ font: "600 22px var(--mono)", fill: "var(--ink)" }}>{dateAt}</text>
      <text x={FW - 40} y={70} textAnchor="end" style={{ font: "12px var(--mono)", fill: "var(--ink-3)" }}>week {t.toFixed(1)} of {T}</text>

      {/* time axis */}
      {months.map((m) => (
        <g key={+m}>
          <line x1={x(wk(m))} x2={x(wk(m))} y1={L.t - 6} y2={L.t + lanes.length * laneH} stroke="var(--rule-2)" />
          <text x={x(wk(m)) + 3} y={L.t - 10} style={{ font: "600 10.5px var(--sans)", fill: "var(--ink-3)", letterSpacing: "0.04em" }}>{d3.timeFormat("%b")(m).toUpperCase()}</text>
        </g>
      ))}
      <line x1={x(spec.graduation_week)} x2={x(spec.graduation_week)} y1={L.t - 6} y2={L.t + lanes.length * laneH} stroke="var(--ink-3)" strokeDasharray="4 4" />
      <text x={x(spec.graduation_week) + 4} y={L.t + lanes.length * laneH + 14} style={{ font: "11px var(--sans)", fill: "var(--ink-3)" }}>graduation</text>

      {/* rules and outside events (all, faint until reached) */}
      {rules.map((e, i) => (
        <g key={i} opacity={e.week <= t ? 1 : 0.18}>
          <line x1={x(e.week)} x2={x(e.week)} y1={L.t - 6} y2={L.t + lanes.length * laneH} stroke={e.type === "rule" ? "var(--s7)" : "var(--s2)"} strokeWidth={1.5} strokeDasharray={e.type === "rule" ? undefined : "3 3"} />
        </g>
      ))}

      {/* lanes */}
      {lanes.map((l, i) => {
        const y = L.t + i * laneH;
        const s = st[l.id];
        const active = s.start != null && s.start <= t;
        const endW = s.end != null ? Math.min(s.end, t) : s.missed != null ? Math.min(s.missed, t) : t;
        const done = s.end != null && s.end <= t;
        const missed = s.missed != null && s.missed <= t;
        return (
          <g key={l.id} style={{ cursor: onLane ? "pointer" : undefined }} onClick={() => onLane?.(l.id)}>
            <rect x={0} y={y} width={FW} height={laneH} fill={i % 2 ? "var(--wash)" : "transparent"} opacity={0.6} />
            <text x={L.l - 12} y={y + laneH / 2 + 4} textAnchor="end" style={{ font: `${active ? 600 : 400} 12px var(--sans)`, fill: active ? "var(--ink)" : "var(--ink-3)" }}>
              {l.name.length > 44 ? l.name.slice(0, 42) + "…" : l.name}
            </text>
            {l.deadline_week != null && l.deadline_week <= T && (
              <path d={`M${x(l.deadline_week)},${y + 3} l4,${-0} l-4,${laneH - 6} l-4,${-(laneH - 6)} z`} fill="none" stroke="var(--ink-3)" strokeWidth={1} opacity={0.6} />
            )}
            {active && (
              <rect x={x(s.start!)} y={y + laneH * 0.28} width={Math.max(2, x(endW) - x(s.start!))} height={laneH * 0.44} rx={3}
                fill={missed ? "var(--bad)" : done ? "var(--ink-2)" : "var(--s1)"} opacity={missed ? 0.55 : 1} />
            )}
            {missed && <text x={x(s.missed!) + 6} y={y + laneH / 2 + 4} style={{ font: "600 11px var(--sans)", fill: "var(--bad)" }}>✕ missed</text>}
            {s.results.map((r, j) => {
              const good = r.type === "offer" || GOOD.test(r.label);
              const cx = x(r.week);
              const cy = y + laneH / 2;
              return r.type === "offer"
                ? <path key={j} d={`M${cx},${cy - 8} L${cx + 8},${cy} L${cx},${cy + 8} L${cx - 8},${cy} Z`} fill="var(--s3)" stroke="var(--panel-2)" strokeWidth={2} />
                : <circle key={j} cx={cx} cy={cy} r={5} fill={good ? "var(--ink)" : "var(--panel-2)"} stroke="var(--ink)" strokeWidth={1.5} />;
            })}
          </g>
        );
      })}

      {/* playhead */}
      <line x1={x(t)} x2={x(t)} y1={L.t - 20} y2={L.t + lanes.length * laneH + 4} stroke="var(--ink)" strokeWidth={2} />

      {/* right panel: state at t */}
      <g transform={`translate(${FW - L.r + 34}, ${L.t})`}>
        <text style={{ font: "600 12px var(--sans)", fill: "var(--ink-2)", letterSpacing: "0.04em" }}>IN THIS WORLD, SO FAR</text>
        <text y={30} style={{ font: "500 15px var(--sans)", fill: "var(--ink)" }}>{offers.length} offer{offers.length === 1 ? "" : "s"}{offers.length ? ":" : ""}</text>
        {offers.slice(0, 4).map((o, i) => <text key={i} y={52 + i * 19} style={{ font: "13px var(--sans)", fill: "var(--ink)" }}>◆ {o.label.replace(/_/g, " ")}</text>)}
        <text y={140} style={{ font: "14px var(--sans)", fill: "var(--ink)" }}>{counts.papers} paper acceptance{counts.papers === 1 ? "" : "s"}</text>
        <text y={162} style={{ font: "14px var(--sans)", fill: "var(--ink)" }}>{counts.outputs} public output{counts.outputs === 1 ? "" : "s"} shipped</text>
        <text y={184} style={{ font: "14px var(--sans)", fill: "var(--ink)" }}>{evNow.filter((e) => e.type === "missed").length} deadline{evNow.filter((e) => e.type === "missed").length === 1 ? "" : "s"} missed</text>
      </g>
      <g>
        <text x={fanX(0)} y={fanY(1) - 14} style={{ font: "600 12px var(--sans)", fill: "var(--ink-2)", letterSpacing: "0.04em" }}>ACROSS ALL WORLDS</text>
        <line x1={fanX(0)} x2={fanX(T)} y1={fanY(0)} y2={fanY(0)} stroke="var(--rule)" />
        <path d={d3.area<number>().x((_, i) => fanX(i)).y0(fanY(0)).y1((v) => fanY(v))(posSeries) || ""} fill="var(--s3)" opacity={0.18} />
        <path d={d3.line<number>().x((_, i) => fanX(i)).y((v) => fanY(v))(posSeries.slice(0, tIdx + 1)) || ""} fill="none" stroke="var(--s3)" strokeWidth={2.5} />
        <circle cx={fanX(tIdx)} cy={fanY(posSeries[tIdx] ?? 0)} r={4.5} fill="var(--s3)" stroke="var(--panel-2)" strokeWidth={2} />
        <text x={fanX(0)} y={fanY(0) + 18} style={{ font: "12.5px var(--sans)", fill: "var(--ink)" }}>
          <tspan style={{ font: "600 13px var(--mono)" }}>{Math.round((posSeries[tIdx] ?? 0) * 100)}%</tspan> of worlds have a position secured by now
        </text>
      </g>

      {/* caption */}
      <rect x={0} y={FH - 104} width={FW} height={104} fill="var(--panel)" />
      <line x1={0} x2={FW} y1={FH - 104} y2={FH - 104} stroke="var(--rule)" />
      <foreignObject x={40} y={FH - 94} width={FW - 80} height={62}>
        <div style={{ font: "400 21px/1.3 var(--serif)", color: "var(--ink)" }}>{scene?.text}</div>
      </foreignObject>
      <text x={40} y={FH - 14} style={{ font: "11px var(--mono)", fill: "var(--ink-3)" }}>
        Simulated sample, not a prediction · run {spec.run_id} · model {spec.model_fingerprint} · data {spec.dataset_version} · seed {spec.seed}
      </text>
      {!compact && (
        <g transform={`translate(${FW - 40}, ${FH - 14})`}>
          <text textAnchor="end" style={{ font: "11px var(--sans)", fill: "var(--ink-3)" }}>bar = action in progress · ● result · ◆ offer · ✕ missed · purple line = policy rule · dashed = outside event</text>
        </g>
      )}
    </svg>
  );
}
