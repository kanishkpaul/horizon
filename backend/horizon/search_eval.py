"""Labelled retrieval queries. Relevance is defined by explicit name/organization patterns
(resolved against the database at evaluation time), written before looking at system output."""
from __future__ import annotations

QUERIES = [
    ("ARC-AGI abstract reasoning competition", ["%ARC Prize%", "%ARC-AGI%"]),
    ("research fellowship India after bachelor's degree", ["%Microsoft Research India%", "%Research Fellow%India%", "%pre-doc%", "%Pre-Doctoral%", "%predoc%"]),
    ("ACL rolling review paper submission deadline", ["%ARR%", "%NAACL%", "%Rolling Review%", "%ACL 2027%"]),
    ("free GPU compute for academic researchers", ["%TPU Research Cloud%", "%Compute Grant%", "%for Academics%", "%Research access%", "%Compute Portal%", "%compute%credit%"]),
    ("Indian startup seed funding government grant", ["%Startup India Seed%", "%Seed Fund%", "%Seed Support%"]),
    ("AI safety alignment research program mentorship", ["%MATS%", "%SPAR%", "%Anthropic Fellows%", "%ERA%", "%alignment%"]),
    ("benchmark evaluation of language models grant", ["%Snorkel%", "%Benchmark%", "%Epoch AI%", "%Evaluation%"]),
    ("PhD program in Europe machine learning", ["%ELLIS PhD%", "%ISTA%", "%ETH%doctoral%", "%PhD%"]),
    ("summer research internship Switzerland", ["%EPFL%", "%ETH%", "%Summer@EPFL%"]),
    ("hackathon in Kolkata", ["%Kolkata%"]),
    ("multilingual Indic language shared task", ["%SemEval%", "%WMT%", "%FIRE 2026%", "%Indic%"]),
    ("open source mentorship stipend", ["%GSoC%", "%Summer of Code%", "%LFX%", "%Season of KDE%", "%Mentorship%"]),
]


def resolve(con) -> list[dict]:
    out = []
    for q, pats in QUERIES:
        ids = set()
        for p in pats:
            ids |= {r[0] for r in con.execute(
                "SELECT id FROM opportunity WHERE name LIKE ? OR org_name LIKE ?", (p, p))}
        if ids:
            out.append({"query": q, "relevant": sorted(ids), "types": ["opportunity"]})
    return out

