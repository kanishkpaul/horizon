import { useEffect } from "react";
import { CommandPalette } from "./components/CommandPalette";
import { HorizonRuler } from "./components/HorizonRuler";
import { Icon } from "./components/Icons";
import { Inspector } from "./components/Inspector";
import { api } from "./lib/api";
import { useStore } from "./lib/store";
import { Atlas } from "./views/Atlas";
import { Brief } from "./views/Brief";
import { Cockpit } from "./views/Cockpit";
import { Graph } from "./views/Graph";
import { Lab } from "./views/Lab";
import { ModelView } from "./views/ModelView";
import { RenderFrame } from "./views/RenderFrame";
import { Research } from "./views/Research";
import { Theater } from "./views/Theater";

const NAV = [
  ["brief", "Brief", "brief", "1"], ["atlas", "Atlas", "atlas", "2"], ["graph", "Graph", "graph", "3"],
  ["lab", "Scenario lab", "lab", "4"], ["theater", "Theater", "theater", "5"], ["cockpit", "Cockpit", "cockpit", "6"],
  ["model", "Model & values", "model", "7"], ["research", "Research", "research", "8"],
];

export default function App() {
  const s = useStore();
  const { route, go } = s;
  useEffect(() => {
    const k = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement)?.closest("input,textarea,select") || e.metaKey || e.ctrlKey || e.altKey) return;
      const n = NAV.find((x) => x[3] === e.key);
      if (n) go(n[0]);
    };
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [go]);
  if (route.view === "render") return <RenderFrame id={route.arg || ""} />;
  const undo = async () => {
    const r: any = await api("/api/undo", { body: {} });
    s.say(r.undone ? `Undid the last change to ${r.undone.table_name} ${r.undone.row_id}` : "Nothing to undo");
    s.refresh();
  };
  const V = { brief: Brief, atlas: Atlas, graph: Graph, lab: Lab, theater: Theater, cockpit: Cockpit, model: ModelView, research: Research }[route.view] || Brief;
  return (
    <div className="shell">
      <nav className="rail" aria-label="Workspaces">
        <div className="brand"><b>Horizon</b><span>v0.3</span></div>
        <button className="nav" onClick={() => s.setPaletteOpen(true)}><Icon name="search" />Search<span className="k">⌘K</span></button>
        <div style={{ height: 8 }} />
        {NAV.map(([id, label, icon, key]) => (
          <button key={id} className="nav" aria-current={route.view === id ? "page" : undefined} onClick={() => go(id)}>
            <Icon name={icon} />{label}<span className="k">{key}</span>
          </button>
        ))}
        <div className="rail-foot">
          <button className="nav" onClick={undo}><Icon name="undo" />Undo last edit</button>
          <button className="nav" onClick={() => s.setTheme(s.theme === "auto" ? "dark" : s.theme === "dark" ? "light" : "auto")}>
            <Icon name="sun" />Theme: {s.theme}</button>
          <div>{s.run ? <>Run <span className="mono">{s.run.id.slice(4, 19)}</span></> : "No simulation yet"}</div>
          <div>Decision support, not prediction.</div>
        </div>
      </nav>
      <HorizonRuler />
      <main className="main" id="main">
        <V />
      </main>
      <Inspector />
      <CommandPalette />
      {s.toast && <div className="tooltip" role="status" style={{ left: "50%", transform: "translateX(-50%)", bottom: 22, top: "auto" }}>{s.toast}</div>}
    </div>
  );
}
