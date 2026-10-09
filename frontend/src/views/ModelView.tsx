import { Fragment, useEffect, useState } from "react";
import { EligChip, OriginChip } from "../components/Inspector";
import { METRIC_LABEL, api, fdate, useApi } from "../lib/api";
import { useStore } from "../lib/store";

const TABS = [["profile", "Profile"], ["values", "Values"], ["parameters", "Parameters"], ["actions", "Actions"], ["strategies", "Strategies"], ["shortlist", "In the model"]];

export function ModelView() {
  const { route, go } = useStore();
  const tab = route.arg || "profile";
  return (
    <div className="page">
      <div className="page-head">
        <div><h1>Model & values</h1><div className="sub">Everything the simulator assumes about you, your values and the world — editable, with history and undo.</div></div>
        <div className="actions"><div className="seg">{TABS.map(([k, l]) => <button key={k} aria-pressed={tab === k} onClick={() => go("model", k)}>{l}</button>)}</div></div>
      </div>
      {tab === "profile" && <Profile />}
      {tab === "values" && <Values />}
      {tab === "parameters" && <Parameters />}
      {tab === "actions" && <Actions />}
      {tab === "strategies" && <Strategies />}
      {tab === "shortlist" && <Shortlist />}
    </div>
  );
}

const STATUS_TONE: Record<string, string> = { measured: "good", reported: "neutral", "user-supplied": "neutral", planned: "warn", assumed: "warn", unknown: "bad" };

function Profile() {
  const { say, refresh, bump } = useStore();
  const { data, reload } = useApi<any>("/api/profile", [bump]);
  const [edit, setEdit] = useState<string | null>(null);
  const [val, setVal] = useState("");
  const [st, setSt] = useState("user-supplied");
  if (!data) return <span className="spin" />;
  const dims: Record<string, any[]> = {};
  for (const it of data.items) (dims[it.dimension] ||= []).push(it);
  const save = async (id: string) => {
    await api(`/api/profile/${encodeURIComponent(id)}`, { method: "PATCH", body: { value: val, evidence_status: st } });
    setEdit(null); reload(); refresh(); say("Profile updated; eligibility re-assessed.");
  };
  return (
    <div className="grid g2">
      {Object.entries(dims).map(([dim, items]) => (
        <section className="panel" key={dim}><header><h2 style={{ textTransform: "capitalize" }}>{dim}</h2></header>
          <div className="body">
            {items.map((it) => (
              <div key={it.id} style={{ padding: "7px 0", borderBottom: "1px solid var(--rule-2)" }}>
                <div className="row" style={{ justifyContent: "space-between" }}>
                  <b style={{ fontWeight: 550 }}>{it.label}</b>
                  <span className={`chip ${STATUS_TONE[it.evidence_status] || "neutral"}`}>{it.evidence_status}</span>
                </div>
                {edit === it.id ? (
                  <div className="stack" style={{ gap: 6, marginTop: 6 }}>
                    <textarea className="input" rows={2} value={val} onChange={(e) => setVal(e.target.value)} />
                    <div className="row">
                      <select className="input" value={st} onChange={(e) => setSt(e.target.value)}>{["measured", "reported", "user-supplied", "planned", "assumed", "unknown"].map((s) => <option key={s}>{s}</option>)}</select>
                      <button className="btn primary sm" onClick={() => save(it.id)}>Save</button><button className="btn sm" onClick={() => setEdit(null)}>Cancel</button>
                    </div>
                  </div>
                ) : (
                  <div className="row" style={{ alignItems: "flex-start" }}>
                    <div style={{ flex: 1 }}>{it.value ?? <span className="faint">not known</span>}{it.notes && <div className="faint" style={{ fontSize: 12 }}>{it.notes}</div>}</div>
                    <button className="btn sm ghost" onClick={() => { setEdit(it.id); setVal(it.value ?? ""); setSt(it.evidence_status === "unknown" ? "user-supplied" : it.evidence_status); }}>Edit</button>
                  </div>
                )}
              </div>
            ))}
          </div></section>
      ))}
    </div>
  );
}

