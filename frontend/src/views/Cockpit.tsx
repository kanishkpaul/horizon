import { Fragment, useState } from "react";
import { api, fdate, pct, relDays, useApi } from "../lib/api";
import { useStore } from "../lib/store";

const HORIZONS = ["24h", "72h", "7d", "14d", "30d", "90d", "6m", "12m", "later"];
const HLABEL: Record<string, string> = { "24h": "Next 24 hours", "72h": "Next 72 hours", "7d": "This week", "14d": "Next two weeks",
  "30d": "This month", "90d": "Next 90 days", "6m": "Six months", "12m": "Twelve months", later: "Later" };

export function Cockpit() {
  const { run, setInspect, say, refresh, bump } = useStore();
  const items = useApi<any[]>("/api/actions", [bump]);
  const fc = useApi<any>("/api/forecasts", [bump]);
  const outs = useApi<any[]>("/api/outcomes", [bump]);
  const [strategy, setStrategy] = useState("");
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState<string | null>(null);
  const [log, setLog] = useState<any>(null);

  const generate = async () => {
    setBusy(true);
    try {
      const r: any = await api("/api/plan/generate", { body: { run_id: run?.id, strategy: strategy || undefined } });
      say(`Plan generated from ${r.strategy}: ${r.items.length} actions`); refresh();
    } catch (e: any) { say(e.message); } finally { setBusy(false); }
  };
  const setStatus = async (id: string, status: string) => { await api(`/api/actions/${id}`, { method: "PATCH", body: { status } }); refresh(); };
  const submitLog = async () => {
    try {
      const r: any = await api("/api/outcomes", { body: log });
      say(r.param_update ? `Logged. ${r.param_update.param}: mean ${pct(r.param_update.prior_mean, 1)} → ${pct(r.param_update.posterior_mean, 1)}` : "Outcome logged");
      setLog(null); refresh();
    } catch (e: any) { say(e.message); }
  };
  const groups: Record<string, any[]> = {};
  for (const it of items.data ?? []) (groups[it.horizon || "later"] ||= []).push(it);

  return (
    <div className="page">
      <div className="page-head">
        <div><h1>Execution cockpit</h1><div className="sub">Turn a simulated strategy into dated actions, track them, and log what actually happens. Logged results update the matching parameters (down-weighted, reversible).</div></div>
        <div className="actions">
          {run && <select className="input" value={strategy} onChange={(e) => setStrategy(e.target.value)}>
            <option value="">Top-ranked strategy</option>{run.strategies.map((s: any) => <option key={s.id} value={s.id}>{s.name}</option>)}</select>}
          <button className="btn primary" onClick={generate} disabled={busy || !run}>{busy && <span className="spin" />}Generate plan from current run</button>
          <a className="btn" href="/api/export/actions.json">Export</a>
        </div>
      </div>
      <div className="grid g-main">
        <div className="stack" style={{ gap: 14 }}>
          {(items.data ?? []).length === 0 && <div className="panel"><div className="empty">No actions yet. Generate a plan from the current simulation run.</div></div>}
          {HORIZONS.filter((h) => groups[h]?.length).map((h) => (
            <section className="panel" key={h}>
              <header><h2>{HLABEL[h]}</h2><span className="hint">{groups[h].length} action{groups[h].length === 1 ? "" : "s"}</span></header>
              <div className="body">
                {groups[h].map((it) => (
                  <div key={it.id} style={{ borderBottom: "1px solid var(--rule-2)", padding: "8px 0" }}>
                    <div className="row" style={{ alignItems: "flex-start" }}>
                      <input type="checkbox" aria-label="Done" checked={it.status === "done"} onChange={() => setStatus(it.id, it.status === "done" ? "todo" : "done")} style={{ marginTop: 3 }} />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <button className="btn ghost" style={{ padding: 0, fontWeight: 600, textAlign: "left", whiteSpace: "normal", textDecoration: it.status === "done" ? "line-through" : undefined }} onClick={() => setOpen(open === it.id ? null : it.id)}>{it.title}</button>
                        <div className="faint" style={{ fontSize: 12 }}>{it.due ? `${fdate(it.due)} · ${relDays(it.due)}` : "no date"} · {it.effort_hours ?? "?"} h · {it.kind}</div>
                      </div>
                      <select className="input" value={it.status} onChange={(e) => setStatus(it.id, e.target.value)} aria-label="Status">
                        {["todo", "doing", "waiting", "done", "dropped"].map((s) => <option key={s}>{s}</option>)}</select>
                      <button className="btn sm" onClick={() => setLog({ action_id: it.id, strategy_action: it.strategy_action, event_type: "result", result: "", successes: "", trials: "", weight: 0.5, mark_done: true })}>Log result</button>
                    </div>
                    {open === it.id && (
                      <dl className="kv" style={{ marginTop: 8, marginLeft: 24 }}>
                        {[["Why", it.reason], ["Objective", it.objective], ["Evidence", it.evidence], ["Prerequisites", it.prerequisites], ["Attention", it.attention], ["Automation", it.automation],
                          ["Possible outcomes", it.outcomes], ["Risk", it.risk], ["Success", it.success_criteria], ["Failure", it.failure_criteria], ["Review on", it.review_on], ["Unlocks", it.unlocks]]
                          .filter(([, v]) => v).map(([k, v]) => <Fragment key={k}><dt>{k}</dt><dd>{v}</dd></Fragment>)}
                        {it.strategy_action && <><dt>Model action</dt><dd><button className="chip" onClick={() => setInspect({ kind: "action", id: it.strategy_action })}>{it.strategy_action}</button></dd></>}
                      </dl>
                    )}
                  </div>
                ))}
              </div>
            </section>
          ))}
        </div>
        <div className="stack" style={{ gap: 14 }}>
          {log && (
            <section className="panel"><header><h2>Log a real outcome</h2></header>
              <div className="body stack">
                <label className="field">What happened<input className="input" value={log.result} onChange={(e) => setLog({ ...log, result: e.target.value })} placeholder="e.g. 2 replies out of 5 emails" /></label>
                <div className="row">
                  <label className="field" style={{ flex: 1 }}>Successes<input className="input" type="number" min={0} value={log.successes} onChange={(e) => setLog({ ...log, successes: e.target.value === "" ? "" : +e.target.value })} /></label>
                  <label className="field" style={{ flex: 1 }}>Attempts<input className="input" type="number" min={0} value={log.trials} onChange={(e) => setLog({ ...log, trials: e.target.value === "" ? "" : +e.target.value })} /></label>
                  <label className="field" style={{ flex: 1 }}>Weight<input className="input" type="number" step={0.1} min={0.1} max={1} value={log.weight} onChange={(e) => setLog({ ...log, weight: +e.target.value })} /></label>
                </div>
                <label className="field">Parameter to update (optional)<input className="input mono" value={log.param_name || ""} onChange={(e) => setLog({ ...log, param_name: e.target.value || undefined })} placeholder="auto from the action, e.g. p_reply_faculty" /></label>
                <p className="faint" style={{ fontSize: 11.5 }}>Counts update a Beta parameter by weight × observations (power prior), because a handful of your own attempts is weak evidence about the underlying rate. Undo from the rail if needed.</p>
                <div className="row"><button className="btn primary" onClick={submitLog}>Save outcome</button><button className="btn" onClick={() => setLog(null)}>Cancel</button></div>
              </div></section>
          )}
          <section className="panel"><header><h2>Recent outcomes</h2></header>
            <div className="body">
              {(outs.data ?? []).length === 0 && <p className="muted">Nothing logged yet. Each logged outcome sharpens the model's parameters.</p>}
              {(outs.data ?? []).slice(0, 12).map((o: any) => (
                <div key={o.id} style={{ padding: "4px 0", borderBottom: "1px solid var(--rule-2)" }}>
                  <b>{o.result || o.event_type}</b> <span className="faint">{o.recorded_at?.slice(0, 10)}</span>
                  {o.param_name && <div className="faint mono" style={{ fontSize: 11 }}>{o.param_name}: {o.successes}/{o.trials}</div>}
                </div>
              ))}
            </div></section>
          <Forecasts data={fc.data} reload={refresh} />
        </div>
      </div>
    </div>
  );
}

function Forecasts({ data, reload }: { data: any; reload: () => void }) {
  const [q, setQ] = useState("");
  const [p, setP] = useState(0.5);
  const [by, setBy] = useState("");
  const add = async () => { if (!q) return; await api("/api/forecasts", { body: { question: q, prob: p, resolve_by: by || null } }); setQ(""); reload(); };
  const resolve = async (id: string, outcome: boolean) => { await api("/api/forecasts", { body: { id, outcome } }); reload(); };
  return (
    <section className="panel"><header><h2>Forecasts and calibration</h2>{data?.scores?.n > 0 && <span className="hint">Brier {data.scores.brier.toFixed(3)} · n={data.scores.n}</span>}</header>
      <div className="body stack">
        <p className="faint" style={{ fontSize: 12 }}>Write down probabilities before events resolve (e.g. “ARR paper accepted to main or Findings”). Proper scoring rules show whether the model and you are calibrated over time.</p>
        <input className="input" placeholder="Question" value={q} onChange={(e) => setQ(e.target.value)} />
        <div className="row">
          <label className="field" style={{ flex: 1 }}>Probability <input className="input" type="number" step={0.05} min={0} max={1} value={p} onChange={(e) => setP(+e.target.value)} /></label>
          <label className="field" style={{ flex: 1 }}>Resolves by<input className="input" type="date" value={by} onChange={(e) => setBy(e.target.value)} /></label>
        </div>
        <button className="btn" onClick={add}>Add forecast</button>
        {(data?.forecasts ?? []).map((f: any) => (
          <div key={f.id} className="row" style={{ borderTop: "1px solid var(--rule-2)", paddingTop: 6 }}>
            <span style={{ flex: 1 }}>{f.question} <span className="num faint">{pct(f.prob)}</span></span>
            {f.outcome == null ? <><button className="btn sm" onClick={() => resolve(f.id, true)}>Happened</button><button className="btn sm" onClick={() => resolve(f.id, false)}>Didn't</button></>
              : <span className={`chip ${f.outcome ? "good" : "neutral"}`}>{f.outcome ? "✓ happened" : "– didn't"}</span>}
          </div>
        ))}
        {data?.scores?.calibration && <p className="faint" style={{ fontSize: 11.5 }}>{data.scores.note}</p>}
      </div></section>
  );
}
