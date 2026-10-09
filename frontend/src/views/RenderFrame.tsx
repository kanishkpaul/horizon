import { useEffect, useState } from "react";
import { FH, FW, TheaterFrame } from "../components/TheaterFrame";
import { api } from "../lib/api";

declare global {
  interface Window { __horizonReady?: boolean; __horizonSetT?: (t: number) => Promise<void>; }
}

/** Headless render target: #/render/<mediaId>. The video renderer calls window.__horizonSetT(t)
 *  for each frame and screenshots the frame. Same component as the interactive theater. */
export function RenderFrame({ id }: { id: string }) {
  const [spec, setSpec] = useState<any>(null);
  const [t, setT] = useState(0);
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", "light");
    api(`/api/media/${id}/spec`).then(setSpec);
  }, [id]);
  useEffect(() => {
    if (!spec) return;
    window.__horizonSetT = (nt: number) => new Promise((res) => { setT(nt); requestAnimationFrame(() => requestAnimationFrame(() => res())); });
    document.fonts.ready.then(() => { window.__horizonReady = true; });
  }, [spec]);
  if (!spec) return null;
  return (
    <div id="frame" style={{ width: FW, height: FH, overflow: "hidden", background: "var(--panel-2)" }}>
      <TheaterFrame spec={spec} t={t} compact={false} />
    </div>
  );
}
