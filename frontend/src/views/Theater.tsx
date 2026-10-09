import { useEffect, useMemo, useRef, useState } from "react";
import { Icon } from "../components/Icons";
import { TheaterFrame, sceneAt } from "../components/TheaterFrame";
import { api, useApi } from "../lib/api";
import { useStore } from "../lib/store";

export function Theater() {
  const { run, setInspect, say, go } = useStore();
  const [strategy, setStrategy] = useState<string>("");
  const [world, setWorld] = useState(0);
  const [t, setT] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(2);
  const [narrate, setNarrate] = useState(true);
  const [rendering, setRendering] = useState<string | null>(null);
  useEffect(() => { if (run && !strategy) setStrategy(run.analysis.ranking[0].strategy); }, [run?.id]);
  const worlds = useApi<any[]>(run && strategy ? `/api/theater/worlds?run=${run.id}&strategy=${strategy}` : null);
  const spec = useApi<any>(run && strategy ? `/api/theater/spec?run=${run.id}&strategy=${strategy}&world=${world}` : null);
  const media = useApi<any[]>("/api/media");
  const raf = useRef<number>(0);
  useEffect(() => { setT(0); setPlaying(false); }, [spec.data?.run_id, strategy, world]);
  useEffect(() => {
    if (!playing || !spec.data) return;
    let last = performance.now();
    const tick = (now: number) => {
      const dt = (now - last) / 1000;
      last = now;
      setT((x) => {
        const nx = x + dt * speed;
        if (nx >= spec.data.horizon_weeks) { setPlaying(false); return spec.data.horizon_weeks; }
        return nx;
      });
      raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf.current);
  }, [playing, speed, spec.data]);
  useEffect(() => {
    const k = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement)?.closest("input,select,textarea")) return;
      if (e.key === " ") { e.preventDefault(); setPlaying((p) => !p); }
      if (e.key === "ArrowRight") jump(1);
      if (e.key === "ArrowLeft") jump(-1);
    };
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  });
  const marks = useMemo(() => (spec.data?.scenes ?? []).map((s: any) => s.t), [spec.data]);
  const jump = (dir: number) => {
    setPlaying(false);
    const ts = marks as number[];
    if (dir > 0) setT(ts.find((m) => m > t + 1e-6) ?? spec.data.horizon_weeks);
    else setT([...ts].reverse().find((m) => m < t - 1e-6) ?? 0);
  };
  const jumpDecision = () => {
    setPlaying(false);
    const d = (spec.data?.events ?? []).filter((e: any) => (e.type === "rule" || e.type === "offer" || e.type === "missed") && e.week > t + 1e-6);
    if (d.length) setT(d[0].week);
  };
  const render = async () => {
    try {
      const m: any = await api("/api/media/render", { body: { run_id: run.id, strategy, world, narrate, duration_s: 45 } });
      setRendering(m.id);
      say("Rendering video in the background…");
      const poll = window.setInterval(async () => {
        const all: any[] = await api("/api/media");
        const it = all.find((x) => x.id === m.id);
        if (it && (it.status === "done" || it.status === "error")) {
          window.clearInterval(poll); setRendering(null); media.reload();
          say(it.status === "done" ? "Video rendered" : `Render failed: ${it.error}`);
        }
      }, 2500);
    } catch (e: any) { say(e.message); }
  };
  if (!run) return <div className="page"><div className="panel"><div className="empty">Run a simulation first; the theater replays its worlds.</div></div></div>;
  const names = Object.fromEntries(run.strategies.map((s: any) => [s.id, s.name]));
  const scene = spec.data ? sceneAt(spec.data, t) : null;
  return (
    <div className="page" style={{ maxWidth: "none" }}>
      <div className="page-head">
        <div><h1>Strategy theater</h1><div className="sub">Replay one simulated world event by event. Each world is a single draw from the model, so compare several before reading anything into one.</div></div>
        <div className="actions">
          <select className="input" value={strategy} onChange={(e) => { setStrategy(e.target.value); setWorld(0); }}>{run.strategies.map((s: any) => <option key={s.id} value={s.id}>{s.name}</option>)}</select>
          <button className="btn" onClick={() => go("lab")}>Change assumptions in the lab</button>
        </div>
      </div>
      <div className="grid" style={{ gridTemplateColumns: "minmax(0, 1fr) 300px", alignItems: "start" }}>
        <div className="stack" style={{ gap: 10 }}>
          <div className="panel" style={{ overflow: "hidden" }}>
            {spec.data ? <TheaterFrame spec={spec.data} t={t} onLane={(id) => setInspect({ kind: "action", id })} /> : <div className="empty"><span className="spin" /></div>}
          </div>
          <div className="panel"><div className="body row" style={{ gap: 10 }}>
            <button className="btn" aria-label="Previous event" onClick={() => jump(-1)}><Icon name="back" /></button>
            <button className="btn primary" aria-label={playing ? "Pause" : "Play"} onClick={() => { if (t >= (spec.data?.horizon_weeks ?? 0)) setT(0); setPlaying(!playing); }}><Icon name={playing ? "pause" : "play"} />{playing ? "Pause" : "Play"}</button>
            <button className="btn" aria-label="Next event" onClick={() => jump(1)}><Icon name="step" /></button>
            <button className="btn" onClick={jumpDecision}><Icon name="flag" />Next decision</button>
            <input type="range" min={0} max={spec.data?.horizon_weeks ?? 52} step={0.05} value={t} onChange={(e) => { setPlaying(false); setT(+e.target.value); }} style={{ flex: 1, minWidth: 200 }} aria-label="Scrub time" />
            <div className="seg">{[1, 2, 4].map((s) => <button key={s} aria-pressed={speed === s} onClick={() => setSpeed(s)}>{s}×</button>)}</div>
          </div></div>
          <div className="panel"><header><h2>Why the policy did what it did</h2><span className="hint">scenes are derived from the model's event log for this world</span></header>
            <div className="body scroll" style={{ maxHeight: 260 }}>
              {(spec.data?.scenes ?? []).map((s: any, i: number) => (
                <div key={i} className="row" style={{ padding: "4px 0", cursor: "pointer", opacity: s.t <= t ? 1 : 0.5, fontWeight: scene === s ? 600 : 400 }} onClick={() => { setPlaying(false); setT(s.t); }}>
                  <span className="mono faint" style={{ width: 54, fontSize: 11 }}>wk {s.t.toFixed(1)}</span>
                  <span className={`chip ${s.kind === "offer" ? "good" : s.kind === "missed" ? "bad" : s.kind === "rule" ? "ink" : ""}`}>{s.kind}</span>
                  <span style={{ flex: 1 }}>{s.text}</span>
                </div>
              ))}
            </div></div>
        </div>
        <aside className="stack" style={{ gap: 10 }}>
          <section className="panel"><header><h2>Alternative worlds</h2><span className="hint">{worlds.data?.length ?? 0} traced</span></header>
            <div className="body scroll" style={{ maxHeight: 360 }}>
              {(worlds.data ?? []).map((w: any) => (
                <button key={w.world} className="nav" aria-current={w.world === world ? "page" : undefined} onClick={() => setWorld(w.world)} style={{ alignItems: "flex-start" }}>
                  <span className="mono" style={{ width: 26 }}>#{w.world}</span>
                  <span style={{ fontSize: 12 }}>{w.offers.length ? w.offers.map((o: string) => o.replace(/_/g, " ")).join(", ") : <span className="faint">no offer</span>}{w.missed ? <span className="faint"> · {w.missed} missed</span> : null}</span>
                </button>
              ))}
            </div></section>
          <section className="panel"><header><h2>Explainer video</h2></header>
            <div className="body stack">
              <p className="faint" style={{ fontSize: 12 }}>Renders this exact world and run to MP4 (1280×720) with burned-in captions and a WebVTT file. Narration uses the macOS system voice, locally.</p>
              <label className="row" style={{ gap: 6 }}><input type="checkbox" checked={narrate} onChange={(e) => setNarrate(e.target.checked)} />Add narration</label>
              <button className="btn primary" disabled={!!rendering} onClick={render}>{rendering ? <><span className="spin" />Rendering…</> : `Render world #${world} of ${names[strategy] ?? ""}`}</button>
              {(media.data ?? []).filter((m: any) => m.status === "done").slice(0, 4).map((m: any) => (
                <div key={m.id} className="stack" style={{ gap: 4 }}>
                  <video src={`/media/${m.path}`} controls preload="metadata" style={{ width: "100%", borderRadius: 6, border: "1px solid var(--rule)" }}>
                    {m.captions_path && <track kind="captions" src={`/media/${m.captions_path}`} srcLang="en" label="English" default />}
                  </video>
                  <div className="faint mono" style={{ fontSize: 10.5 }}>{m.id} · {m.duration_s?.toFixed(0)} s · {JSON.parse(m.spec_json || "{}").strategy_name} #{JSON.parse(m.spec_json || "{}").world}</div>
                </div>
              ))}
            </div></section>
        </aside>
      </div>
    </div>
  );
}
