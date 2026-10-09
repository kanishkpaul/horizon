"""Explainer-video pipeline.

simulation run → theater spec (one world, one strategy) → timeline of held scenes →
optional per-scene narration (macOS `say`, local) → frames rendered by the same React
component the app uses (headless Chromium via frontend/scripts/render.mjs) → ffmpeg MP4
plus a WebVTT caption file. The media row stores the spec, so every video is traceable
to its run, model fingerprint, dataset version, seed and world.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
import uuid
from pathlib import Path

from .db import ROOT, connect, now_iso, one
from .theater import build_spec

RENDERS = ROOT / "media" / "renders"
FPS = 24
WEEK_SECONDS = 0.32          # travel speed between scenes
HOLD_KINDS = {"intro", "outro", "offer", "rule", "missed", "exogenous"}
MAX_HELD = 16


def _reading_time(text: str) -> float:
    return min(7.0, 2.2 + 0.055 * len(text))


def _say_clip(text: str, path: Path) -> float | None:
    """Render narration with the local macOS voice; return its duration in seconds."""
    if not shutil.which("say"):
        return None
    clean = re.sub(r"[#*_`]", "", text)
    subprocess.run(["say", "-r", "185", "-o", str(path), clean], check=True, capture_output=True)
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True)
    try:
        return float(out.stdout.strip())
    except ValueError:
        return None


def build_timeline(spec: dict, clip_durations: dict[int, float] | None = None) -> dict:
    scenes = spec["scenes"]
    important = [i for i, s in enumerate(scenes) if s["kind"] in HOLD_KINDS
                 or (s["kind"] == "outcome" and re.search(r"Accepted|Offer|award|Grant|Joint|merged", s["text"]))]
    if len(important) > MAX_HELD:  # keep intro/outro, then earliest decisive moments
        core = [i for i in important if scenes[i]["kind"] in ("intro", "outro")]
        rest = [i for i in important if i not in core][: MAX_HELD - len(core)]
        important = sorted(core + rest)
    clip_durations = clip_durations or {}
    kf = []  # (video_seconds, week, scene_index)
    v = 0.0
    prev_t = 0.0
    for i in important:
        s = scenes[i]
        v += max(0.0, s["t"] - prev_t) * WEEK_SECONDS
        hold = max(_reading_time(s["text"]), (clip_durations.get(i) or 0) + 0.5)
        kf.append((round(v, 3), s["t"], i, round(hold, 3)))
        v += hold
        prev_t = s["t"]
    return {"fps": FPS, "keyframes": kf, "duration_s": round(v, 3), "held": important}


def write_vtt(spec: dict, timeline: dict, path: Path) -> None:
    def ts(x):
        h, r = divmod(x, 3600)
        m, s = divmod(r, 60)
        return f"{int(h):02d}:{int(m):02d}:{s:06.3f}"
    lines = ["WEBVTT", ""]
    for n, (v, _t, i, hold) in enumerate(timeline["keyframes"]):
        lines += [str(n + 1), f"{ts(v)} --> {ts(v + hold)}", spec["scenes"][i]["text"], ""]
    path.write_text("\n".join(lines))


def start_render(con, body: dict) -> dict:
    spec = build_spec(con, body["run_id"], body["strategy"], int(body.get("world", 0)))
    mid = "MED-" + uuid.uuid4().hex[:10]
    out = RENDERS / mid
    out.mkdir(parents=True, exist_ok=True)
    narrate = bool(body.get("narrate", True)) and shutil.which("say") is not None
    con.execute("INSERT INTO media(id, created_at, sim_run_id, strategy_id, kind, spec_json, format, renderer, status)"
                " VALUES(?,?,?,?,?,?,?,?,?)",
                (mid, now_iso(), body["run_id"], body["strategy"], "trajectory_explainer", json.dumps(spec), "mp4",
                 "react-svg frames → headless chromium → ffmpeg (h264)", "queued"))
    con.commit()
    if body.get("_sync"):
        _render_job(mid, spec, narrate, body.get("app_url"))
    else:
        threading.Thread(target=_render_job, args=(mid, spec, narrate, body.get("app_url")), daemon=True).start()
    return {"id": mid, "status": "queued"}


def render_sync(con, run_id: str, strategy: str, world: int = 0, narrate: bool = True, app_url: str | None = None) -> dict:
    """Blocking render used by the CLI and tests."""
    r = start_render(con, {"run_id": run_id, "strategy": strategy, "world": world, "narrate": narrate,
                           "app_url": app_url, "_sync": True})
    return dict(one(connect(), "SELECT * FROM media WHERE id=?", (r["id"],)))


def _render_job(mid: str, spec: dict, narrate: bool, app_url: str | None):
    con = connect()
    out = RENDERS / mid
    try:
        con.execute("UPDATE media SET status='rendering' WHERE id=?", (mid,))
        con.commit()
        clips: dict[int, float] = {}
        if narrate:
            pre = build_timeline(spec)
            for i in pre["held"]:
                d = _say_clip(spec["scenes"][i]["text"], out / f"n_{i}.aiff")
                if d:
                    clips[i] = d
        tl = build_timeline(spec, clips)
        spec = {**spec, "video": tl}
        con.execute("UPDATE media SET spec_json=? WHERE id=?", (json.dumps(spec), mid))
        con.commit()
        write_vtt(spec, tl, out / "captions.vtt")
        silent = out / "video_silent.mp4"
        url = app_url or os.environ.get("HORIZON_APP_URL", "http://127.0.0.1:8765")
        cmd = ["node", str(ROOT / "frontend" / "scripts" / "render.mjs"), "--id", mid, "--url", url, "--out", str(silent)]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        if p.returncode != 0:
            raise RuntimeError((p.stderr or p.stdout)[-1500:])
        final = out / "explainer.mp4"
        if clips:
            inputs, filters = [], []
            for n, (v, _t, i, _h) in enumerate(tl["keyframes"]):
                if i in clips:
                    inputs += ["-i", str(out / f"n_{i}.aiff")]
                    k = len(inputs) // 2
                    filters.append(f"[{k}:a]adelay={int(v * 1000)}|{int(v * 1000)}[a{k}]")
            labels = "".join(f"[a{k}]" for k in range(1, len(inputs) // 2 + 1))
            fc = ";".join(filters) + f";{labels}amix=inputs={len(inputs) // 2}:normalize=0[aout]"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(silent), *inputs, "-filter_complex", fc,
                            "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
                            "-t", str(tl["duration_s"]), str(final)], check=True, capture_output=True)
        else:
            shutil.copy(silent, final)
        dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(final)],
                             capture_output=True, text=True).stdout.strip()
        con.execute("UPDATE media SET status='done', path=?, captions_path=?, duration_s=? WHERE id=?",
                    (f"{mid}/explainer.mp4", f"{mid}/captions.vtt", float(dur or 0), mid))
        con.commit()
    except Exception as e:  # recorded on the media row; surfaced in the app
        con.execute("UPDATE media SET status='error', error=? WHERE id=?", (str(e)[-2000:], mid))
        con.commit()
