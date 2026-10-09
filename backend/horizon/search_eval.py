"""Labelled retrieval queries. Relevance is defined by explicit word-boundary regexes over the
opportunity name (and organisation), written before looking at system output. Substring LIKE
patterns over-matched (review #12: "ERA" in "accelerator"), so patterns are case-sensitive where
they name acronyms."""
from __future__ import annotations

import re

QUERIES = [
    ("ARC-AGI abstract reasoning competition", [r"\bARC Prize\b", r"\bARC-AGI"]),
    ("research fellowship India after bachelor's degree", [r"Microsoft Research India", r"Research Fellows?\b.*India|India.*Research Fellows?\b", r"\b[Pp]re-?[Dd]octoral\b", r"\bpredoc\b"]),
    ("ACL rolling review paper submission deadline", [r"\bARR\b", r"\bNAACL\b", r"Rolling Review", r"\bACL 2027\b"]),
    ("free GPU compute for academic researchers", [r"TPU Research Cloud", r"\b[Cc]ompute [Gg]rants?\b", r"\bfor Academics\b", r"Academic Research access", r"Compute Portal"]),
    ("Indian startup seed funding government grant", [r"Startup India Seed", r"\bSeed Fund\b", r"Seed Support"]),
    ("AI safety alignment research program mentorship", [r"\bMATS\b", r"\bSPAR\b", r"Anthropic Fellows", r"\bERA\b", r"[Aa]lignment", r"AI [Ss]afety"]),
    ("benchmark evaluation of language models grant", [r"\bSnorkel\b", r"\b[Bb]enchmark", r"\bEpoch AI\b", r"\b[Ee]valuation\b"]),
    ("PhD program in Europe machine learning", [r"ELLIS PhD", r"\bISTA\b.*PhD|PhD.*\bISTA\b", r"ETH AI Center.*[Dd]octoral", r"Max Planck.*(PhD|IMPRS)|IMPRS"]),
    ("summer research internship Switzerland", [r"\bEPFL\b", r"\bETH\b(?! ?[Gg]lobal)", r"Summer@EPFL"]),
    ("hackathon in Kolkata", [r"Kolkata"]),
    ("multilingual Indic language shared task", [r"\bSemEval\b", r"\bWMT\b", r"\bFIRE 2026\b", r"\bIndic\b"]),
    ("open source mentorship stipend", [r"\bGSoC\b", r"Summer of Code", r"\bLFX\b", r"Season of KDE", r"[Mm]entorship [Pp]rogram|Mentorship\b"]),
]


def resolve(con) -> list[dict]:
    rows = con.execute("SELECT id, name, org_name FROM opportunity").fetchall()
    out = []
    for q, pats in QUERIES:
        rx = [re.compile(p) for p in pats]
        ids = sorted({r[0] for r in rows if any(x.search(f"{r[1]} | {r[2] or ''}") for x in rx)})
        if ids:
            out.append({"query": q, "relevant": ids, "types": ["opportunity"]})
    return out
