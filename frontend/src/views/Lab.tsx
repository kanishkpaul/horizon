import * as d3 from "d3";
import { useEffect, useMemo, useState } from "react";
import { OriginChip } from "../components/Inspector";
import { DominanceTable, DotRange, Histogram, Scatter, Tornado, WeekLines } from "../components/charts";
import { METRIC_LABEL, PROB_METRICS, api, fmtMetric, pct, stratColor, useApi } from "../lib/api";
import { useStore } from "../lib/store";
import { QUESTIONS } from "./Brief";

const WHATIF: { id: string; label: string; apply: (s: any) => any }[] = [
  { id: "paper_near", label: "The paper needs only 6–16 more hours", apply: (s) => ({ ...s, effort_overrides: { ...s.effort_overrides, reg_paper_arr_oct: [6, 10, 16] } }) },
  { id: "paper_far", label: "The paper needs 40–90 more hours", apply: (s) => ({ ...s, effort_overrides: { ...s.effort_overrides, reg_paper_arr_oct: [40, 60, 90] } }) },
  { id: "replies_low", label: "Outreach replies are half as likely", apply: (s) => ({ ...s, param_overrides: { ...s.param_overrides, p_reply_faculty: 0.12, p_reply_founder: 0.1 } }) },
  { id: "no_evidence", label: "Evidence (papers, referrals) has no causal effect", apply: (s) => ({ ...s, param_overrides: { ...s.param_overrides, bonus_peer_reviewed: 0, bonus_preprint: 0, bonus_referral: 0, bonus_artifact: 0, bonus_targeted_demo: 0 } }) },
  { id: "arxiv_ok", label: "You can already post to arXiv", apply: (s) => ({ ...s, param_overrides: { ...s.param_overrides, has_arxiv_endorsement: 1 } }) },
  { id: "sem8_ok", label: "8th-semester internships are allowed", apply: (s) => ({ ...s, param_overrides: { ...s.param_overrides, sem8_internship_allowed: 1 } }) },
  { id: "no_reloc", label: "You cannot relocate abroad", apply: (s) => ({ ...s, allow_relocation: false }) },
  { id: "indep", label: "Outcomes are independent (no shared factors)", apply: (s) => ({ ...s, independent_outcomes: true }) },
];

const TABS = ["Overview", "Over time", "Tradeoffs", "Uncertainty", "Robustness", "Sensitivity", "Search", "Assumptions"];
const PRESET = { adverse: { weekly_hours: 50, ai_multiplier: 0.85, effort_bias: 1.75 }, central: { weekly_hours: 60, ai_multiplier: 1.25, effort_bias: 1.4 }, aggressive: { weekly_hours: 72, ai_multiplier: 2.0, effort_bias: 1.1 } } as Record<string, any>;

