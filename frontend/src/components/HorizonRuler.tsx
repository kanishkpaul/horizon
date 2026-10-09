import * as d3 from "d3";
import { useEffect, useMemo, useRef, useState } from "react";
import { fdate, relDays, useApi } from "../lib/api";
import { useStore } from "../lib/store";

/** The signature element: one week-ruler from today to the 52-week horizon, shared by every workspace.
 *  Tall ticks are deadlines of modelled actions (solid = verified date, hollow = assumed);
 *  short ticks are deadlines of opportunities you could apply to (eligible or needs-check). */
export function HorizonRuler() {
  const { setInspect, bump } = useStore();
  const model = useApi<any>("/api/model", [bump]);
  const ov = useApi<any>("/api/overview", [bump]);
  const ref = useRef<HTMLDivElement>(null);
  const [w, setW] = useState(900);
  const [hover, setHover] = useState<{ x: number; label: string; sub: string } | null>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setW(el.clientWidth));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  const start = model.data ? new Date(model.data.start) : new Date("2026-10-09T00:00:00+05:30");
  const end = d3.timeWeek.offset(start, model.data?.horizon_weeks ?? 52);
  const x = useMemo(() => d3.scaleTime().domain([start, end]).range([18, Math.max(200, w - 18)]), [w, model.data]);
  const now = new Date();
  const grad = model.data ? d3.timeDay.offset(start, Math.round(model.data.graduation_week * 7)) : null;
  const months = x.ticks(d3.timeMonth.every(1) as any);
  const weeks = d3.timeWeek.range(start, end);
  const actionTicks = (model.data?.actions ?? []).filter((a: any) => a.deadline && !a.id.startsWith("opp_"))
    .map((a: any) => ({ d: new Date(a.deadline), a }));
  const oppTicks = (ov.data?.upcoming_deadlines ?? []).map((o: any) => ({ d: new Date(o.deadline_utc), o }));
  const H = 74;
  return (
    <div className="ruler" ref={ref}>
      <svg role="img" aria-label="Horizon ruler: weeks from today to the planning horizon, with deadlines">
        <line x1={x(start)} x2={x(end)} y1={44} y2={44} stroke="var(--ink-3)" strokeWidth={1} />
        {weeks.map((wk) => <line key={+wk} x1={x(wk)} x2={x(wk)} y1={41} y2={47} stroke="var(--rule)" />)}
        {months.map((m) => (
          <g key={+m}>
            <line x1={x(m)} x2={x(m)} y1={36} y2={52} stroke="var(--ink-3)" />
            <text className="month" x={x(m) + 4} y={64}>{d3.timeFormat("%b %y")(m)}</text>
          </g>
        ))}
        {grad && (
          <g>
            <rect x={x(grad)} y={14} width={Math.max(0, x(end) - x(grad))} height={30} fill="var(--wash)" />
            <text className="tick-label" x={x(grad) + 4} y={24}>after graduation</text>
          </g>
        )}
        {oppTicks.map(({ d, o }: any) => (
          <line key={o.id} x1={x(d)} x2={x(d)} y1={44} y2={34} strokeWidth={6} stroke="transparent"
            onMouseEnter={() => setHover({ x: x(d), label: o.name, sub: `${fdate(o.deadline_utc)} · ${relDays(o.deadline_utc)}` })}
            onMouseLeave={() => setHover(null)} onClick={() => setInspect({ kind: "opportunity", id: o.id })}
            style={{ cursor: "pointer" }}>
          </line>
        ))}
        {oppTicks.map(({ d, o }: any) => (
          <line key={o.id + "v"} x1={x(d)} x2={x(d)} y1={44} y2={36} stroke="var(--ink-3)" strokeWidth={1} pointerEvents="none" />
        ))}
        {actionTicks.map(({ d, a }: any) => {
          const verified = (a.deadline_basis || "").startsWith("verified");
          return (
            <g key={a.id} style={{ cursor: "pointer" }}
              onMouseEnter={() => setHover({ x: x(d), label: a.name, sub: `${fdate(a.deadline)} · ${relDays(a.deadline)} · deadline ${a.deadline_basis}` })}
              onMouseLeave={() => setHover(null)} onClick={() => setInspect({ kind: "action", id: a.id })}>
              <line x1={x(d)} x2={x(d)} y1={44} y2={16} stroke="transparent" strokeWidth={8} />
              <line x1={x(d)} x2={x(d)} y1={44} y2={20} stroke="var(--ink)" strokeWidth={1.2} />
              <circle cx={x(d)} cy={18} r={3.2} fill={verified ? "var(--ink)" : "var(--panel)"} stroke="var(--ink)" strokeWidth={1.2} />
            </g>
          );
        })}
        <g>
          <line x1={x(now)} x2={x(now)} y1={8} y2={H - 4} stroke="var(--ink)" strokeWidth={2} />
          <text x={x(now) + 5} y={13} style={{ font: "600 10.5px var(--sans)", fill: "var(--ink)" }}>today</text>
        </g>
      </svg>
      {hover && (
        <div className="tooltip" style={{ left: Math.min(hover.x + (ref.current?.getBoundingClientRect().left ?? 0) + 10, window.innerWidth - 330), top: 60 }}>
          <div style={{ fontWeight: 600 }}>{hover.label}</div>
          <div style={{ opacity: 0.8 }}>{hover.sub}</div>
        </div>
      )}
    </div>
  );
}
