import { Fragment, useEffect, useState } from "react";
import { ACCESS, ELIG, ORIGIN_LABEL, ORIGIN_TONE, api, fdate, pct, relDays, useApi } from "../lib/api";
import { useStore } from "../lib/store";
import { Icon } from "./Icons";
import { DistPreview } from "./charts";

export function EligChip({ status }: { status?: string }) {
  const e = ELIG[status || ""] || { label: status || "–", tone: "neutral", icon: "·" };
  return <span className={`chip ${e.tone}`}><span aria-hidden>{e.icon}</span>{e.label}</span>;
}

export function OriginChip({ origin }: { origin: string }) {
  return <span className={`chip ${ORIGIN_TONE[origin] || "neutral"}`} title={origin}>{ORIGIN_LABEL[origin] || origin}</span>;
}

export function Inspector() {
  const { inspect, setInspect } = useStore();
  useEffect(() => {
    const k = (e: KeyboardEvent) => { if (e.key === "Escape") setInspect(null); };
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [setInspect]);
  if (!inspect) return null;
  return (
    <>
      <div className="drawer-scrim" onClick={() => setInspect(null)} />
      <aside className="drawer" role="dialog" aria-label="Inspector">
        {inspect.kind === "opportunity" && <OppInspector id={inspect.id} />}
        {inspect.kind === "parameter" && <ParamInspector name={inspect.id} />}
        {inspect.kind === "action" && <ActionInspector id={inspect.id} />}
        {inspect.kind === "hypothesis" && <HypInspector id={inspect.id} />}
      </aside>
    </>
  );
}

function Head({ eyebrow, title, children }: { eyebrow: string; title: string; children?: any }) {
  const { setInspect } = useStore();
  return (
    <header>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div className="faint mono" style={{ fontSize: 11 }}>{eyebrow}</div>
        <h1 style={{ fontSize: 21, marginTop: 2 }}>{title}</h1>
        {children}
      </div>
      <button className="btn ghost" aria-label="Close inspector" onClick={() => setInspect(null)}><Icon name="close" /></button>
    </header>
  );
}

function OppInspector({ id }: { id: string }) {
  const { setInspect, refresh, say } = useStore();
  const { data, reload } = useApi<any>(`/api/opportunities/${encodeURIComponent(id)}`);
  const [raw, setRaw] = useState(false);
  if (!data) return <div className="content"><span className="spin" /></div>;
  const o = data.opportunity;
  const byPred: Record<string, any[]> = {};
  for (const c of data.claims) (byPred[c.predicate] ||= []).push(c);
  const toggle = async () => {
    if (data.shortlisted) await api(`/api/shortlist/${id}`, { method: "DELETE" });
    else await api(`/api/shortlist/${id}`, { body: {} });
    say(data.shortlisted ? "Removed from the model" : "Added to the model as an application action");
    reload(); refresh();
  };
  return (
    <>
      <Head eyebrow={`${o.id} · ${o.origin}`} title={o.name}>
        <div className="row" style={{ marginTop: 8 }}>
          <span className="chip">{o.org_name}</span>
          <span className="chip">{o.type_canonical}</span>
          <span className="chip ink">{ACCESS[o.access_class] || o.access_class}</span>
          <EligChip status={data.assessment?.status} />
        </div>
      </Head>
      <div className="content">
        <div className="row">
          <button className="btn primary" onClick={toggle}>{data.shortlisted ? "Remove from model" : "Add to model"}</button>
          {o.official_url && <a className="btn" href={o.official_url} target="_blank" rel="noreferrer">Official page ↗</a>}
          {o.application_url && o.application_url !== o.official_url && <a className="btn" href={o.application_url} target="_blank" rel="noreferrer">Application ↗</a>}
        </div>
        {data.assessment && (
          <section>
            <h3>Why this eligibility status</h3>
            <ul style={{ margin: "6px 0 0", paddingLeft: 18 }}>
              {data.assessment.reasons.map((r: string, i: number) => <li key={i}>{r}</li>)}
            </ul>
            <p className="faint" style={{ fontSize: 12, marginTop: 6 }}>Rule-based check against your profile. Edit the profile to change inputs; disagree with a rule by noting it on the item.</p>
          </section>
        )}
        <dl className="kv">
          <dt>Deadline</dt><dd>{o.deadline_utc ? <>{fdate(o.deadline_utc)} <span className="faint">({relDays(o.deadline_utc)}, {o.deadline_quality})</span></> : <span className="faint">none recorded</span>}</dd>
          <dt>Raw deadline</dt><dd className="mono">{o.deadline_raw || "–"} {o.deadline_tz_raw ? `· ${o.deadline_tz_raw}` : ""}</dd>
          <dt>Location</dt><dd>{[o.country, o.region, o.location_mode].filter(Boolean).join(" · ") || "–"}</dd>
          <dt>Money</dt><dd>{o.money_text || "–"}</dd>
          <dt>Relevance (sheet)</dt><dd>R {o.rel_researcher || "–"} · D {o.rel_developer || "–"} · F {o.rel_founder || "–"}</dd>
          <dt>Verification</dt><dd>{o.verification_result} · confidence {o.confidence} · last {o.last_verified || "–"}</dd>
        </dl>
        {o.description && <p>{o.description}</p>}
        {o.why_it_matters && <p className="note">{o.why_it_matters}</p>}
        <section>
          <h3>Evidence timeline</h3>
          <p className="faint" style={{ fontSize: 12 }}>Every fact is a claim with its source, grade and validity. Superseded claims stay as history.</p>
          <div className="stack" style={{ gap: 12, marginTop: 8 }}>
            {Object.entries(byPred).map(([pred, cs]) => (
              <div key={pred}>
                <div className="mono faint" style={{ fontSize: 11, marginBottom: 4 }}>{pred}</div>
                {cs.map((c) => (
                  <div key={c.id} style={{ display: "grid", gridTemplateColumns: "22px 1fr", gap: 8, padding: "4px 0", opacity: c.status === "active" ? 1 : 0.55 }}>
                    <span className={`grade ${c.evidence_grade}`} title={`Evidence grade ${c.evidence_grade}`}>{c.evidence_grade || "?"}</span>
                    <div>
                      <div style={{ textDecoration: c.status === "superseded" ? "line-through" : "none" }}>{String(c.value).slice(0, 400)}</div>
                      <div className="faint" style={{ fontSize: 11.5 }}>
                        {c.status !== "active" && <span className="chip warn" style={{ marginRight: 6 }}>{c.status}</span>}
                        {c.verification_method} · accessed {c.accessed_at || "–"} · recorded by {c.recorded_by}
                        {c.source_url && <> · <a href={c.source_url} target="_blank" rel="noreferrer">{c.source_url.replace(/^https?:\/\/(www\.)?/, "").slice(0, 60)}</a></>}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </section>
        {data.similar.length > 0 && (
          <section>
            <h3>Semantically related</h3>
            <p className="faint" style={{ fontSize: 12 }}>{data.similarity_note}</p>
            <table className="t"><tbody>
              {data.similar.map((s: any) => (
                <tr key={s.id} className="click" onClick={() => setInspect({ kind: "opportunity", id: s.id })}>
                  <td>{s.name}<div className="faint" style={{ fontSize: 11.5 }}>{s.org_name} · {s.type_canonical}</div></td>
                  <td className="r num">{s.similarity.toFixed(2)}</td>
                </tr>))}
            </tbody></table>
          </section>
        )}
        {data.same_organization.length > 0 && (
          <section>
            <h3>Same organization ({data.same_organization.length})</h3>
            <div className="row" style={{ marginTop: 6 }}>
              {data.same_organization.slice(0, 16).map((s: any) => (
                <button key={s.id} className="chip" style={{ cursor: "pointer" }} onClick={() => setInspect({ kind: "opportunity", id: s.id })}>{s.name.slice(0, 48)}</button>
              ))}
            </div>
          </section>
        )}
        <section>
          <button className="btn sm" onClick={() => setRaw(!raw)}>{raw ? "Hide" : "Show"} all original fields ({Object.keys(o.raw || {}).length})</button>
          {raw && (
            <dl className="kv" style={{ marginTop: 8 }}>
              {Object.entries(o.raw || {}).filter(([, v]) => v !== null && v !== "").map(([k, v]) => (
                <Fragment key={k}><dt>{k}</dt><dd>{typeof v === "object" ? JSON.stringify(v) : String(v)}</dd></Fragment>
              ))}
            </dl>
          )}
        </section>
      </div>
    </>
  );
}

function ParamInspector({ name }: { name: string }) {
  const { refresh, say } = useStore();
  const { data, reload } = useApi<any>("/api/parameters");
  const [dist, setDist] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const p = data?.parameters.find((x: any) => x.name === name);
  useEffect(() => { if (p) setDist(p.dist); }, [p?.dist]);
  if (!p) return <div className="content"><span className="spin" /></div>;
  const hist = data.history.filter((h: any) => h.param_id === name);
  const save = async () => {
    try {
      await api(`/api/parameters/${name}`, { method: "PATCH", body: { dist, origin: p.origin === "calibrated" ? "calibrated" : "expert_judgment", reason: "edited in inspector" } });
      setErr(null); reload(); refresh(); say("Parameter updated. Re-run the simulation to see the effect.");
    } catch (e: any) { setErr(e.message); }
  };
  return (
    <>
      <Head eyebrow="parameter" title={p.name}><div className="row" style={{ marginTop: 8 }}><OriginChip origin={p.origin} />{p.evidence_grade && <span className={`grade ${p.evidence_grade}`}>{p.evidence_grade}</span>}</div></Head>
      <div className="content">
        <p>{p.description}</p>
        <DistPreview dist={p.dist} />
        <dl className="kv">
          <dt>Distribution</dt><dd className="mono">{p.dist}</dd>
          <dt>Mean</dt><dd className="num">{p.mean.toFixed(3)}</dd>
          <dt>10th–90th</dt><dd className="num">{p.p10.toFixed(3)} – {p.p90.toFixed(3)}</dd>
          <dt>Origin</dt><dd>{p.origin}</dd>
        </dl>
        {p.notes && <p className="note">{p.notes}</p>}
        {p.sources?.length > 0 && <section><h3>Evidence</h3><ul style={{ paddingLeft: 18 }}>{p.sources.map((s: string, i: number) => <li key={i}>{s}</li>)}</ul></section>}
        <section className="stack">
          <h3>Edit</h3>
          <label className="field">Distribution (beta(a,b), normal(mu,sd), lognormal(median,gsd), triangular(lo,mode,hi), fixed(v), bernoulli(p))
            <input className="input mono" value={dist} onChange={(e) => setDist(e.target.value)} /></label>
          {err && <div className="chip bad">✕ {err}</div>}
          <div className="row"><button className="btn primary" onClick={save}>Save distribution</button><span className="faint" style={{ fontSize: 12 }}>Edits are recorded with history and can be undone.</span></div>
        </section>
        {hist.length > 0 && (
          <section><h3>History</h3>
            {hist.map((h: any) => (<div key={h.id} className="faint" style={{ fontSize: 12 }}>{h.changed_at}: {JSON.parse(h.before_json).dist} → {JSON.parse(h.after_json).dist} ({h.reason})</div>))}
          </section>
        )}
      </div>
    </>
  );
}

function ActionInspector({ id }: { id: string }) {
  const { run, setInspect } = useStore();
  const { data } = useApi<any>("/api/model");
  const a = data?.actions.find((x: any) => x.id === id);
  if (!a) return <div className="content"><span className="spin" /></div>;
  const stats: [string, any][] = run ? Object.entries(run.strategy_results).map(([sid, r]: any) => [sid, r.action_stats[id]]).filter(([, s]) => s) as any : [];
  const unlocks = data.unlocks;
  const produced = unlocks.produces.filter((p: any) => p.action === id).map((p: any) => p.token);
  const unlockedBy = unlocks.consumes.filter((c: any) => produced.includes(c.token) && c.action !== id);
  const needs = unlocks.consumes.filter((c: any) => c.action === id);
  return (
    <>
      <Head eyebrow={`action · ${a.kind}`} title={a.name}>
        <div className="row" style={{ marginTop: 8 }}>
          {a.deadline && <span className="chip">{fdate(a.deadline)} · {relDays(a.deadline)}</span>}
          {a.deadline_basis && <span className={`chip ${a.deadline_basis.startsWith("verified") ? "good" : a.deadline_basis === "assumed" ? "warn" : "neutral"}`}>deadline {a.deadline_basis}</span>}
          {a.opportunity_id && <button className="chip" onClick={() => setInspect({ kind: "opportunity", id: a.opportunity_id })}>{a.opportunity_id} ↗</button>}
        </div>
      </Head>
      <div className="content">
        <dl className="kv">
          <dt>Effort (est.)</dt><dd className="num">{a.effort[0]}–{a.effort[2]} h, mode {a.effort[1]} h</dd>
          <dt>AI-assistable</dt><dd>{pct(a.automatable)} of the work</dd>
          <dt>Requires</dt><dd>{a.requires}</dd>
          {a.external_dependency && <><dt>Depends on</dt><dd>{a.external_dependency}</dd></>}
          {a.group && <><dt>Exclusive group</dt><dd className="mono">{a.group}</dd></>}
        </dl>
        <section>
          <h3>What it can lead to</h3>
          {a.stages.length === 0 && <p className="muted">Completes immediately; effects: {JSON.stringify(a.effects?.tokens || {})}</p>}
          {a.stages.map((s: any, i: number) => (
            <div key={i} style={{ marginTop: 6 }}>
              <div className="mono faint" style={{ fontSize: 11 }}>stage {i + 1}: {s.name} · delay {typeof s.delay === "object" ? s.delay.dist : s.delay}</div>
              {s.outcomes.map((o: any, j: number) => (
                <div key={j} style={{ padding: "3px 0" }}>
                  <b>{o.label}</b>{o.count ? ` (up to ${o.count})` : ""} <span className="faint">p = </span>
                  <ProbLink p={o.p} />
                  {Object.keys(o.tokens || {}).length > 0 && <span className="faint"> → {Object.keys(o.tokens).join(", ")}</span>}
                </div>
              ))}
              <div className="faint">otherwise: {s.otherwise.label}</div>
            </div>
          ))}
        </section>
        {(unlockedBy.length > 0 || needs.length > 0) && (
          <section>
            <h3>Dependencies</h3>
            {needs.length > 0 && <p><span className="faint">Uses state:</span> {needs.map((n: any) => `${n.token} (${n.kind === "requires" ? "required" : "raises odds"})`).join(", ")}</p>}
            {unlockedBy.length > 0 && <p><span className="faint">Feeds:</span> {[...new Set(unlockedBy.map((u: any) => u.action))].map((aid: any) => (
              <button key={aid} className="chip" style={{ margin: 2, cursor: "pointer" }} onClick={() => setInspect({ kind: "action", id: aid })}>{aid}</button>))}</p>}
          </section>
        )}
        {stats.length > 0 && (
          <section>
            <h3>In the current run ({run.id})</h3>
            <table className="t"><thead><tr><th>Strategy</th><th className="r">Done</th><th className="r">Missed</th><th className="r">Mean week</th></tr></thead><tbody>
              {stats.map(([sid, s]) => (<tr key={sid}><td>{sid}</td><td className="r num">{pct(s.p_done)}</td><td className="r num">{pct(s.p_missed)}</td><td className="r num">{s.mean_completion_week?.toFixed(1) ?? "–"}</td></tr>))}
            </tbody></table>
          </section>
        )}
      </div>
    </>
  );
}

function ProbLink({ p }: { p: any }) {
  const { setInspect } = useStore();
  if (!p) return <span>–</span>;
  const base = typeof p.base === "string" ? p.base : p.base?.dist;
  return (
    <span>
      {typeof p.base === "string" ? <button className="chip" style={{ cursor: "pointer" }} onClick={() => setInspect({ kind: "parameter", id: p.base })}>{base}</button> : <span className="mono">{base}</span>}
      {(p.shifts || []).map((s: any, i: number) => (
        <span key={i}> + <button className="chip" style={{ cursor: "pointer" }} onClick={() => setInspect({ kind: "parameter", id: s.param })}>{s.param}{s.token ? ` × ${s.token}` : ""}</button></span>
      ))}
      {p.at === "resolve" && <span className="faint"> (evaluated at decision time)</span>}
    </span>
  );
}

function HypInspector({ id }: { id: string }) {
  const { data } = useApi<any[]>("/api/hypotheses");
  const h = data?.find((x) => x.id === id);
  if (!h) return <div className="content"><span className="spin" /></div>;
  return (
    <>
      <Head eyebrow={`${h.id} · ${h.classification?.replace(/_/g, " ")}`} title={h.target_org}>
        <div className="row" style={{ marginTop: 8 }}><span className="chip">{h.target_role}</span>{h.public_lead && <span className="chip">{h.public_lead}</span>}</div>
      </Head>
      <div className="content">
        <p className="note">This is a hypothesis about useful work you could offer, not an advertised vacancy.</p>
        <dl className="kv">
          <dt>Problem</dt><dd>{h.problem}</dd>
          <dt>Why you</dt><dd>{h.why_me}</dd>
          <dt>Smallest demo</dt><dd>{h.demo_needed} <span className="faint">({h.demo_effort_low}–{h.demo_effort_high} h)</span></dd>
          <dt>Form</dt><dd>{h.collab_form}</dd>
          <dt>Access route</dt><dd>{h.access_mechanism}</dd>
          <dt>Route evidence</dt><dd>{h.access_evidence}</dd>
          <dt>Next step</dt><dd><b>{h.next_step}</b></dd>
          <dt>Upside</dt><dd>{h.upside}</dd>
          <dt>Risks</dt><dd>{h.risks}</dd>
        </dl>
        <section><h3>Evidence the problem exists</h3>
          <ul style={{ paddingLeft: 18 }}>{h.evidence.map((e: any, i: number) => <li key={i}>{e.claim} {e.url && <a href={e.url} target="_blank" rel="noreferrer">↗</a>}</li>)}</ul>
        </section>
        <section><h3>What would invalidate it</h3><ul style={{ paddingLeft: 18 }}>{h.invalidators.map((e: string, i: number) => <li key={i}>{e}</li>)}</ul></section>
      </div>
    </>
  );
}
