import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import { useStore } from "../lib/store";

const VIEWS = [
  ["brief", "Brief — what to do now"], ["atlas", "Opportunity atlas"], ["graph", "Relationship graph"],
  ["lab", "Scenario lab"], ["theater", "Strategy theater"], ["cockpit", "Execution cockpit"],
  ["model", "Model, values & profile"], ["research", "Research & evidence"],
];

export function CommandPalette() {
  const { paletteOpen, setPaletteOpen, go, setInspect } = useStore();
  const [q, setQ] = useState("");
  const [res, setRes] = useState<any[]>([]);
  const [sel, setSel] = useState(0);
  const [mode, setMode] = useState("hybrid");
  const inp = useRef<HTMLInputElement>(null);
  useEffect(() => {
    const k = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setPaletteOpen(!paletteOpen); }
      if (e.key === "/" && !paletteOpen && !(e.target as HTMLElement)?.closest("input,textarea,select")) { e.preventDefault(); setPaletteOpen(true); }
    };
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [paletteOpen, setPaletteOpen]);
  useEffect(() => { if (paletteOpen) { setTimeout(() => inp.current?.focus(), 10); } else { setQ(""); setRes([]); } }, [paletteOpen]);
  useEffect(() => {
    if (q.trim().length < 2) { setRes([]); return; }
    const t = setTimeout(() => {
      api(`/api/search?q=${encodeURIComponent(q)}&mode=${mode}&k=20`).then((r: any) => { setRes(r.results); setSel(0); }).catch(() => {});
    }, 160);
    return () => clearTimeout(t);
  }, [q, mode]);
  if (!paletteOpen) return null;
  const views = VIEWS.filter(([, l]) => !q || l.toLowerCase().includes(q.toLowerCase()));
  const items: { kind: string; title: string; sub: string; act: () => void; badge?: string }[] = [
    ...views.map(([v, l]) => ({ kind: "go to", title: l, sub: "", act: () => go(v) })),
    ...res.map((r) => ({
      kind: r.doc_type, title: r.title, sub: r.snippet,
      badge: Object.keys(r.signals).join(" + "),
      act: () => {
        if (r.doc_type === "opportunity") setInspect({ kind: "opportunity", id: r.doc_id });
        else if (r.doc_type === "hypothesis") setInspect({ kind: "hypothesis", id: r.doc_id });
        else if (r.doc_type === "outreach") go("research", "outreach");
        else if (r.doc_type === "event") go("research", "events");
        else if (r.doc_type === "organization") go("graph", r.doc_id);
      },
    })),
  ];
  const choose = (i: number) => { items[i]?.act(); setPaletteOpen(false); };
  return (
    <>
      <div className="drawer-scrim" style={{ zIndex: 59 }} onClick={() => setPaletteOpen(false)} />
      <div className="palette" role="dialog" aria-label="Search and commands">
        <input ref={inp} value={q} placeholder="Search opportunities, organizations, hypotheses, events… or jump to a view"
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") { e.preventDefault(); setSel((s) => Math.min(s + 1, items.length - 1)); }
            if (e.key === "ArrowUp") { e.preventDefault(); setSel((s) => Math.max(s - 1, 0)); }
            if (e.key === "Enter") choose(sel);
            if (e.key === "Escape") setPaletteOpen(false);
          }} />
        <div className="row" style={{ padding: "6px 12px", borderBottom: "1px solid var(--rule-2)", fontSize: 12 }}>
          <span className="faint">Retrieval</span>
          <div className="seg">{["hybrid", "lexical", "dense"].map((m) => <button key={m} aria-pressed={mode === m} onClick={() => setMode(m)}>{m}</button>)}</div>
          <span className="faint" style={{ marginLeft: "auto" }}>Hybrid = BM25 + embeddings, fused by rank. Similarity is not evidence.</span>
        </div>
        <div className="results" role="listbox">
          {items.map((it, i) => (
            <div key={i} className="item" role="option" aria-selected={i === sel} onMouseEnter={() => setSel(i)} onClick={() => choose(i)}>
              <span className="mono faint" style={{ fontSize: 11 }}>{it.kind}</span>
              <span className="t">{it.title}</span>
              <span className="mono faint" style={{ fontSize: 10.5 }}>{it.badge}</span>
              {it.sub && <span className="s">{it.sub}</span>}
            </div>
          ))}
          {q.length >= 2 && res.length === 0 && <div className="empty">No matches yet. Try fewer words or switch retrieval mode.</div>}
        </div>
      </div>
    </>
  );
}