function Values() {
  const { say, refresh } = useStore();
  const { data, reload } = useApi<any>("/api/objectives");
  const [cur, setCur] = useState<any>(null);
  useEffect(() => { if (data && !cur) setCur(structuredClone(data.profiles[0])); }, [data]);
  if (!data || !cur) return <span className="spin" />;
  const metrics = Object.keys(data.defaults.refs);
  const save = async (asNew: boolean) => {
    const body = asNew ? { ...cur, id: undefined, name: `${cur.name} (mine)`, builtin: undefined } : { ...cur, builtin: undefined };
    if (!asNew && cur.builtin) { say("Built-in profiles are read-only; save a copy instead."); return; }
    const r: any = await api("/api/objectives", { method: "PUT", body });
    setCur(r); reload(); refresh(); say("Value model saved. Re-rank any run from the Brief or Lab.");
  };
  return (
    <div className="grid g-main">
      <section className="panel"><header><h2>Value model</h2>
        <div className="right"><select className="input" value={cur.id} onChange={(e) => setCur(structuredClone(data.profiles.find((p: any) => p.id === e.target.value)))}>
          {data.profiles.map((p: any) => <option key={p.id} value={p.id}>{p.name}{p.builtin ? "" : " (yours)"}</option>)}</select></div></header>
        <div className="body stack">
          <p className="muted">{cur.description}</p>
          <p className="faint" style={{ fontSize: 12 }}>Weights express what you care about, not exchange rates found in data. Each metric is scaled to its reference value and capped, so no single metric can win through scale alone. Negative weights penalise.</p>
          <table className="t"><thead><tr><th>Metric</th><th>Weight</th><th className="r">Reference = 1</th></tr></thead>
            <tbody>{metrics.map((m) => (
              <tr key={m}><td>{METRIC_LABEL[m] ?? m}</td>
                <td style={{ width: "50%" }}><div className="row"><input type="range" min={-3} max={3} step={0.25} value={cur.weights[m] ?? 0} style={{ flex: 1 }}
                  onChange={(e) => setCur({ ...cur, weights: { ...cur.weights, [m]: +e.target.value } })} aria-label={`Weight for ${m}`} />
                  <span className="num" style={{ width: 36, textAlign: "right" }}>{(cur.weights[m] ?? 0).toFixed(2)}</span></div></td>
                <td className="r num">{data.defaults.refs[m]}</td></tr>))}</tbody></table>
          <div className="row">
            <label className="field">Risk measure<select className="input" value={cur.risk?.measure ?? "mean"} onChange={(e) => setCur({ ...cur, risk: { ...cur.risk, measure: e.target.value } })}>
              <option value="mean">Expected value</option><option value="cvar">CVaR (mean of worst α)</option><option value="quantile">Quantile</option></select></label>
            {cur.risk?.measure !== "mean" && <label className="field">α<input className="input" type="number" step={0.05} min={0.05} max={0.95} value={cur.risk?.alpha ?? 0.2} onChange={(e) => setCur({ ...cur, risk: { ...cur.risk, alpha: +e.target.value } })} /></label>}
          </div>
          <h3>Hard constraints</h3>
          {(cur.constraints ?? []).map((c: any, i: number) => (
            <div key={i} className="row">
              <select className="input" value={c.metric} onChange={(e) => { const cs = [...cur.constraints]; cs[i] = { ...c, metric: e.target.value }; setCur({ ...cur, constraints: cs }); }}>{metrics.map((m) => <option key={m} value={m}>{METRIC_LABEL[m]}</option>)}</select>
              <select className="input" value={c.stat} onChange={(e) => { const cs = [...cur.constraints]; cs[i] = { ...c, stat: e.target.value }; setCur({ ...cur, constraints: cs }); }}>{["mean", "p10", "p50", "p90"].map((s) => <option key={s}>{s}</option>)}</select>
              <select className="input" value={c.op} onChange={(e) => { const cs = [...cur.constraints]; cs[i] = { ...c, op: e.target.value }; setCur({ ...cur, constraints: cs }); }}>{[">=", "<="].map((s) => <option key={s}>{s}</option>)}</select>
              <input className="input" type="number" step={0.05} value={c.value} style={{ width: 80 }} onChange={(e) => { const cs = [...cur.constraints]; cs[i] = { ...c, value: +e.target.value }; setCur({ ...cur, constraints: cs }); }} />
              <button className="btn sm ghost" onClick={() => setCur({ ...cur, constraints: cur.constraints.filter((_: any, j: number) => j !== i) })}>Remove</button>
            </div>
          ))}
          <button className="btn sm" onClick={() => setCur({ ...cur, constraints: [...(cur.constraints ?? []), { metric: "position_by_grad", stat: "mean", op: ">=", value: 0.8, hard: true }] })}>Add constraint</button>
          <div className="row"><button className="btn primary" onClick={() => save(true)}>Save as my own profile</button>{!cur.builtin && <button className="btn" onClick={() => save(false)}>Update this profile</button>}</div>
        </div></section>
      <section className="panel"><header><h2>Why several value models</h2></header>
        <div className="body">
          <p>The simulator estimates what different policies might lead to. It cannot tell you what to want. Research impact, compensation, founder upside, optionality and autonomy pull in different directions, and the right weighting is yours.</p>
          <p className="muted">Hard constraints keep non-negotiables out of the trade-off (lexicographic preference): a strategy that violates one is marked infeasible regardless of its score. Risk measures change attitude to downside: CVaR judges a strategy by its worst worlds; a high quantile by its plausible upside.</p>
          <p className="muted">Switch value models in the Brief to see which conclusions survive your own disagreement with yourself.</p>
        </div></section>
    </div>
  );
}

