import { useEffect, useState } from "react";
import { EligChip, OriginChip } from "../components/Inspector";
import { DotRange } from "../components/charts";
import { api, fdate, fmtMetric, pct, relDays, stratColor, useApi } from "../lib/api";
import { useStore } from "../lib/store";

/** Plain-language questions for parameters whose value would change the decision. */
export const QUESTIONS: Record<string, { q: string; how: string }> = {
  has_arxiv_endorsement: { q: "Can you already post to arXiv (cs.CL / cs.AI) without a new endorsement?", how: "Try starting a submission on arXiv; it tells you immediately." },
  sem8_internship_allowed: { q: "Does HIT allow a full-time research internship in the 8th semester?", how: "Ask the department / placement cell (one email)." },
  continual_arc_code_available: { q: "Will Unify release the Continual-ARC code?", how: "Ask Daniel Lenton directly; you have an existing relationship." },
  p_predoc_offer: { q: "How selective are India predoc programs for someone with your record?", how: "Ask a current or former MSR India Research Fellow." },
  p_reply_faculty: { q: "What reply rate will your faculty outreach get?", how: "Send the first 3 emails and log the replies; the model updates." },
  p_reply_founder: { q: "What reply rate will founder outreach get?", how: "Send 3 and log replies." },
  p_epoch_offer: { q: "Is the Epoch AI role open to India-based candidates, and still open?", how: "Check the job page / email Epoch's hiring contact." },
  hazard_epoch_filled_week: { q: "Is the Epoch AI role still open?", how: "Check Epoch's careers page." },
  hazard_mcw_scoop_week: { q: "How close is the competing world-model work to Daedalus?", how: "Read the two overlapping 2026 papers the discovery worker found." },
  p_arr_main: { q: "How strong is the register paper relative to typical *ACL submissions?", how: "Ask Prof. Naskar for a candid score estimate." },
  p_startup_offer_targeted: { q: "How often do targeted applications to Indian AI startups convert?", how: "Ask two people hired at Sarvam/Soket how they got in." },
  bonus_referral: { q: "How much does a referral actually help at your target organizations?", how: "Ask recent hires." },
  p_tmlr_accept: { q: "Is MCW TMLR-ready (claims supported by evidence)?", how: "Ask a TMLR-published researcher to skim it." },
};

