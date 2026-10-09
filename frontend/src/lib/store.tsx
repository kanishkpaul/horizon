import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "./api";

export type Route = { view: string; arg?: string };
export type Inspect = { kind: "opportunity" | "parameter" | "action" | "hypothesis" | "strategy"; id: string } | null;

type Ctx = {
  route: Route;
  go: (view: string, arg?: string) => void;
  inspect: Inspect;
  setInspect: (i: Inspect) => void;
  runId: string | null;
  setRunId: (id: string | null) => void;
  run: any | null;
  setRun: (r: any) => void;
  paletteOpen: boolean;
  setPaletteOpen: (b: boolean) => void;
  theme: string;
  setTheme: (t: string) => void;
  toast: string | null;
  say: (msg: string) => void;
  bump: number;
  refresh: () => void;
};

const C = createContext<Ctx>(null as any);
export const useStore = () => useContext(C);

function parseHash(): Route {
  const h = window.location.hash.replace(/^#\/?/, "");
  const [view, ...rest] = h.split("/");
  return { view: view || "brief", arg: rest.length ? decodeURIComponent(rest.join("/")) : undefined };
}

export function StoreProvider({ children }: { children: ReactNode }) {
  const [route, setRoute] = useState<Route>(parseHash());
  const [inspect, setInspect] = useState<Inspect>(null);
  const [runId, setRunIdState] = useState<string | null>(() => {
    try { return localStorage.getItem("horizon.run"); } catch { return null; }
  });
  const [run, setRun] = useState<any | null>(null);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [theme, setThemeState] = useState<string>(() => {
    try { return localStorage.getItem("horizon.theme") || "auto"; } catch { return "auto"; }
  });
  const [toast, setToast] = useState<string | null>(null);
  const [bump, setBump] = useState(0);

  useEffect(() => {
    const on = () => setRoute(parseHash());
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  useEffect(() => {
    if (theme === "auto") document.documentElement.removeAttribute("data-theme");
    else document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);
  useEffect(() => {
    if (!runId) {
      api<any[]>("/api/runs").then((rs) => { if (rs.length) setRunIdState(rs[0].id); }).catch(() => {});
      return;
    }
    api(`/api/runs/${runId}`).then(setRun).catch(() => { setRun(null); });
  }, [runId]);

  const value = useMemo<Ctx>(() => ({
    route,
    go: (view, arg) => { window.location.hash = `/${view}${arg ? "/" + encodeURIComponent(arg) : ""}`; },
    inspect, setInspect,
    runId,
    setRunId: (id) => {
      setRunIdState(id);
      try { id ? localStorage.setItem("horizon.run", id) : localStorage.removeItem("horizon.run"); } catch {}
    },
    run, setRun,
    paletteOpen, setPaletteOpen,
    theme,
    setTheme: (t) => { setThemeState(t); try { localStorage.setItem("horizon.theme", t); } catch {} },
    toast,
    say: (m) => { setToast(m); window.setTimeout(() => setToast((x) => (x === m ? null : x)), 3200); },
    bump, refresh: () => setBump((b) => b + 1),
  }), [route, inspect, runId, run, paletteOpen, theme, toast, bump]);
  return <C.Provider value={value}>{children}</C.Provider>;
}
