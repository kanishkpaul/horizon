import { Fragment, useState } from "react";
import { api, useApi } from "../lib/api";
import { useStore } from "../lib/store";

const TABS = [["ledger", "Research ledger"], ["evidence", "Evidence"], ["hypotheses", "Created opportunities"], ["outreach", "Outreach targets"],
  ["events", "Events"], ["gaps", "Search gaps"], ["docs", "Methods & docs"]];
const DOCS = ["AUDIT", "METHODOLOGY_REGISTRY", "MODEL_CARD", "ASSUMPTIONS", "VALIDATION", "DECISIONS", "RECOMMENDATIONS", "ADVERSARIAL_REVIEW", "RESEARCH_LEDGER", "PROGRESS"];

/** Minimal markdown: headings, lists, tables, paragraphs, bold/code. Docs are local project files. */
function Md({ text }: { text: string }) {
  const inline = (s: string) => s.split(/(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/g).map((p, i) => {
    if (p.startsWith("**")) return <b key={i}>{p.slice(2, -2)}</b>;
    if (p.startsWith("`")) return <code key={i} className="mono">{p.slice(1, -1)}</code>;
    const m = p.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
    if (m) return <a key={i} href={m[2]} target="_blank" rel="noreferrer">{m[1]}</a>;
    return <Fragment key={i}>{p}</Fragment>;
  });
  const out: any[] = [];
  const lines = text.split("\n");
  for (let i = 0; i < lines.length; i++) {
    const l = lines[i];
    if (/^#{1,4} /.test(l)) { const n = l.match(/^#+/)![0].length; out.push(n <= 1 ? <h1 key={i} style={{ fontSize: 22, margin: "14px 0 6px" }}>{inline(l.slice(n + 1))}</h1> : <h2 key={i} style={{ fontSize: n === 2 ? 16 : 14, margin: "14px 0 6px" }}>{inline(l.slice(n + 1))}</h2>); continue; }
    if (l.startsWith("|")) {
      const rows: string[][] = [];
      while (i < lines.length && lines[i].startsWith("|")) { if (!/^\|[\s\-|:]+\|$/.test(lines[i])) rows.push(lines[i].split("|").slice(1, -1).map((c) => c.trim())); i++; }
      i--;
      out.push(<div key={i} className="scroll"><table className="t" style={{ margin: "6px 0" }}><thead><tr>{rows[0].map((c, j) => <th key={j}>{inline(c)}</th>)}</tr></thead><tbody>{rows.slice(1).map((r, k) => <tr key={k}>{r.map((c, j) => <td key={j}>{inline(c)}</td>)}</tr>)}</tbody></table></div>);
      continue;
    }
    if (/^\s*[-*] /.test(l) || /^\s*\d+\. /.test(l)) {
      const items: string[] = [];
      while (i < lines.length && (/^\s*[-*] /.test(lines[i]) || /^\s*\d+\. /.test(lines[i]))) { items.push(lines[i].replace(/^\s*([-*]|\d+\.) /, "")); i++; }
      i--;
      out.push(<ul key={i} style={{ paddingLeft: 20, margin: "4px 0" }}>{items.map((t, j) => <li key={j}>{inline(t)}</li>)}</ul>);
      continue;
    }
    if (l.trim()) out.push(<p key={i}>{inline(l)}</p>);
  }
  return <div style={{ maxWidth: 900 }}>{out}</div>;
}

export function Research() {
  const { route, go, setInspect } = useStore();
  const tab = route.arg || "ledger";
  const r = useApi<any>(tab === "ledger" || tab === "evidence" || tab === "gaps" ? "/api/research" : null);
  const hyp = useApi<any[]>(tab === "hypotheses" ? "/api/hypotheses" : null);
  const out = useApi<any[]>(tab === "outreach" ? "/api/outreach" : null);
  const ev = useApi<any[]>(tab === "events" ? "/api/events" : null);
  const [doc, setDoc] = useState("AUDIT");
  const docTxt = useApi<string>(tab === "docs" ? `/api/docs/${doc}` : null, [doc]);
  const [cat, setCat] = useState("tech");
  return (
    <div className="page">
      <div className="page-head">
        <div><h1>Research</h1><div className="sub">What was researched, by whom, with what evidence — and what is still unknown. Nothing here was sent to anyone.</div></div>
        <div className="actions"><div className="seg">{TABS.map(([k, l]) => <button key={k} aria-pressed={tab === k} onClick={() => go("research", k)}>{l}</button>)}</div></div>
      </div>
      {tab === "ledger" && r.data && (
        <div className="stack" style={{ gap: 14 }}>
          {r.data.research_log.map((l: any) => (
            <section className="panel" key={l.id}><header><h2>{l.question}</h2><span className="chip">{l.workstream}</span><span className="hint">{l.created_at?.slice(0, 10)} · {JSON.parse(l.sources_json || "[]").join(", ")}</span></header>
              <div className="body"><Md text={l.finding || ""} /></div></section>
          ))}
        </div>
      )}
      {tab === "evidence" && r.data && (
        <div className="grid g2">
          <section className="panel"><header><h2>Claims by grade and method</h2></header>
            <div className="body"><table className="t"><thead><tr><th>Grade</th><th>Method</th><th className="r">Claims</th></tr></thead>
              <tbody>{r.data.claims_by_grade.map((c: any, i: number) => <tr key={i}><td><span className={`grade ${c.evidence_grade}`}>{c.evidence_grade ?? "?"}</span></td><td>{c.verification_method}</td><td className="r num">{c.n}</td></tr>)}</tbody></table>
              <p className="faint" style={{ fontSize: 12, marginTop: 6 }}>A = primary source states it for the current cycle (read by a Horizon worker). Workbook claims are capped at B because Horizon did not read their sources itself.</p></div></section>
          <section className="panel"><header><h2>Superseded and contradicted claims</h2><span className="hint">history is kept, never overwritten</span></header>
            <div className="body scroll" style={{ maxHeight: 520 }}>
              {r.data.contradictions.map((c: any) => (
                <div key={c.id} className="click" style={{ padding: "6px 0", borderBottom: "1px solid var(--rule-2)", cursor: "pointer" }} onClick={() => setInspect({ kind: "opportunity", id: c.subject_id })}>
                  <div className="row"><span className="chip warn">{c.status}</span><span className="mono faint" style={{ fontSize: 11 }}>{c.subject_id} · {c.predicate}</span></div>
                  <div style={{ textDecoration: "line-through", opacity: 0.6 }}>{String(c.value).slice(0, 200)}</div>
                  <div className="faint" style={{ fontSize: 11.5 }}>superseded by {c.superseded_by || c.contradicts}</div>
                </div>))}
            </div></section>
          <section className="panel" style={{ gridColumn: "1 / -1" }}><header><h2>Primary-source verification claims ({r.data.agent_claims.length})</h2></header>
            <div className="body scroll" style={{ maxHeight: 520 }}>
              <table className="t"><thead><tr><th>Grade</th><th>Subject</th><th>Predicate</th><th>Value</th><th>Source</th></tr></thead>
                <tbody>{r.data.agent_claims.map((c: any) => (
                  <tr key={c.id} className={c.subject_type === "opportunity" ? "click" : ""} onClick={() => c.subject_type === "opportunity" && setInspect({ kind: "opportunity", id: c.subject_id })}>
                    <td><span className={`grade ${c.evidence_grade}`}>{c.evidence_grade}</span></td><td className="mono" style={{ fontSize: 11 }}>{c.subject_id}</td><td>{c.predicate}</td>
                    <td style={{ maxWidth: 520 }}>{String(c.value).slice(0, 240)}</td>
                    <td>{c.source_url && <a href={c.source_url} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()}>{c.source_url.replace(/^https?:\/\/(www\.)?/, "").slice(0, 36)}</a>}</td></tr>))}</tbody></table>
            </div></section>
        </div>
      )}
      {tab === "hypotheses" && (
        <section className="panel"><header><h2>Opportunity-creation hypotheses</h2><span className="hint">useful work you could offer; not advertised vacancies</span></header>
          <div className="body">
            <table className="t"><thead><tr><th>Target</th><th>Problem</th><th>Smallest demonstration</th><th>Next step (highest information value)</th><th>Class</th></tr></thead>
              <tbody>{(hyp.data ?? []).map((h: any) => (
                <tr key={h.id} className="click" onClick={() => setInspect({ kind: "hypothesis", id: h.id })}>
                  <td><b>{h.target_org}</b><div className="faint" style={{ fontSize: 11.5 }}>{h.target_role}</div></td><td style={{ maxWidth: 300, fontSize: 12 }}>{h.problem}</td>
                  <td style={{ maxWidth: 260, fontSize: 12 }}>{h.demo_needed} <span className="faint">({h.demo_effort_low}–{h.demo_effort_high} h)</span></td>
                  <td style={{ maxWidth: 280, fontSize: 12 }}>{h.next_step}</td>
                  <td><span className={`chip ${h.classification?.startsWith("evidence") ? "neutral" : "warn"}`}>{h.classification?.startsWith("evidence") ? "evidence-supported" : "speculative"}</span></td></tr>))}</tbody></table>
          </div></section>
      )}
      {tab === "outreach" && (
        <section className="panel"><header><h2>Outreach targets from the original research</h2><span className="hint">public contacts only · nothing has been sent</span></header>
          <div className="body scroll" style={{ maxHeight: "calc(100vh - 260px)" }}>
            <table className="t"><thead><tr><th className="r">#</th><th>Entity</th><th>Ask</th><th>Why you fit</th><th>Opening evidence</th><th>Caveats</th><th>Status</th></tr></thead>
              <tbody>{(out.data ?? []).map((o: any) => (
                <tr key={o.id}><td className="r num">{o.priority}</td><td><b>{o.entity}</b><div className="faint" style={{ fontSize: 11.5 }}>{o.contact} · {o.wave}</div></td>
                  <td style={{ fontSize: 12, maxWidth: 220 }}>{o.ask}</td><td style={{ fontSize: 12, maxWidth: 260 }}>{o.why_fit}</td><td style={{ fontSize: 12, maxWidth: 220 }}>{o.opening_evidence}</td>
                  <td style={{ fontSize: 12, maxWidth: 220 }} className="faint">{o.caveats}</td><td><span className="chip">{o.status}</span></td></tr>))}</tbody></table>
          </div></section>
      )}
      {tab === "events" && (
        <section className="panel"><header><h2>Kolkata and online events (Oct 2026 – Jan 2027)</h2>
          <div className="right"><div className="seg">{[["tech", "Tech"], ["all", "All"]].map(([k, l]) => <button key={k} aria-pressed={cat === k} onClick={() => setCat(k)}>{l}</button>)}</div></div></header>
          <div className="body scroll" style={{ maxHeight: "calc(100vh - 260px)" }}>
            <table className="t"><thead><tr><th>When</th><th>Event</th><th>Where</th><th>Topic</th><th>Fee</th><th>Uncertainty</th></tr></thead>
              <tbody>{(ev.data ?? []).filter((e: any) => cat === "all" || /tech|ai|ml|data|dev|startup|research|conference|hack|workshop/i.test(`${e.category} ${e.topic} ${e.name}`)).map((e: any) => (
                <tr key={e.id}><td style={{ whiteSpace: "nowrap" }}>{e.starts_on ?? "–"}<div className="faint" style={{ fontSize: 11.5 }}>{e.when_text}</div></td>
                  <td>{e.source_url ? <a href={e.source_url} target="_blank" rel="noreferrer">{e.name}</a> : e.name}<div className="faint" style={{ fontSize: 11.5 }}>{e.category}</div></td>
                  <td>{e.location}</td><td style={{ fontSize: 12 }}>{e.topic}</td><td style={{ fontSize: 12 }}>{e.fee}</td><td className="faint" style={{ fontSize: 12, maxWidth: 260 }}>{e.availability}</td></tr>))}</tbody></table>
          </div></section>
      )}
      {tab === "gaps" && r.data && (
        <section className="panel"><header><h2>Known search gaps ({r.data.search_gaps.length})</h2><span className="hint">from the original radar's own audit trail</span></header>
          <div className="body scroll" style={{ maxHeight: "calc(100vh - 260px)" }}>
            <table className="t"><tbody>{r.data.search_gaps.map((g: any) => <tr key={g.id}><td style={{ width: 200 }}><b>{g.workstream}</b></td><td>{g.gap}</td></tr>)}</tbody></table>
          </div></section>
      )}
      {tab === "docs" && (
        <div className="grid" style={{ gridTemplateColumns: "220px minmax(0, 1fr)", alignItems: "start" }}>
          <nav className="panel"><div className="body stack" style={{ gap: 2 }}>{DOCS.map((d) => <button key={d} className="nav" aria-current={doc === d ? "page" : undefined} onClick={() => setDoc(d)}>{d.replace(/_/g, " ").toLowerCase()}</button>)}</div></nav>
          <section className="panel"><div className="body">{docTxt.data ? <Md text={docTxt.data} /> : docTxt.error ? <p className="muted">This document has not been written yet.</p> : <span className="spin" />}</div></section>
        </div>
      )}
    </div>
  );
}
