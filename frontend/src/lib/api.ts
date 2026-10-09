import { useCallback, useEffect, useRef, useState } from "react";

export async function api<T = any>(path: string, opts: { method?: string; body?: any } = {}): Promise<T> {
  const res = await fetch(path, {
    method: opts.method ?? (opts.body ? "POST" : "GET"),
    headers: opts.body ? { "Content-Type": "application/json" } : undefined,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  if (!res.ok) {
    let msg = `${res.status} ${res.statusText}`;
    try {
      const j = await res.json();
      if (j?.detail) msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
    } catch {}
    throw new Error(msg);
  }
  const ct = res.headers.get("content-type") || "";
  return (ct.includes("json") ? res.json() : res.text()) as Promise<T>;
}

export function useApi<T = any>(path: string | null, deps: any[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const seq = useRef(0);
  const load = useCallback(() => {
    if (!path) return;
    const n = ++seq.current;
    setLoading(true);
    api<T>(path)
      .then((d) => { if (n === seq.current) { setData(d); setError(null); } })
      .catch((e) => { if (n === seq.current) setError(String(e.message || e)); })
      .finally(() => { if (n === seq.current) setLoading(false); });
  }, [path]);
  useEffect(load, [load, ...deps]);
  return { data, error, loading, reload: load, setData };
}

// ------------------------------------------------------------------ formatting
export const pct = (x: number | null | undefined, d = 0) => (x == null || isNaN(x) ? "–" : `${(x * 100).toFixed(d)}%`);
export const fx = (x: number | null | undefined, d = 2) => (x == null || isNaN(x) ? "–" : x.toFixed(d));
export const fdate = (iso?: string | null) => {
  if (!iso) return "–";
  const d = new Date(iso);
  if (isNaN(+d)) return iso;
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric", timeZone: "Asia/Kolkata" });
};
export const fdateShort = (iso?: string | null) => {
  if (!iso) return "–";
  const d = new Date(iso);
  if (isNaN(+d)) return iso;
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short", timeZone: "Asia/Kolkata" });
};
export function daysUntil(iso?: string | null): number | null {
  if (!iso) return null;
  const t = new Date(iso).getTime();
  if (isNaN(t)) return null;
  return (t - Date.now()) / 86400000;
}
export function relDays(iso?: string | null) {
  const d = daysUntil(iso);
  if (d == null) return "";
  if (d < 0) return `${Math.ceil(-d)}d ago`;
  if (d < 1) return `${Math.round(d * 24)}h left`;
  return `${Math.floor(d)}d left`;
}

export const ELIG: Record<string, { label: string; tone: string; icon: string }> = {
  eligible_likely: { label: "Likely eligible", tone: "good", icon: "✓" },
  needs_check: { label: "Needs a check", tone: "warn", icon: "?" },
  travel_or_relocation: { label: "Needs travel/relocation", tone: "warn", icon: "✈" },
  eligible_later: { label: "Eligible later", tone: "neutral", icon: "◷" },
  closed_watch: { label: "Closed · watch", tone: "neutral", icon: "↻" },
  deadline_passed: { label: "Deadline passed", tone: "neutral", icon: "–" },
  ineligible: { label: "Ineligible", tone: "bad", icon: "✕" },
};

export const ACCESS: Record<string, string> = {
  verified_open: "Verified open",
  partially_verified: "Partially verified",
  historically_open: "Historically open",
  unverified_lead: "Unverified lead",
  evidence_supported_collaboration: "Evidence-supported collaboration",
  speculative_hypothesis: "Speculative hypothesis",
};

export const ORIGIN_TONE: Record<string, string> = {
  published_empirical: "good", official_statistic: "good", organizer_published: "good", observed_base_rate: "good",
  calibrated: "good", historical_user: "neutral", expert_judgment: "neutral", scenario_assumption: "warn",
  illustrative_placeholder: "bad", unknown: "bad",
};
export const ORIGIN_LABEL: Record<string, string> = {
  published_empirical: "published", official_statistic: "official stat", organizer_published: "organizer",
  observed_base_rate: "base rate", calibrated: "calibrated", historical_user: "your history",
  expert_judgment: "judgment", scenario_assumption: "scenario", illustrative_placeholder: "placeholder", unknown: "unknown",
};

export const METRIC_LABEL: Record<string, string> = {
  peer_reviewed: "Peer-reviewed papers", workshop: "Workshop papers", public_outputs: "New public outputs",
  best_comp_lpa: "Best secured pay (₹ lakh/yr)", position_by_grad: "Position by graduation",
  position_by_horizon: "Position by Oct 2027", optionality: "Open pathways", autonomy: "Research autonomy (0–3)",
  founder_stage: "Founder stage (0–3)", ties: "New professional ties", adoption: "External uptake",
  cash_lpa: "Prizes & grants (₹ lakh)", crunch_weeks: "Deadline-crunch weeks", hours_used: "Hours used",
};
export const PROB_METRICS = new Set(["position_by_grad", "position_by_horizon"]);
export const fmtMetric = (k: string, v: number) => (PROB_METRICS.has(k) ? pct(v) : k === "hours_used" ? v.toFixed(0) : fx(v, k.includes("lpa") ? 1 : 2));

export const SERIES = ["--s1", "--s2", "--s3", "--s4", "--s5", "--s6", "--s7", "--s8"].map((v) => `var(${v})`);
/** Color follows the entity, never its rank: strategies get a stable slot from a fixed list. */
const STRAT_ORDER = ["research_first", "research_engineer", "founder", "barbell", "artifact_led", "creation_portfolio",
  "conventional", "defer_depth", "max_parallel"];
export function stratColor(id: string, all: string[]): string {
  const i = STRAT_ORDER.indexOf(id);
  // A ninth series is never a generated hue: everything past slot 8 (incl. discovered/user strategies) is neutral ink,
  // and charts give those a dashed stroke plus a direct label so identity never rests on colour alone.
  return i >= 0 && i < 8 ? SERIES[i] : "var(--ink-2)";
}