function Parameters() {
  const { setInspect, bump } = useStore();
  const { data } = useApi<any>("/api/parameters", [bump]);
  const [f, setF] = useState("");
  if (!data) return <span className="spin" />;
  const counts: Record<string, number> = {};
  data.parameters.forEach((p: any) => { counts[p.origin] = (counts[p.origin] || 0) + 1; });
  return (
    <section className="panel"><header><h2>Parameter registry ({data.parameters.length})</h2><span className="hint">{Object.entries(counts).map(([k, v]) => `${v} ${k.replace(/_/g, " ")}`).join(" · ")}</span>
      <div className="right"><input className="input" placeholder="Filter" value={f} onChange={(e) => setF(e.target.value)} /></div></header>
      <div className="body scroll" style={{ maxHeight: "calc(100vh - 260px)" }}>
        <table className="t"><thead><tr><th>Parameter</th><th>Origin</th><th>Distribution</th><th className="r">Mean</th><th className="r">10–90%</th><th>Evidence</th></tr></thead>
          <tbody>{data.parameters.filter((p: any) => !f || (p.name + p.description).toLowerCase().includes(f.toLowerCase())).map((p: any) => (
            <tr key={p.name} className="click" onClick={() => setInspect({ kind: "parameter", id: p.name })}>
              <td><span className="mono" style={{ fontSize: 11.5 }}>{p.name}</span><div className="faint" style={{ fontSize: 12, maxWidth: 420 }}>{p.description}</div></td>
              <td><OriginChip origin={p.origin} /></td><td className="mono" style={{ fontSize: 11.5 }}>{p.dist}</td>
              <td className="r num">{p.mean.toFixed(3)}</td><td className="r num">{p.p10.toFixed(2)}–{p.p90.toFixed(2)}</td>
              <td style={{ fontSize: 11.5, maxWidth: 300 }} className="faint">{(p.sources || []).slice(0, 2).join("; ")}</td></tr>))}</tbody></table>
      </div></section>
  );
}

function Actions() {
  const { setInspect, bump } = useStore();
  const { data } = useApi<any>("/api/model", [bump]);
  if (!data) return <span className="spin" />;
  return (
    <section className="panel"><header><h2>Action catalog ({data.actions.length})</h2><span className="hint">model {data.version} · fingerprint {data.fingerprint} · edit data/seed/actions.yaml to change structure</span></header>
      <div className="body scroll" style={{ maxHeight: "calc(100vh - 260px)" }}>
        <table className="t"><thead><tr><th>Action</th><th>Kind</th><th className="r">Effort (h)</th><th className="r">AI-assistable</th><th>Deadline</th><th>Requires</th><th>Stages</th></tr></thead>
          <tbody>{data.actions.map((a: any) => (
            <tr key={a.id} className="click" onClick={() => setInspect({ kind: "action", id: a.id })}>
              <td>{a.name}<div className="faint mono" style={{ fontSize: 10.5 }}>{a.id}</div></td><td><span className="chip">{a.kind}</span></td>
              <td className="r num">{a.effort[0]}–{a.effort[2]}</td><td className="r num">{Math.round(a.automatable * 100)}%</td>
              <td style={{ whiteSpace: "nowrap" }}>{a.deadline ? <>{fdate(a.deadline)}<div><span className={`chip ${a.deadline_basis?.startsWith("verified") ? "good" : a.deadline_basis === "assumed" ? "warn" : "neutral"}`}>{a.deadline_basis}</span></div></> : <span className="faint">none</span>}</td>
              <td style={{ fontSize: 11.5 }}>{a.requires === "always" ? <span className="faint">—</span> : a.requires}</td>
              <td style={{ fontSize: 11.5 }}>{a.stages.map((s: any) => s.name).join(" → ") || <span className="faint">immediate</span>}</td></tr>))}</tbody></table>
        <div className="sep" />
        <h3>Outside events (not under your control)</h3>
        <p className="faint" style={{ fontSize: 12 }}>Hazards such as being scooped or a role being filled are modelled as weekly probabilities; some actions (posting publicly) switch them off.</p>
      </div></section>
  );
}

