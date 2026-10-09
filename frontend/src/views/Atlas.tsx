import { useMemo, useState } from "react";
import { EligChip } from "../components/Inspector";
import { ACCESS, ELIG, api, fdate, relDays, useApi } from "../lib/api";
import { useStore } from "../lib/store";

const TYPES = ["research_internship", "research_fellowship", "fellowship", "research_job", "job", "internship", "competition",
  "hackathon", "grant", "compute_credits", "accelerator", "incubator", "publication_venue", "community", "event",
  "open_source_program", "education", "visa_mobility", "government_program", "award", "early_access", "investment", "other"];

export function Atlas() {
  const { setInspect, inspect, bump, refresh, say } = useStore();
  const [q, setQ] = useState("");
  const [qDeb, setQDeb] = useState("");
  const [elig, setElig] = useState<string[]>(["eligible_likely", "needs_check", "travel_or_relocation"]);
  const [type, setType] = useState("");
  const [access, setAccess] = useState("");
  const [origin, setOrigin] = useState("");
  const [sort, setSort] = useState("deadline");
  const [window_, setWindow] = useState("any");
  const params = new URLSearchParams();
  if (qDeb) params.set("q", qDeb);
  if (elig.length) params.set("eligibility_status", elig.join(","));
  if (type) params.set("type", type);
  if (access) params.set("access", access);
  if (origin) params.set("origin", origin);
  if (window_ !== "any") params.set("deadline_before", new Date(Date.now() + Number(window_) * 86400000).toISOString());
  params.set("sort", sort);
  const { data, loading } = useApi<any>(`/api/opportunities?${params}`, [bump]);
  const items = data?.items ?? [];
  const counts = useMemo(() => {
    const c: Record<string, number> = {};
    for (const it of items) c[it.access_class] = (c[it.access_class] || 0) + 1;
    return c;
  }, [items]);

  const toggleShort = async (e: React.MouseEvent, it: any) => {
    e.stopPropagation();
    if (it.shortlisted) await api(`/api/shortlist/${it.id}`, { method: "DELETE" });
    else await api(`/api/shortlist/${it.id}`, { body: {} });
    say(it.shortlisted ? `Removed ${it.name} from the model` : `Added ${it.name} to the model`);
    refresh();
  };

  return (
    <div className="page">
      <div className="page-head">
        <div><h1>Atlas</h1><div className="sub">Every opportunity from the original sheets, primary-source verification and independent discovery. Eligibility is checked against your profile; add any item to the model to simulate applying.</div></div>
        <div className="actions"><a className="btn" href="/api/export/opportunities.csv">Export CSV</a></div>
      </div>
      <div className="panel" style={{ marginBottom: 12 }}>
        <div className="body" style={{ display: "grid", gap: 10 }}>
          <div className="row">
            <input className="input" style={{ flex: "1 1 320px" }} placeholder="Search in plain language, e.g. “Indic MT evaluation internship”"
              value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && setQDeb(q)} onBlur={() => setQDeb(q)} />
            <select className="input" value={type} onChange={(e) => setType(e.target.value)} aria-label="Type">
              <option value="">All types</option>{TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
            </select>
            <select className="input" value={access} onChange={(e) => setAccess(e.target.value)} aria-label="Access class">
              <option value="">Any access class</option>{Object.entries(ACCESS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <select className="input" value={origin} onChange={(e) => setOrigin(e.target.value)} aria-label="Origin">
              <option value="">Any origin</option>
              <option value="radar_2026-10-03">Original radar sheet</option>
              <option value="verify_agent">Added by verification</option>
              <option value="discovery_agent">Independent discovery</option>
            </select>
            <select className="input" value={window_} onChange={(e) => setWindow(e.target.value)} aria-label="Deadline window">
              <option value="any">Any deadline</option><option value="14">Due within 14 days</option><option value="30">Within 30 days</option><option value="90">Within 90 days</option>
            </select>
            <div className="seg" role="group" aria-label="Sort">
              <button aria-pressed={sort === "deadline"} onClick={() => setSort("deadline")}>By deadline</button>
              <button aria-pressed={sort === "fit"} onClick={() => setSort("fit")}>By profile similarity</button>
            </div>
          </div>
          <div className="row" style={{ gap: 6 }}>
            <span className="faint" style={{ fontSize: 12 }}>Eligibility:</span>
            {Object.entries(ELIG).map(([k, e]) => (
              <button key={k} className={`chip ${elig.includes(k) ? e.tone : ""}`} style={{ cursor: "pointer", opacity: elig.includes(k) ? 1 : 0.6 }}
                aria-pressed={elig.includes(k)} onClick={() => setElig(elig.includes(k) ? elig.filter((x) => x !== k) : [...elig, k])}>
                <span aria-hidden>{e.icon}</span>{e.label}</button>
            ))}
          </div>
          <div className="faint" style={{ fontSize: 12 }}>
            {loading ? <span className="spin" /> : <b className="num" style={{ color: "var(--ink)" }}>{data?.total ?? 0}</b>} shown · {Object.entries(counts).map(([k, v]) => `${v} ${ACCESS[k]?.toLowerCase() ?? k}`).join(" · ")}
            {qDeb && <> · ranked by hybrid retrieval (BM25 + embeddings); similarity is not evidence of fit or eligibility</>}
            {sort === "fit" && !qDeb && <> · sorted by semantic similarity to your research interests</>}
          </div>
        </div>
      </div>
      <div className="panel">
        <div className="scroll" style={{ maxHeight: "calc(100vh - 330px)" }}>
          <table className="t">
            <thead><tr><th>Deadline</th><th>Opportunity</th><th>Type</th><th>Access</th><th>Eligibility</th><th className="r" title="Cosine similarity to your interests">Sim.</th><th>Model</th></tr></thead>
            <tbody>
              {items.map((it: any) => (
                <tr key={it.id} className="click" aria-selected={inspect?.id === it.id} onClick={() => setInspect({ kind: "opportunity", id: it.id })}>
                  <td style={{ whiteSpace: "nowrap" }} className="num">{it.deadline_utc ? <>{fdate(it.deadline_utc)}<div className="faint">{relDays(it.deadline_utc)}</div></> : <span className="faint">rolling / none</span>}</td>
                  <td style={{ maxWidth: 460 }}><b style={{ fontWeight: 550 }}>{it.name}</b><div className="faint" style={{ fontSize: 12 }}>{it.org_name}{it.country ? ` · ${it.country}` : ""}{it.location_mode && it.location_mode !== "unknown" ? ` · ${it.location_mode.replace("_", " ")}` : ""}</div></td>
                  <td><span className="chip">{it.type_canonical?.replace(/_/g, " ")}</span></td>
                  <td style={{ fontSize: 12 }}>{ACCESS[it.access_class] ?? it.access_class}<div className="faint mono" style={{ fontSize: 10.5 }}>{it.origin}</div></td>
                  <td><EligChip status={it.eligibility} /><div className="faint" style={{ fontSize: 11.5, maxWidth: 260 }}>{it.reasons?.[0]?.slice(0, 90)}</div></td>
                  <td className="r num">{it.fit != null ? it.fit.toFixed(2) : "–"}</td>
                  <td><button className={`btn sm ${it.shortlisted ? "primary" : ""}`} onClick={(e) => toggleShort(e, it)}>{it.shortlisted ? "In model" : "Add"}</button></td>
                </tr>
              ))}
            </tbody>
          </table>
          {!loading && items.length === 0 && <div className="empty">Nothing matches these filters. Widen the eligibility chips or clear the search.</div>}
        </div>
      </div>
    </div>
  );
}
