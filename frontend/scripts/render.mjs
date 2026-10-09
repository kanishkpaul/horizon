// Frame-exact renderer: loads #/render/<mediaId>, steps the shared TheaterFrame through the
// timeline stored in the media spec, screenshots each frame and pipes PNGs into ffmpeg.
import { chromium } from "playwright-core";
import { spawn } from "node:child_process";
import { existsSync, readdirSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

const arg = (k, d) => { const i = process.argv.indexOf(`--${k}`); return i > 0 ? process.argv[i + 1] : d; };
const id = arg("id"), base = arg("url", "http://127.0.0.1:8765"), out = arg("out");
if (!id || !out) { console.error("usage: render.mjs --id MED-… --out file.mp4 [--url http://127.0.0.1:8765]"); process.exit(2); }

function findChrome() {
  if (process.env.HORIZON_CHROME) return process.env.HORIZON_CHROME;
  const root = join(homedir(), "Library/Caches/ms-playwright");
  const dirs = existsSync(root) ? readdirSync(root).filter((d) => d.startsWith("chromium_headless_shell-")).sort().reverse() : [];
  for (const d of dirs) {
    for (const sub of ["chrome-headless-shell-mac-arm64", "chrome-headless-shell-mac-x64", "chrome-linux"]) {
      for (const bin of ["chrome-headless-shell", "headless_shell"]) {
        const p = join(root, d, sub, bin);
        if (existsSync(p)) return p;
      }
    }
  }
  return undefined; // fall back to playwright's own resolution
}

const spec = await (await fetch(`${base}/api/media/${id}/spec`)).json();
const tl = spec.video;
const kfs = tl.keyframes; // [videoSeconds, week, sceneIndex, hold]
function at(v) {
  // returns [week, sceneIndex] for video time v
  let cur = kfs[0];
  for (let k = 0; k < kfs.length; k++) {
    const [vs, wk, si, hold] = kfs[k];
    if (v < vs) {
      const [pv, pw, psi, ph] = kfs[k - 1];
      const travelStart = pv + ph;
      const f = Math.min(1, Math.max(0, (v - travelStart) / Math.max(1e-6, vs - travelStart)));
      return [pw + f * (wk - pw), psi];
    }
    if (v <= vs + hold) return [wk, si];
    cur = kfs[k];
  }
  return [cur[1], cur[2]];
}

const browser = await chromium.launch({ executablePath: findChrome(), headless: true });
const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1, colorScheme: "light" });
await page.goto(`${base}/#/render/${id}`);
await page.waitForFunction(() => window.__horizonReady === true, null, { timeout: 30000 });
const frames = Math.ceil(tl.duration_s * tl.fps);
const ff = spawn("ffmpeg", ["-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", String(tl.fps), "-i", "-",
  "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "medium", "-movflags", "+faststart", out],
  { stdio: ["pipe", "inherit", "inherit"] });
const frameEl = await page.$("#frame");
let last = "";
let buf;
for (let i = 0; i < frames; i++) {
  const [wk, si] = at(i / tl.fps);
  const key = `${wk.toFixed(3)}|${si}`;
  if (key !== last) {   // held frames are identical: reuse the screenshot
    await page.evaluate(([t, s]) => window.__horizonSetT(t, s), [wk, si]);
    buf = await frameEl.screenshot({ type: "png" });
    last = key;
  }
  if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once("drain", r));
}
ff.stdin.end();
await new Promise((res, rej) => ff.on("close", (c) => (c === 0 ? res() : rej(new Error(`ffmpeg exited ${c}`)))));
await browser.close();
console.log(`rendered ${frames} frames → ${out}`);