export function Lab() {
  const { run, setRunId, refresh, say, setInspect, bump } = useStore();
  const strategies = useApi<any[]>("/api/strategies", [bump]);
  const objs = useApi<any>("/api/objectives");
  const [sel, setSel] = useState<string[]>([]);
  const [obj, setObj] = useState("balanced");
  const [preset, setPreset] = useState("central");
  const [knobs, setKnobs] = useState<any>(PRESET.central);
  const [whatif, setWhatif] = useState<string[]>([]);
  const [worlds, setWorlds] = useState(3000);
  const [seed, setSeed] = useState(20261009);
  const [busy, setBusy] = useState(false);
  const [tab, setTab] = useState("Overview");
  useEffect(() => { if (strategies.data && !sel.length) setSel(strategies.data.filter((s: any) => s.origin === "preset").map((s: any) => s.id)); }, [strategies.data]);
  useEffect(() => { if (run) { setObj(run.objective.id); } }, [run?.id]);

  const scenario = useMemo(() => {
    let s: any = { preset, name: preset, ...knobs, effort_overrides: {}, param_overrides: {} };
    for (const w of WHATIF) if (whatif.includes(w.id)) s = w.apply(s);
    if (whatif.length) s.name = `${preset} + ${whatif.length} what-if`;
    return s;
  }, [preset, knobs, whatif]);

  const go = async () => {
    setBusy(true);
    try {
      const r: any = await api("/api/simulate", { body: { strategies: sel, objective: obj, scenario, n_worlds: worlds, seed, label: scenario.name } });
      setRunId(r.id); refresh();
      say(`Exact recomputation: ${r.strategies.length} strategies × ${r.n_worlds.toLocaleString()} worlds in ${(r.duration_ms / 1000).toFixed(1)} s`);
    } catch (e: any) { say(e.message); } finally { setBusy(false); }
  };

  return (
    <div className="page" style={{ maxWidth: "none" }}>
      <div className="page-head">
        <div><h1>Scenario lab</h1><div className="sub">Change assumptions and re-simulate. Every run recomputes exactly (no cached approximations) and is stored with its seed, model fingerprint and parameter values.</div></div>
      </div>
      <div className="grid" style={{ gridTemplateColumns: "minmax(280px, 330px) minmax(0, 1fr)", alignItems: "start" }}>
        <aside className="panel" style={{ position: "sticky", top: 12 }}>
          <div className="body stack" style={{ gap: 12 }}>
            <label className="field">Value model
              <select className="input" value={obj} onChange={(e) => setObj(e.target.value)}>{(objs.data?.profiles ?? []).map((p: any) => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
            <div className="field">Effort scenario
              <div className="seg">{Object.keys(PRESET).map((p) => <button key={p} aria-pressed={preset === p} onClick={() => { setPreset(p); setKnobs(PRESET[p]); }}>{p}</button>)}</div></div>
            <Slider label="Total weekly work hours (incl. classes)" min={35} max={90} step={1} v={knobs.weekly_hours} on={(v) => setKnobs({ ...knobs, weekly_hours: v })} fmt={(v) => `${v} h`} />
            <Slider label="AI speed-up on automatable work" min={0.7} max={3} step={0.05} v={knobs.ai_multiplier} on={(v) => setKnobs({ ...knobs, ai_multiplier: v })} fmt={(v) => `×${v.toFixed(2)}`} />
            <Slider label="Effort overrun vs. estimates" min={0.9} max={2.2} step={0.05} v={knobs.effort_bias} on={(v) => setKnobs({ ...knobs, effort_bias: v })} fmt={(v) => `×${v.toFixed(2)}`} />
            <p className="faint" style={{ fontSize: 11.5 }}>Evidence: people take ~1.64× their own estimates (Buehler 1994); measured AI effects range from 19% slower (METR 2025) to 56% faster (Copilot RCT). Output flattens above ~49 h/week.</p>
            <div className="field">What if…
              <div className="stack" style={{ gap: 4 }}>
                {WHATIF.map((w) => (
                  <label key={w.id} className="row" style={{ gap: 6, color: "var(--ink)", fontSize: 12.5 }}>
                    <input type="checkbox" checked={whatif.includes(w.id)} onChange={() => setWhatif(whatif.includes(w.id) ? whatif.filter((x) => x !== w.id) : [...whatif, w.id])} />{w.label}</label>
                ))}
              </div>
            </div>
            <div className="field">Strategies
              <div className="stack" style={{ gap: 3, maxHeight: 220, overflow: "auto" }}>
                {(strategies.data ?? []).map((s: any) => (
                  <label key={s.id} className="row" style={{ gap: 6, color: "var(--ink)", fontSize: 12.5 }}>
                    <input type="checkbox" checked={sel.includes(s.id)} onChange={() => setSel(sel.includes(s.id) ? sel.filter((x) => x !== s.id) : [...sel, s.id])} />
                    <i style={{ width: 9, height: 9, borderRadius: 2, background: stratColor(s.id, []), display: "inline-block" }} />{s.name}
                    {s.origin !== "preset" && <span className="chip">{s.origin}</span>}
                  </label>
                ))}
              </div>
            </div>
            <div className="row">
              <label className="field" style={{ flex: 1 }}>Worlds
                <select className="input" value={worlds} onChange={(e) => setWorlds(+e.target.value)}>{[500, 1000, 3000, 6000, 12000].map((n) => <option key={n} value={n}>{n.toLocaleString()}</option>)}</select></label>
              <label className="field" style={{ flex: 1 }}>Seed<input className="input mono" value={seed} onChange={(e) => setSeed(+e.target.value || 0)} /></label>
            </div>
            <button className="btn primary" onClick={go} disabled={busy || !sel.length}>{busy && <span className="spin" />}Run simulation</button>
          </div>
        </aside>
        <section>
          {!run ? <div className="panel"><div className="empty">Run a simulation to see results.</div></div> : (
            <>
              <div className="row" style={{ marginBottom: 10 }}>
                <div className="seg" role="tablist">{TABS.map((t) => <button key={t} role="tab" aria-pressed={tab === t} onClick={() => setTab(t)}>{t}</button>)}</div>
                <span className="faint mono" style={{ fontSize: 11, marginLeft: "auto" }}>{run.id} · {run.scenario.name} · {run.n_worlds.toLocaleString()} worlds · seed {run.seed}</span>
              </div>
              {run.warnings.length > 0 && tab !== "Assumptions" && (
                <div className="note" style={{ marginBottom: 10 }}>{run.warnings.map((w: string, i: number) => <div key={i}>⚠ {w}</div>)}</div>
              )}
              {tab === "Overview" && <Overview run={run} />}
              {tab === "Over time" && <OverTime run={run} />}
              {tab === "Tradeoffs" && <Tradeoffs run={run} />}
              {tab === "Uncertainty" && <Uncertainty run={run} onParam={(p) => setInspect({ kind: "parameter", id: p })} />}
              {tab === "Robustness" && <Robustness run={run} />}
              {tab === "Sensitivity" && <Sensitivity run={run} scenario={scenario} />}
              {tab === "Search" && <Search run={run} scenario={scenario} />}
              {tab === "Assumptions" && <Assumptions run={run} />}
            </>
          )}
        </section>
      </div>
    </div>
  );
}

function Slider({ label, min, max, step, v, on, fmt }: { label: string; min: number; max: number; step: number; v: number; on: (v: number) => void; fmt: (v: number) => string }) {
  return (
    <label className="field">
      <span className="row" style={{ justifyContent: "space-between" }}>{label}<b className="num" style={{ color: "var(--ink)" }}>{fmt(v)}</b></span>
      <input type="range" min={min} max={max} step={step} value={v} onChange={(e) => on(+e.target.value)} />
    </label>
  );
}

const names = (run: any) => Object.fromEntries(run.strategies.map((s: any) => [s.id, s.name]));
const ids = (run: any) => run.strategies.map((s: any) => s.id);

function Overview({ run }: { run: any }) {
  const N = names(run);
  const I = ids(run);
  const [metric, setMetric] = useState("position_by_grad");
  const [focus, setFocus] = useState(run.analysis.ranking[0].strategy);
  const r = run.strategy_results;
  return (
    <div className="grid g2">
      <section className="panel">
        <header><h2>Ranking under {run.objective.name}</h2><span className="hint">{run.objective.risk?.measure === "mean" ? "expected value" : `${run.objective.risk?.measure} (${run.objective.risk?.alpha})`} · bar = 10–90%</span></header>
        <div className="body">
          <DotRange label="Strategy scores" rows={run.analysis.ranking.map((x: any) => ({ id: x.strategy, name: N[x.strategy], color: stratColor(x.strategy, I), mean: x.score, lo: x.p10, hi: x.p90, dim: !x.feasible, note: `±${x.se.toFixed(3)} MC s.e.${x.feasible ? "" : " · infeasible"}` }))} />
          {run.analysis.top_vs_runner_up && (
            <p className="note" style={{ marginTop: 8 }}>
              {N[run.analysis.top_vs_runner_up.top]} vs {N[run.analysis.top_vs_runner_up.runner_up]}: difference {run.analysis.top_vs_runner_up.mean_diff.toFixed(3)} ± {run.analysis.top_vs_runner_up.se.toFixed(3)} (z = {run.analysis.top_vs_runner_up.z.toFixed(1)}).
              {run.analysis.top_vs_runner_up.resolved ? " The ordering is resolved at this sample size." : " Not resolved: treat as tied or add worlds."}
            </p>
          )}
        </div>
      </section>
      <section className="panel">
        <header><h2>Metric explorer</h2>
          <div className="right"><select className="input" value={metric} onChange={(e) => setMetric(e.target.value)}>{Object.keys(METRIC_LABEL).map((k) => <option key={k} value={k}>{METRIC_LABEL[k]}</option>)}</select></div></header>
        <div className="body">
          <DotRange label={METRIC_LABEL[metric]} fmt={(v) => fmtMetric(metric, v)} rows={I.map((s: string) => {
            const m = r[s].metrics[metric];
            return { id: s, name: N[s], color: stratColor(s, I), mean: m.mean, lo: m.p10, hi: m.p90 };
          })} />
          <div className="row" style={{ marginTop: 8 }}>
            <span className="faint" style={{ fontSize: 12 }}>Distribution across worlds for</span>
            <select className="input" value={focus} onChange={(e) => setFocus(e.target.value)}>{I.map((s: string) => <option key={s} value={s}>{N[s]}</option>)}</select>
          </div>
          <Histogram hist={r[focus].metrics[metric].hist} color={stratColor(focus, I)} fmt={(v) => (PROB_METRICS.has(metric) ? (v ? "yes" : "no") : d3.format("~g")(v))} label={`${METRIC_LABEL[metric]} for ${N[focus]}`} />
        </div>
      </section>
      <section className="panel" style={{ gridColumn: "1 / -1" }}>
        <header><h2>Actions inside {N[focus]}</h2><span className="hint">share of worlds where each action completed, was missed, or never became possible</span></header>
        <div className="body scroll" style={{ maxHeight: 420 }}>
          <table className="t">
            <thead><tr><th>Action</th><th className="r">Done</th><th className="r">Missed</th><th className="r">Never enabled</th><th className="r">Mean week</th><th>Most common results</th></tr></thead>
            <tbody>{Object.entries(r[focus].action_stats).map(([aid, s]: any) => (
              <tr key={aid}><td>{run.actions[aid]?.name ?? aid}</td>
                <td className="r num">{pct(s.p_done)}</td><td className="r num" style={{ color: s.p_missed > 0.2 ? "var(--bad)" : undefined }}>{pct(s.p_missed)}</td>
                <td className="r num">{pct(s.p_never_enabled + s.p_dropped)}</td><td className="r num">{s.mean_completion_week?.toFixed(1) ?? "–"}</td>
                <td style={{ fontSize: 12 }}>{Object.entries(s.outcomes).filter(([, v]: any) => v > 0.01).sort((a: any, b: any) => b[1] - a[1]).slice(0, 3).map(([k, v]: any) => `${k.split(" → ")[1]} ${pct(v)}`).join(" · ")}</td></tr>
            ))}</tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function OverTime({ run }: { run: any }) {
  const N = names(run);
  const I = ids(run);
  const start = new Date(run.start_date + "T00:00:00+05:30");
  const series = (k: string) => I.map((s: string) => ({ id: s, name: N[s], color: stratColor(s, I), values: run.strategy_results[s].series[k], dashed: stratColor(s, I) === "var(--ink-2)" }));
  return (
    <div className="grid">
      <section className="panel"><header><h2>Share of worlds with a post-graduation position secured</h2><span className="hint">fan of policies over time · hover for values</span></header>
        <div className="body"><WeekLines label="Probability of a secured position over time" series={series("position")} yMax={1} start={start} gradWeek={run.graduation_week} /></div></section>
      <div className="grid g2">
        <section className="panel"><header><h2>Peer-reviewed papers (mean)</h2></header>
          <div className="body"><WeekLines label="Mean peer-reviewed papers over time" series={series("peer_reviewed")} yFmt={d3.format(".2f")} start={start} gradWeek={run.graduation_week} height={200} /></div></section>
        <section className="panel"><header><h2>Share of worlds in a deadline crunch</h2></header>
          <div className="body"><WeekLines label="Crunch share over time" series={series("crunch")} start={start} gradWeek={run.graduation_week} height={200} /></div></section>
        <section className="panel"><header><h2>Hours used per week (mean)</h2></header>
          <div className="body"><WeekLines label="Hours used per week" series={series("hours")} yFmt={d3.format(".0f")} start={start} gradWeek={run.graduation_week} height={200} /></div></section>
        <section className="panel"><header><h2>New professional ties (mean, cumulative)</h2></header>
          <div className="body"><WeekLines label="Ties over time" series={series("ties")} yFmt={d3.format(".1f")} start={start} gradWeek={run.graduation_week} height={200} /></div></section>
      </div>
    </div>
  );
}

function Tradeoffs({ run }: { run: any }) {
  const N = names(run);
  const I = ids(run);
  const [xm, setXm] = useState("peer_reviewed");
  const [ym, setYm] = useState("position_by_grad");
  const means = run.analysis.means;
  return (
    <div className="grid g2">
      <section className="panel"><header><h2>Tradeoff map</h2>
        <div className="right">
          <select className="input" value={xm} onChange={(e) => setXm(e.target.value)}>{Object.keys(METRIC_LABEL).map((k) => <option key={k} value={k}>{METRIC_LABEL[k]}</option>)}</select>
          <span className="faint">vs</span>
          <select className="input" value={ym} onChange={(e) => setYm(e.target.value)}>{Object.keys(METRIC_LABEL).map((k) => <option key={k} value={k}>{METRIC_LABEL[k]}</option>)}</select>
        </div></header>
        <div className="body">
          <Scatter xLabel={METRIC_LABEL[xm]} yLabel={METRIC_LABEL[ym]} xFmt={(v) => fmtMetric(xm, v)} yFmt={(v) => fmtMetric(ym, v)}
            front={run.analysis.pareto.front}
            points={I.map((s: string) => ({ id: s, name: N[s], color: stratColor(s, I), x: means[s][xm], y: means[s][ym], dashed: stratColor(s, I) === "var(--ink-2)" }))} />
          <p className="faint" style={{ fontSize: 12 }}>The dashed line is the trade-off frontier for these two metrics (when more of both is better). Larger dots are on the Pareto front across {run.analysis.pareto.metrics.length} metrics ({run.analysis.pareto.metrics.map((m: string) => METRIC_LABEL[m]).join(", ")}): no other strategy is at least as good on all of them and better on one. A dominated strategy is never the right choice under any weighting of those metrics.</p>
        </div></section>
      <section className="panel"><header><h2>Paired dominance</h2></header>
        <div className="body"><DominanceTable ids={run.analysis.dominance.ids} M={run.analysis.dominance.p_better} names={N} /></div></section>
    </div>
  );
}

function Uncertainty({ run, onParam }: { run: any; onParam: (p: string) => void }) {
  const N = names(run);
  const I = ids(run);
  const best = run.analysis.ranking[0].strategy;
  const conv = run.analysis.convergence[best];
  const start = new Date(run.start_date);
  return (
    <div className="grid g2">
      <section className="panel" style={{ gridColumn: "1 / -1" }}><header><h2>Value of information</h2><span className="hint">how much better the decision would be if this unknown were resolved before choosing</span></header>
        <div className="body scroll">
          <table className="t"><thead><tr><th>Unknown</th><th>Origin</th><th className="r">EVPPI</th><th className="r">raw</th><th className="r">noise floor</th><th>Best strategy if you knew (low → high)</th></tr></thead>
            <tbody>{(run.analysis.voi ?? []).slice(0, 20).map((v: any) => (
              <tr key={v.param} className="click" onClick={() => onParam(v.param)}>
                <td><b style={{ fontWeight: 550 }}>{QUESTIONS[v.param]?.q ?? v.param}</b><div className="faint mono" style={{ fontSize: 11 }}>{v.param}</div></td>
                <td><OriginChip origin={v.origin} /></td>
                <td className="r num"><b>{v.evppi.toFixed(3)}</b></td><td className="r num faint">{v.evppi_raw.toFixed(3)}</td><td className="r num faint">{v.noise_floor.toFixed(3)}</td>
                <td style={{ fontSize: 11.5 }}>{v.decision_sensitive ? <span className="chip warn">⇄</span> : null} {[...new Set(v.best_by_bin as string[])].map((s) => N[s] ?? s).join(" → ")}</td>
              </tr>))}</tbody></table>
          <p className="faint" style={{ fontSize: 11.5, marginTop: 6 }}>Nonparametric EVPPI: worlds are grouped by the parameter's value, the best strategy is chosen within each group, and the gain over choosing once is reported minus the same statistic on shuffled values (noise floor). Strong & Oakley (2014) motivate the regression approach; binning is used here for transparency.</p>
        </div></section>
      <section className="panel"><header><h2>What drives {N[best]}'s value</h2><span className="hint">Spearman correlation with world utility</span></header>
        <div className="body">
          <table className="t"><tbody>{(run.analysis.sensitivity ?? []).map((s: any) => (
            <tr key={s.param} className="click" onClick={() => onParam(s.param)}><td className="mono" style={{ fontSize: 11.5 }}>{s.param}</td>
              <td style={{ width: "45%" }}><div className="bar-track"><div className="bar-fill" style={{ width: `${Math.abs(s.rho) * 100 / 0.6}%`, maxWidth: "100%", background: s.rho > 0 ? "var(--s1)" : "var(--s2)" }} /></div></td>
              <td className="r num">{s.rho.toFixed(2)}</td></tr>))}</tbody></table>
        </div></section>
      <section className="panel"><header><h2>Monte Carlo convergence</h2><span className="hint">running mean of {N[best]}'s utility</span></header>
        <div className="body">
          <WeekLines label="Running mean" start={start} yFmt={d3.format(".2f")} height={180}
            xTick={(i) => `n = ${conv.running_mean[i]?.n.toLocaleString() ?? ""}`}
            series={[{ id: best, name: "running mean", color: stratColor(best, I), values: conv.running_mean.map((r: any) => r.mean) }]}
            yMax={Math.max(...conv.running_mean.map((r: any) => r.mean)) * 1.05} />
          <dl className="kv"><dt>Worlds</dt><dd className="num">{conv.n.toLocaleString()}</dd><dt>Std. error (iid)</dt><dd className="num">{conv.se_iid.toFixed(4)}</dd><dt>Std. error (batch means)</dt><dd className="num">{conv.se_batch_means?.toFixed(4)}</dd><dt>Relative s.e.</dt><dd className="num">{pct(conv.relative_se, 2)}</dd></dl>
          <p className="faint" style={{ fontSize: 11.5 }}>The x-axis here is sample count, not time. More worlds shrink sampling error only; they cannot fix a wrong model.</p>
        </div></section>
    </div>
  );
}

function Robustness({ run }: { run: any }) {
  const [res, setRes] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const N = names(run);
  const go = async () => { setBusy(true); try { setRes(await api("/api/compare-scenarios", { body: { strategies: ids(run), objective: run.objective.id, n_worlds: 1500 } })); } finally { setBusy(false); } };
  return (
    <section className="panel"><header><h2>Robustness across models</h2><span className="hint">parametric and structural alternatives; minimax regret</span>
      <div className="right"><button className="btn primary" onClick={go} disabled={busy}>{busy && <span className="spin" />}Run 7 scenarios</button></div></header>
      <div className="body">
        {!res && <p className="muted">Runs every selected strategy under adverse/central/aggressive effort, independent outcomes, no AI speed-up, evidence-has-no-effect, and no-relocation. A strategy that is never far from the best is robust even if it is rarely first.</p>}
        {res && (
          <>
            <p className="verdict" style={{ fontSize: 18 }}>Minimax-regret choice: <b>{N[res.regret.minimax_choice]}</b> — its worst shortfall against the best strategy in any scenario is {res.regret.max_regret[res.regret.minimax_choice].toFixed(3)}.</p>
            <div className="scroll"><table className="t" style={{ marginTop: 10 }}>
              <thead><tr><th>Strategy</th>{res.scenarios.map((s: string) => <th key={s} className="r">{s}</th>)}<th className="r">Max regret</th></tr></thead>
              <tbody>{res.regret.order.map((sid: string) => (
                <tr key={sid}><td>{N[sid] ?? sid}</td>
                  {res.scenarios.map((sc: string) => {
                    const v = res.expected_scores[sc][sid];
                    const best = Math.max(...Object.values(res.expected_scores[sc]) as number[]);
                    return <td key={sc} className="r num" style={{ fontWeight: v === best ? 700 : 400 }}>{v.toFixed(2)}</td>;
                  })}
                  <td className="r num"><b>{res.regret.max_regret[sid].toFixed(2)}</b></td></tr>))}</tbody></table></div>
            <p className="faint" style={{ fontSize: 11.5, marginTop: 6 }}>Bold = best in that scenario. {res.n_worlds.toLocaleString()} worlds per cell.</p>
          </>
        )}
      </div></section>
  );
}

function Sensitivity({ run, scenario }: { run: any; scenario: any }) {
  const [res, setRes] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const N = names(run);
  const go = async () => { setBusy(true); try { setRes(await api("/api/tornado", { body: { strategies: ids(run), objective: run.objective.id, n_worlds: 800, scenario } })); } finally { setBusy(false); } };
  return (
    <section className="panel"><header><h2>One-at-a-time sensitivity (tornado)</h2>
      <div className="right"><button className="btn primary" onClick={go} disabled={busy}>{busy && <span className="spin" />}Compute (~1 min)</button></div></header>
      <div className="body">
        {!res && <p className="muted">Fixes each uncertain parameter at its 10th and then 90th percentile, re-simulates every strategy, and records how the leading strategy's score moves and whether the leader changes.</p>}
        {res && <>
          <p className="muted">Strategy: <b>{N[res.strategy]}</b> · base score {res.base_score.toFixed(3)} · {res.note}</p>
          <Tornado label="Tornado chart" base={res.base_score} rows={res.rows.slice(0, 18).map((r: any) => ({ name: r.param, low: r.low_score, high: r.high_score, lowV: d3.format(".3~g")(r.low_value), highV: d3.format(".3~g")(r.high_value), flips: r.flips_choice, origin: r.origin }))} />
        </>}
      </div></section>
  );
}

function Search({ run, scenario }: { run: any; scenario: any }) {
  const { refresh, say } = useStore();
  const [res, setRes] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const go = async () => { setBusy(true); try { setRes(await api("/api/strategy-search", { body: { objective: run.objective.id, scenario, generations: 8, population: 24, n_worlds: 500 } })); } finally { setBusy(false); } };
  const save = async (f: any) => { await api("/api/strategies", { method: "PUT", body: { ...f.spec, id: `disc_${Date.now().toString(36)}` } }); refresh(); say(`Saved ${f.spec.name} as a strategy; select it in the panel and re-run.`); };
  return (
    <section className="panel"><header><h2>Discover strategies</h2><span className="hint">NSGA-II over action portfolios and parallelism</span>
      <div className="right"><button className="btn primary" onClick={go} disabled={busy}>{busy && <span className="spin" />}Search (~1–2 min)</button></div></header>
      <div className="body">
        {!res && <p className="muted">Evolves portfolios of actions (with prerequisites repaired and standard contingency rules attached) to find policies that are not dominated on value, P(position by graduation) and crunch. The front is re-evaluated with more worlds before display.</p>}
        {res && <>
          <p className="faint" style={{ fontSize: 12 }}>{res.method} · {res.evaluations} candidates evaluated. Best preset score: {Math.max(...Object.values(res.preset_scores) as number[]).toFixed(3)}.</p>
          <table className="t"><thead><tr><th>Candidate</th><th className="r">Score</th><th className="r">Position</th><th className="r">Crunch</th><th className="r">Peer-rev.</th><th>Actions</th><th /></tr></thead>
            <tbody>{res.front.map((f: any) => (
              <tr key={f.spec.id}><td><b>{f.spec.name}</b><div className="faint" style={{ fontSize: 11.5 }}>max {f.spec.max_parallel} in parallel{!f.feasible && " · infeasible"}</div></td>
                <td className="r num">{f.score.toFixed(3)}<div className="faint">±{f.se.toFixed(3)}</div></td><td className="r num">{pct(f.position_by_grad)}</td><td className="r num">{f.crunch_weeks.toFixed(1)}</td><td className="r num">{f.peer_reviewed.toFixed(2)}</td>
                <td style={{ fontSize: 11.5, maxWidth: 420 }}>{f.spec.actions.join(", ")}{f.actions_not_in_any_preset.length > 0 && <div><span className="chip warn">new: {f.actions_not_in_any_preset.join(", ")}</span></div>}</td>
                <td><button className="btn sm" onClick={() => save(f)}>Save</button></td></tr>))}</tbody></table>
        </>}
      </div></section>
  );
}

function Assumptions({ run }: { run: any }) {
  const { setInspect } = useStore();
  const ps = Object.entries(run.parameters_used) as [string, any][];
  const byOrigin: Record<string, number> = {};
  ps.forEach(([, p]) => { byOrigin[p.origin] = (byOrigin[p.origin] || 0) + 1; });
  return (
    <div className="grid g2">
      <section className="panel"><header><h2>Run record</h2><a className="btn sm" style={{ marginLeft: "auto" }} href={`/api/export/run-${run.id}.json`}>Export JSON</a></header>
        <div className="body">
          <dl className="kv">
            <dt>Run</dt><dd className="mono">{run.id}</dd><dt>Created</dt><dd>{run.created_at}</dd>
            <dt>Model</dt><dd className="mono">{run.model_version} · {run.model_fingerprint}</dd><dt>Dataset</dt><dd className="mono">{run.dataset_version}</dd>
            <dt>Seed</dt><dd className="mono">{run.seed}</dd><dt>Worlds</dt><dd className="num">{run.n_worlds.toLocaleString()}</dd>
            <dt>Algorithm</dt><dd>{run.algorithm}</dd><dt>Value model</dt><dd>{run.objective.name}: {JSON.stringify(run.objective.weights)}</dd>
            <dt>Constraints</dt><dd>{(run.objective.constraints ?? []).map((c: any) => `${c.metric} ${c.stat} ${c.op} ${c.value}${c.hard ? " (hard)" : ""}`).join("; ") || "none"}</dd>
            <dt>Scenario</dt><dd className="mono" style={{ fontSize: 11 }}>{JSON.stringify(run.scenario)}</dd>
          </dl>
        </div></section>
      <section className="panel"><header><h2>Limitations</h2></header>
        <div className="body"><ul style={{ paddingLeft: 18, margin: 0 }}>{run.limitations.map((l: string, i: number) => <li key={i} style={{ marginBottom: 6 }}>{l}</li>)}</ul>
          <div className="sep" />{run.warnings.map((w: string, i: number) => <div key={i} className="note" style={{ marginBottom: 4 }}>⚠ {w}</div>)}</div></section>
      <section className="panel" style={{ gridColumn: "1 / -1" }}><header><h2>Parameters used ({ps.length})</h2><span className="hint">{Object.entries(byOrigin).map(([k, v]) => `${v} ${k.replace(/_/g, " ")}`).join(" · ")}</span></header>
        <div className="body scroll" style={{ maxHeight: 420 }}>
          <table className="t"><thead><tr><th>Parameter</th><th>Distribution</th><th>Origin</th></tr></thead>
            <tbody>{ps.sort((a, b) => a[1].origin.localeCompare(b[1].origin)).map(([k, p]) => (
              <tr key={k} className="click" onClick={() => setInspect({ kind: "parameter", id: k })}><td className="mono" style={{ fontSize: 11.5 }}>{k}</td><td className="mono" style={{ fontSize: 11.5 }}>{p.dist}</td><td><OriginChip origin={p.origin} /></td></tr>))}</tbody></table>
        </div></section>
    </div>
  );
}