function Strategies() {
  const { say, refresh, bump } = useStore();
  const { data, reload } = useApi<any[]>("/api/strategies", [bump]);
  const [edit, setEdit] = useState<string | null>(null);
  const [txt, setTxt] = useState("");
  const [err, setErr] = useState<string | null>(null);
  if (!data) return <span className="spin" />;
  const save = async () => {
    try { const spec = JSON.parse(txt); await api("/api/strategies", { method: "PUT", body: spec }); setErr(null); setEdit(null); reload(); refresh(); say("Strategy saved"); }
    catch (e: any) { setErr(e.message); }
  };
  const del = async (id: string) => { await api(`/api/strategies/${id}`, { method: "DELETE" }); reload(); refresh(); };
  return (
    <div className="grid g2">
      {data.map((s) => (
        <section className="panel" key={s.id}><header><h2>{s.name}</h2><span className="chip">{s.origin}</span>
          <div className="right">
            <button className="btn sm" onClick={() => { setEdit(s.id); setTxt(JSON.stringify({ ...s, origin: undefined, updated_at: undefined, id: s.origin === "preset" ? `my_${s.id}` : s.id, name: s.origin === "preset" ? `${s.name} (edited)` : s.name }, null, 2)); }}>{s.origin === "preset" ? "Copy & edit" : "Edit"}</button>
            {s.origin !== "preset" && <button className="btn sm ghost" onClick={() => del(s.id)}>Delete</button>}</div></header>
          <div className="body">
            <p className="muted">{s.description}</p>
            <div className="faint" style={{ fontSize: 12 }}>Up to {s.max_parallel} actions in parallel · {s.actions.length} actions in priority order</div>
            <ol style={{ margin: "6px 0", paddingLeft: 20, fontSize: 12 }}>{s.actions.map((a: string) => <li key={a} className="mono" style={{ fontSize: 11.5 }}>{a}</li>)}</ol>
            {(s.rules ?? []).length > 0 && <><h3>Conditional rules</h3>{s.rules.map((r: any, i: number) => <div key={i} style={{ fontSize: 12 }}>↳ {r.label}</div>)}</>}
            {edit === s.id && <div className="stack" style={{ marginTop: 8 }}>
              <textarea className="input mono" rows={16} value={txt} onChange={(e) => setTxt(e.target.value)} style={{ fontSize: 11.5 }} />
              {err && <span className="chip bad">✕ {err}</span>}
              <div className="row"><button className="btn primary sm" onClick={save}>Save</button><button className="btn sm" onClick={() => setEdit(null)}>Cancel</button></div>
            </div>}
          </div></section>
      ))}
    </div>
  );
}

function Shortlist() {
  const { setInspect, refresh, bump } = useStore();
  const { data, reload } = useApi<any[]>("/api/shortlist", [bump]);
  if (!data) return <span className="spin" />;
  return (
    <section className="panel"><header><h2>Opportunities added to the model</h2><span className="hint">each becomes an application action (id opp_…) that strategies can include</span></header>
      <div className="body">
        {data.length === 0 && <p className="muted">Nothing added yet. Use “Add” in the Atlas.</p>}
        <table className="t"><tbody>{data.map((s: any) => (
          <tr key={s.opp_id} className="click" onClick={() => setInspect({ kind: "opportunity", id: s.opp_id })}>
            <td>{s.name}<div className="faint mono" style={{ fontSize: 10.5 }}>opp_{s.opp_id}</div></td><td>{s.type_canonical}</td><td>{fdate(s.deadline_utc)}</td><td><EligChip status={s.eligibility} /></td>
            <td><button className="btn sm" onClick={async (e) => { e.stopPropagation(); await api(`/api/shortlist/${s.opp_id}`, { method: "DELETE" }); reload(); refresh(); }}>Remove</button></td></tr>))}</tbody></table>
      </div></section>
  );
}
