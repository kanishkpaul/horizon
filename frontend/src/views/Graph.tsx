import cytoscape from "cytoscape";
// @ts-ignore no bundled types
import dagre from "cytoscape-dagre";
cytoscape.use(dagre);
import { useEffect, useRef, useState } from "react";
import { useApi } from "../lib/api";
import { useStore } from "../lib/store";

const cssVar = (n: string) => getComputedStyle(document.documentElement).getPropertyValue(n).trim() || "#888";

export function Graph() {
  const { route, setInspect, theme, bump } = useStore();
  const [mode, setMode] = useState<"relations" | "unlocks">("relations");
  const focus = route.arg && route.arg.startsWith("ORG-") ? route.arg : null;
  const rel = useApi<any>(mode === "relations" ? `/api/graph${focus ? `?focus=${focus}` : ""}` : null, [bump]);
  const model = useApi<any>(mode === "unlocks" ? "/api/model" : null, [bump]);
  const box = useRef<HTMLDivElement>(null);
  const cy = useRef<cytoscape.Core | null>(null);
  const [kinds, setKinds] = useState<string[]>(["self", "asset", "relationship", "organization", "opportunity", "person", "hypothesis", "outreach"]);
  const [sel, setSel] = useState<any>(null);

  useEffect(() => {
    if (!box.current) return;
    const colors = {
      self: cssVar("--ink"), asset: cssVar("--s3"), relationship: cssVar("--s6"), organization: cssVar("--ink-3"),
      opportunity: cssVar("--s1"), person: cssVar("--s7"), hypothesis: cssVar("--s2"), outreach: cssVar("--s5"),
      action: cssVar("--s1"), token: cssVar("--s4"), offer: cssVar("--s3"),
    } as Record<string, string>;
    let els: any[] = [];
    if (mode === "relations" && rel.data) {
      const nodes = rel.data.nodes.filter((n: any) => kinds.includes(n.kind));
      const ids = new Set(nodes.map((n: any) => n.id));
      els = [
        ...nodes.map((n: any) => ({ data: { ...n, color: colors[n.kind] || "#999", size: n.kind === "self" ? 34 : n.kind === "organization" ? 16 : 12 } })),
        ...rel.data.edges.filter((e: any) => ids.has(e.source) && ids.has(e.target)).map((e: any, i: number) => ({ data: { id: `e${i}`, ...e } })),
      ];
    } else if (mode === "unlocks" && model.data) {
      const acts = model.data.actions.filter((a: any) => !a.id.startsWith("opp_"));
      const toks = new Set<string>();
      model.data.unlocks.produces.forEach((p: any) => toks.add(p.token));
      model.data.unlocks.consumes.forEach((c: any) => toks.add(c.token));
      const used = new Set(model.data.unlocks.consumes.map((c: any) => c.token));
      const interesting = [...toks].filter((t) => used.has(t) || t.startsWith("offer:"));
      els = [
        ...acts.map((a: any) => ({ data: { id: a.id, label: a.name.length > 46 ? a.name.slice(0, 44) + "…" : a.name, kind: "action", color: colors.action, size: 14 } })),
        ...interesting.map((t) => ({ data: { id: "tok:" + t, label: t.replace("offer:", "offer · "), kind: t.startsWith("offer:") ? "offer" : "token", color: t.startsWith("offer:") ? colors.offer : colors.token, size: 10 } })),
        ...model.data.unlocks.produces.filter((p: any) => interesting.includes(p.token) && acts.find((a: any) => a.id === p.action))
          .map((p: any, i: number) => ({ data: { id: `p${i}`, source: p.action, target: "tok:" + p.token, rel: "produces" } })),
        ...model.data.unlocks.consumes.filter((c: any) => acts.find((a: any) => a.id === c.action))
          .map((c: any, i: number) => ({ data: { id: `c${i}`, source: "tok:" + c.token, target: c.action, rel: c.kind } })),
      ];
    }
    cy.current?.destroy();
    const c = cytoscape({
      container: box.current, elements: els,
      style: [
        { selector: "node", style: { "background-color": "data(color)", width: "data(size)", height: "data(size)", label: "data(label)",
          "font-size": 9, color: cssVar("--ink-2"), "font-family": "Instrument Sans Variable, system-ui", "text-valign": "bottom",
          "text-margin-y": 3, "text-wrap": "ellipsis", "text-max-width": mode === "unlocks" ? "150px" : "120px", "min-zoomed-font-size": 7 } as any },
        ...(mode === "unlocks" ? [{ selector: "node", style: { "text-valign": "center", "text-halign": "right", "text-margin-x": 6, "text-margin-y": 0, "font-size": 12, "min-zoomed-font-size": 0, width: 12, height: 12 } as any }] : []),
        { selector: "node[kind = 'self']", style: { "font-size": 12, "font-weight": 600, color: cssVar("--ink") } as any },
        { selector: "node[kind = 'token']", style: { shape: "diamond" } },
        { selector: "node[kind = 'offer']", style: { shape: "round-rectangle" } },
        { selector: "node[kind = 'hypothesis']", style: { shape: "triangle" } },
        { selector: "edge", style: { width: 1, "line-color": cssVar("--rule"), "curve-style": "bezier", "target-arrow-shape": mode === "unlocks" ? "triangle" : "none", "target-arrow-color": cssVar("--rule"), "arrow-scale": 0.7 } as any },
        { selector: "edge[rel = 'raises_odds']", style: { "line-style": "dashed", "line-color": cssVar("--s4"), "target-arrow-color": cssVar("--s4") } as any },
        { selector: "edge[?inferred]", style: { "line-style": "dotted" } },
        { selector: ":selected", style: { "border-width": 3, "border-color": cssVar("--focus") } as any },
      ],
      layout: mode === "unlocks"
        ? ({ name: "dagre", rankDir: "LR", nodeSep: 8, rankSep: 230, padding: 10 } as any)
        : ({ name: "cose", animate: false, nodeRepulsion: 9000, idealEdgeLength: 60, padding: 20 } as any),
    });
    c.on("tap", "node", (e) => {
      const d = e.target.data();
      setSel(d);
      if (d.kind === "opportunity") setInspect({ kind: "opportunity", id: d.id });
      if (d.kind === "hypothesis") setInspect({ kind: "hypothesis", id: d.id });
      if (d.kind === "action") setInspect({ kind: "action", id: d.id });
    });
    cy.current = c;
    return () => { c.destroy(); };
  }, [rel.data, model.data, mode, kinds.join(","), theme]);

  const K = [["self", "You", "--ink"], ["asset", "Your assets", "--s3"], ["relationship", "Your relationships", "--s6"], ["organization", "Organizations", "--ink-3"],
    ["opportunity", "Opportunities", "--s1"], ["person", "Public contacts", "--s7"], ["hypothesis", "Creation hypotheses", "--s2"], ["outreach", "Outreach targets", "--s5"]];
  return (
    <div className="page" style={{ maxWidth: "none" }}>
      <div className="page-head">
        <div><h1>Graph</h1><div className="sub">{mode === "relations"
          ? "Who and what connects you to opportunities. Edges from the sheets are recorded facts; dotted edges are hypotheses. Relationships shown are only those in your CV evidence — no private social data."
          : "How actions create the state that unlocks or strengthens other actions (AND/OR prerequisites). Solid: required; dashed: raises the odds."}</div></div>
        <div className="actions">
          <div className="seg"><button aria-pressed={mode === "relations"} onClick={() => setMode("relations")}>Relationships</button><button aria-pressed={mode === "unlocks"} onClick={() => setMode("unlocks")}>Unlock map</button></div>
          <button className="btn" onClick={() => cy.current?.fit(undefined, 30)}>Fit</button>
        </div>
      </div>
      {mode === "relations" && (
        <div className="legend" style={{ marginBottom: 8 }}>
          {K.map(([k, l, c]) => (
            <label key={k} style={{ cursor: "pointer" }}><input type="checkbox" checked={kinds.includes(k)} onChange={() => setKinds(kinds.includes(k) ? kinds.filter((x) => x !== k) : [...kinds, k])} /> <i style={{ background: `var(${c})` }} />{l}</label>
          ))}
        </div>
      )}
      {mode === "unlocks" && <div className="legend" style={{ marginBottom: 8 }}><span><i style={{ background: "var(--s1)" }} />action</span><span><i style={{ background: "var(--s4)", transform: "rotate(45deg)" }} />state (token)</span><span><i style={{ background: "var(--s3)" }} />offer</span></div>}
      <div className="panel" style={{ height: "calc(100vh - 250px)", minHeight: 420, position: "relative" }}>
        <div ref={box} style={{ position: "absolute", inset: 0 }} aria-label="Interactive graph; click a node to inspect it" />
        {(rel.loading || model.loading) && <div className="empty" style={{ position: "absolute", inset: 0 }}><span className="spin" /></div>}
        {sel && sel.kind !== "opportunity" && (
          <div className="panel" style={{ position: "absolute", left: 12, bottom: 12, padding: 10, maxWidth: 360 }}>
            <div className="faint mono" style={{ fontSize: 11 }}>{sel.kind}{sel.evidence ? ` · ${sel.evidence}` : ""}</div><b>{sel.label}</b>
          </div>
        )}
      </div>
    </div>
  );
}