export function Brief() {
  const { run, runId, setRunId, go, setInspect, refresh, say } = useStore();
  const ov = useApi<any>("/api/overview");
  const objs = useApi<any>("/api/objectives");
  const model = useApi<any>("/api/model");
  const [obj, setObj] = useState<string>("balanced");
  const [re, setRe] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { if (run) setObj(run.objective.id); }, [run?.id]);
  useEffect(() => {
    if (!run || obj === run.objective.id) { setRe(null); return; }
    api(`/api/runs/${run.id}/reanalyze`, { body: { objective: obj } }).then(setRe).catch(() => setRe(null));
  }, [obj, run?.id]);

  const simulate = async () => {
    setBusy(true);
    try {
      const r: any = await api("/api/simulate", { body: { objective: obj, n_worlds: 3000, label: "Brief run" } });
      setRunId(r.id); refresh(); say(`Simulated ${r.strategies.length} strategies × ${r.n_worlds.toLocaleString()} worlds in ${(r.duration_ms / 1000).toFixed(1)} s`);
    } catch (e: any) { say(e.message); } finally { setBusy(false); }
  };

  const ranking = re?.ranking ?? run?.analysis.ranking ?? [];
  const names: Record<string, string> = Object.fromEntries((run?.strategies ?? []).map((s: any) => [s.id, s.name]));
  const ids = ranking.map((r: any) => r.strategy);
  const top = ranking[0];
  const tvr = re?.top_vs_runner_up ?? run?.analysis.top_vs_runner_up;
  const profName = objs.data?.profiles.find((p: any) => p.id === obj)?.name ?? obj;
  const tr = top && run ? run.strategy_results[top.strategy] : null;
  const now = Date.now();
  const urgent = (model.data?.actions ?? []).filter((a: any) => a.deadline && !a.id.startsWith("opp_") && new Date(a.deadline).getTime() > now && new Date(a.deadline).getTime() - now < 21 * 86400000)
    .sort((a: any, b: any) => a.deadline.localeCompare(b.deadline));
  const voi = (run?.analysis.voi ?? []).filter((v: any) => v.evppi > 0).slice(0, 7);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="faint mono" style={{ fontSize: 11 }}>{new Date().toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long", year: "numeric" })}</div>
          <h1>Brief</h1>
        </div>
        <div className="actions">
          <label className="field" style={{ gridAutoFlow: "column", alignItems: "center", gap: 8 }}>Value model
            <select className="input" value={obj} onChange={(e) => setObj(e.target.value)}>
              {(objs.data?.profiles ?? []).map((p: any) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </label>
          <button className="btn primary" onClick={simulate} disabled={busy}>{busy ? <span className="spin" /> : null}Run a fresh simulation</button>
        </div>
      </div>

      {!run && <div className="panel"><div className="empty">No simulation has been run yet. Run one to rank strategies under your value model.</div></div>}

      {run && top && (
        <section className="panel" style={{ marginBottom: 14 }}>
          <div className="body" style={{ padding: "18px 20px" }}>
            <p className="verdict">
              Under <em>{profName}</em> values, <b>{names[top.strategy] ?? top.strategy}</b> ranks first
              {tvr && !tvr.resolved ? <>, but it is <em>statistically tied</em> with {names[tvr.runner_up]} (it wins in {pct(tvr.p_world_top_better)} of paired worlds)</> : tvr ? <>; it beats {names[tvr.runner_up]} in {pct(tvr.p_world_top_better)} of paired worlds</> : null}.
              {tr && <> It secures a post-graduation position in {pct(tr.metrics.position_by_grad.mean)} of simulated worlds, with {tr.metrics.peer_reviewed.mean.toFixed(2)} peer-reviewed papers and {tr.metrics.crunch_weeks.mean.toFixed(1)} deadline-crunch weeks on average.</>}
            </p>
            <p className="muted" style={{ marginTop: 10, maxWidth: 900 }}>
              Treat this as a comparison of policies under explicit assumptions, not a forecast. {run.warnings.length} warning{run.warnings.length === 1 ? "" : "s"} apply
              (placeholder parameters and assumed deadlines); the ranking changes with the value model — try the selector above.
              <button className="btn sm ghost" onClick={() => go("lab")}>Open the scenario lab →</button>
            </p>
          </div>
        </section>
      )}

      <div className="grid g-main">
        <div className="stack" style={{ gap: 14 }}>
          <section className="panel">
            <header><h2>Due in the next three weeks</h2><span className="hint">Modelled action deadlines · solid dot = verified date</span></header>
            <div className="body">
              <table className="t"><tbody>
                {urgent.map((a: any) => (
                  <tr key={a.id} className="click" onClick={() => setInspect({ kind: "action", id: a.id })}>
                    <td style={{ width: 110 }}><b className="num">{fdate(a.deadline)}</b><div className="faint" style={{ fontSize: 11.5 }}>{relDays(a.deadline)}</div></td>
                    <td>{a.name}{a.external_dependency && <div className="faint" style={{ fontSize: 12 }}>Depends on: {a.external_dependency}</div>}</td>
                    <td><span className={`chip ${a.deadline_basis?.startsWith("verified") ? "good" : "warn"}`}>{a.deadline_basis}</span></td>
                  </tr>
                ))}
                {urgent.length === 0 && <tr><td className="faint">Nothing modelled is due in the next three weeks.</td></tr>}
              </tbody></table>
              <div className="sep" />
              <div className="row" style={{ justifyContent: "space-between" }}>
                <h3>Opportunity deadlines you could still meet</h3>
                <button className="btn sm ghost" onClick={() => go("atlas")}>All in the atlas →</button>
              </div>
              <table className="t" style={{ marginTop: 6 }}><tbody>
                {(ov.data?.upcoming_deadlines ?? []).slice(0, 10).map((o: any) => (
                  <tr key={o.id} className="click" onClick={() => setInspect({ kind: "opportunity", id: o.id })}>
                    <td style={{ width: 110 }} className="num">{fdate(o.deadline_utc)}<div className="faint" style={{ fontSize: 11.5 }}>{relDays(o.deadline_utc)}</div></td>
                    <td>{o.name}<div className="faint" style={{ fontSize: 11.5 }}>{o.org_name} · {o.type_canonical}</div></td>
                    <td><EligChip status={o.eligibility} /></td>
                  </tr>
                ))}
              </tbody></table>
            </div>
          </section>

          {run && (
            <section className="panel">
              <header><h2>Strategies under {profName}</h2><span className="hint">score = {objs.data?.profiles.find((p: any) => p.id === obj)?.risk?.measure === "mean" ? "expected value" : "risk-adjusted value"} · bar = 10th–90th percentile across worlds</span></header>
              <div className="body">
                <DotRange label="Strategy scores" rows={ranking.map((r: any) => ({
                  id: r.strategy, name: names[r.strategy] ?? r.strategy, color: stratColor(r.strategy, ids),
                  mean: r.score, lo: r.p10, hi: r.p90, dim: !r.feasible,
                  note: r.feasible ? undefined : "Violates a hard constraint of this value model",
                }))} />
                <table className="t" style={{ marginTop: 10 }}>
                  <thead><tr><th>Strategy</th><th className="r">Position by grad.</th><th className="r">Peer-reviewed</th><th className="r">Open pathways</th><th className="r">Pay (₹L, median)</th><th className="r">Crunch wks</th></tr></thead>
                  <tbody>{ranking.map((r: any) => {
                    const m = run.strategy_results[r.strategy].metrics;
                    return (
                      <tr key={r.strategy}><td><i style={{ display: "inline-block", width: 9, height: 9, borderRadius: 2, background: stratColor(r.strategy, ids), marginRight: 6 }} />{names[r.strategy]}{!r.feasible && <span className="chip bad" style={{ marginLeft: 6 }}>✕ infeasible</span>}</td>
                        <td className="r num">{pct(m.position_by_grad.mean)}</td><td className="r num">{m.peer_reviewed.mean.toFixed(2)}</td>
                        <td className="r num">{m.optionality.mean.toFixed(2)}</td><td className="r num">{m.best_comp_lpa.p50.toFixed(1)}</td>
                        <td className="r num">{m.crunch_weeks.mean.toFixed(1)}</td></tr>);
                  })}</tbody>
                </table>
              </div>
            </section>
          )}
        </div>

        <div className="stack" style={{ gap: 14 }}>
          {run && (
            <section className="panel">
              <header><h2>Questions worth answering first</h2><span className="hint">expected value of perfect information, net of a noise floor</span></header>
              <div className="body">
                {voi.length === 0 && <p className="muted">No single unknown changes the ranking enough to clear the noise floor.</p>}
                {voi.map((v: any) => (
                  <div key={v.param} style={{ padding: "8px 0", borderBottom: "1px solid var(--rule-2)" }}>
                    <div className="row" style={{ justifyContent: "space-between" }}>
                      <b style={{ maxWidth: "75%" }}>{QUESTIONS[v.param]?.q ?? v.description ?? v.param}</b>
                      <span className="num">{v.evppi.toFixed(3)}</span>
                    </div>
                    <div className="row" style={{ marginTop: 3, gap: 6 }}>
                      <OriginChip origin={v.origin} />
                      {v.decision_sensitive && <span className="chip warn">⇄ changes the best strategy</span>}
                      <button className="chip" style={{ cursor: "pointer" }} onClick={() => setInspect({ kind: "parameter", id: v.param })}>{v.param}</button>
                    </div>
                    {QUESTIONS[v.param] && <div className="faint" style={{ fontSize: 12, marginTop: 3 }}>How to find out: {QUESTIONS[v.param].how}</div>}
                  </div>
                ))}
                <p className="faint" style={{ fontSize: 11.5, marginTop: 8 }}>Units are value-model points. Numbers this small mean the answer refines the plan rather than overturning it.</p>
              </div>
            </section>
          )}
          <section className="panel">
            <header><h2>What the model doesn't know about you</h2><button className="btn sm ghost" style={{ marginLeft: "auto" }} onClick={() => go("model", "profile")}>Edit profile →</button></header>
            <div className="body">
              {(ov.data?.profile_unknowns ?? []).map((u: any) => (
                <div key={u.id} style={{ padding: "5px 0", borderBottom: "1px solid var(--rule-2)" }}>
                  <b>{u.label}</b>{u.notes && <div className="faint" style={{ fontSize: 12 }}>{u.notes}</div>}
                </div>
              ))}
            </div>
          </section>
          <section className="panel">
            <header><h2>Corpus</h2></header>
            <div className="body">
              {ov.data && (
                <dl className="kv">
                  <dt>Opportunities</dt><dd className="num">{ov.data.counts.opportunities} ({Object.entries(ov.data.counts.eligibility).map(([k, v]) => `${v} ${k.replace(/_/g, " ")}`).join(" · ")})</dd>
                  <dt>Claims</dt><dd className="num">{ov.data.counts.claims.toLocaleString()} from {ov.data.counts.sources} sources</dd>
                  <dt>Creation hypotheses</dt><dd className="num">{ov.data.counts.hypotheses}</dd>
                  <dt>Dataset</dt><dd className="mono">{ov.data.dataset_version}</dd>
                  <dt>Simulation runs</dt><dd className="num">{ov.data.counts.runs}</dd>
                </dl>
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
