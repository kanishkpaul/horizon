"""Hybrid retrieval: SQLite FTS5 (BM25) + dense embeddings, fused by reciprocal rank.

Corpus size is a few thousand documents, so dense search is an exact matrix product
in numpy (< 5 ms); an ANN index (HNSW/IVF) would add complexity without benefit.
Semantic similarity is a retrieval signal only. It is never used as evidence that
two things are the same or that the person is eligible.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import threading

import numpy as np

EMBED_MODEL = "BAAI/bge-small-en-v1.5"
RRF_K = 60

_model = None
_model_lock = threading.Lock()
_cache: dict = {}


def _embedder():
    global _model
    with _model_lock:
        if _model is None:
            from fastembed import TextEmbedding
            _model = TextEmbedding(EMBED_MODEL)
    return _model


def documents(con: sqlite3.Connection) -> list[tuple[str, str, str, str]]:
    """(doc_type, doc_id, title, body) for everything searchable."""
    docs = []
    for r in con.execute("SELECT id, name, org_name, type_raw, type_canonical, description, detail, why_it_matters, "
                         "eligibility_text, country, location_mode, money_text, value_tags, notes FROM opportunity"):
        body = " | ".join(str(x) for x in (r["org_name"], r["type_raw"], r["type_canonical"], r["description"],
                                            r["detail"], r["why_it_matters"], r["eligibility_text"], r["country"],
                                            r["location_mode"], r["money_text"], r["value_tags"], r["notes"]) if x)
        docs.append(("opportunity", r["id"], r["name"], body))
    for r in con.execute("SELECT id, name, location, category, when_text, topic, venue, fee FROM event"):
        body = " | ".join(str(x) for x in (r["location"], r["category"], r["when_text"], r["topic"], r["venue"],
                                            r["fee"]) if x)
        docs.append(("event", r["id"], r["name"] or "", body))
    for r in con.execute("SELECT id, entity, contact, ask, why_fit, pitch, opening_evidence, caveats FROM outreach_target"):
        body = " | ".join(str(x) for x in (r["contact"], r["ask"], r["why_fit"], r["pitch"], r["opening_evidence"],
                                            r["caveats"]) if x)
        docs.append(("outreach", r["id"], r["entity"] or "", body))
    for r in con.execute("SELECT id, target_org, target_role, problem, why_me, demo_needed, collab_form FROM hypothesis"):
        body = " | ".join(str(x) for x in (r["target_role"], r["problem"], r["why_me"], r["demo_needed"],
                                            r["collab_form"]) if x)
        docs.append(("hypothesis", r["id"], r["target_org"] or "", body))
    for r in con.execute("SELECT id, name, parent, countries, url FROM organization"):
        docs.append(("organization", r["id"], r["name"], " | ".join(str(x) for x in (r["parent"], r["countries"]) if x)))
    return docs


def build_index(con: sqlite3.Connection, embed: bool = True) -> dict:
    docs = documents(con)
    con.execute("DELETE FROM doc_fts")
    con.executemany("INSERT INTO doc_fts(doc_type, doc_id, title, body) VALUES(?,?,?,?)", docs)
    n_emb = 0
    if embed:
        have = {(r[0], r[1]): r[2] for r in con.execute(
            "SELECT doc_type, doc_id, text_hash FROM doc_embedding WHERE model=?", (EMBED_MODEL,))}
        todo = []
        for t, i, title, body in docs:
            text = f"{title}. {body}"[:2000]
            h = hashlib.sha1(text.encode()).hexdigest()
            if have.get((t, i)) != h:
                todo.append((t, i, text, h))
        if todo:
            vecs = list(_embedder().embed([x[2] for x in todo], batch_size=64))
            con.executemany(
                "INSERT OR REPLACE INTO doc_embedding(doc_type, doc_id, model, dim, vec, text_hash) VALUES(?,?,?,?,?,?)",
                [(t, i, EMBED_MODEL, len(v), np.asarray(v, dtype=np.float32).tobytes(), h)
                 for (t, i, _, h), v in zip(todo, vecs)])
            n_emb = len(todo)
        live = {(t, i) for t, i, _, _ in docs}
        stale = [k for k in have if k not in live]
        con.executemany("DELETE FROM doc_embedding WHERE doc_type=? AND doc_id=? AND model=?",
                        [(t, i, EMBED_MODEL) for t, i in stale])
    con.commit()
    _cache.clear()
    return {"documents": len(docs), "embedded": n_emb}


def _matrix(con):
    if "M" not in _cache:
        rows = con.execute("SELECT doc_type, doc_id, vec FROM doc_embedding WHERE model=?", (EMBED_MODEL,)).fetchall()
        if not rows:
            _cache["M"] = (np.zeros((0, 384), np.float32), [])
        else:
            M = np.stack([np.frombuffer(r[2], dtype=np.float32) for r in rows])
            M = M / np.linalg.norm(M, axis=1, keepdims=True)
            _cache["M"] = (M, [(r[0], r[1]) for r in rows])
    return _cache["M"]


def fts_query(q: str) -> str:
    terms = [t for t in re.findall(r"[\w\-]+", q.lower()) if len(t) > 1]
    stop = {"the", "and", "for", "with", "that", "this", "from", "into", "about", "what", "which", "are", "can", "my",
            "me", "to", "of", "in", "on", "a", "an", "is", "or", "at", "by", "be", "i"}
    terms = [t.replace("-", " ") for t in terms if t not in stop]
    return " OR ".join(f'"{t}"' for t in terms) if terms else ""


def lexical(con, q: str, k: int = 50, types: list[str] | None = None) -> list[tuple[str, str, float]]:
    fq = fts_query(q)
    if not fq:
        return []
    sql = "SELECT doc_type, doc_id, bm25(doc_fts, 0, 0, 3.0, 1.0) AS s FROM doc_fts WHERE doc_fts MATCH ?"
    args: list = [fq]
    if types:
        sql += " AND doc_type IN (%s)" % ",".join("?" * len(types))
        args += types
    sql += " ORDER BY s LIMIT ?"
    args.append(k)
    return [(r[0], r[1], -float(r[2])) for r in con.execute(sql, args)]


def dense(con, q: str, k: int = 50, types: list[str] | None = None) -> list[tuple[str, str, float]]:
    M, keys = _matrix(con)
    if len(keys) == 0:
        return []
    qv = np.asarray(list(_embedder().query_embed([q]))[0], dtype=np.float32)
    qv /= np.linalg.norm(qv)
    s = M @ qv
    order = np.argsort(-s)
    out = []
    for i in order:
        if types and keys[i][0] not in types:
            continue
        out.append((keys[i][0], keys[i][1], float(s[i])))
        if len(out) >= k:
            break
    return out


def similar(con, doc_type: str, doc_id: str, k: int = 10, types: list[str] | None = None):
    M, keys = _matrix(con)
    try:
        i = keys.index((doc_type, doc_id))
    except ValueError:
        return []
    s = M @ M[i]
    out = []
    for j in np.argsort(-s):
        if j == i or (types and keys[j][0] not in types):
            continue
        out.append({"doc_type": keys[j][0], "doc_id": keys[j][1], "similarity": float(s[j])})
        if len(out) >= k:
            break
    return out


def hybrid(con, q: str, k: int = 20, types: list[str] | None = None, mode: str = "hybrid") -> list[dict]:
    lists = []
    if mode in ("hybrid", "lexical"):
        lists.append(("lexical", lexical(con, q, 60, types)))
    if mode in ("hybrid", "dense"):
        lists.append(("dense", dense(con, q, 60, types)))
    fused: dict[tuple[str, str], dict] = {}
    for name, lst in lists:
        for rank, (t, i, s) in enumerate(lst):
            d = fused.setdefault((t, i), {"doc_type": t, "doc_id": i, "score": 0.0, "signals": {}})
            d["score"] += 1.0 / (RRF_K + rank + 1)
            d["signals"][name] = {"rank": rank + 1, "raw": round(s, 4)}
    out = sorted(fused.values(), key=lambda d: -d["score"])[:k]
    return out


def evaluate_retrieval(con, qrels: list[dict], k: int = 10) -> dict:
    """nDCG@k and recall@k for lexical, dense and hybrid on labelled test queries."""
    res = {}
    for mode in ("lexical", "dense", "hybrid"):
        ndcgs, recalls = [], []
        for q in qrels:
            rel = set(q["relevant"])
            got = [d["doc_id"] for d in hybrid(con, q["query"], k=k, types=q.get("types"), mode=mode)]
            dcg = sum(1 / np.log2(i + 2) for i, d in enumerate(got) if d in rel)
            idcg = sum(1 / np.log2(i + 2) for i in range(min(len(rel), k)))
            ndcgs.append(dcg / idcg if idcg else 0.0)
            recalls.append(len(rel & set(got)) / len(rel) if rel else 0.0)
        rng = np.random.default_rng(0)
        boots = [float(np.mean(rng.choice(ndcgs, len(ndcgs)))) for _ in range(2000)]
        res[mode] = {"ndcg@%d" % k: float(np.mean(ndcgs)), "recall@%d" % k: float(np.mean(recalls)),
                     "ndcg_ci95": [float(np.quantile(boots, 0.025)), float(np.quantile(boots, 0.975))],
                     "per_query": [{"query": q["query"], "ndcg": n, "recall": r}
                                   for q, n, r in zip(qrels, ndcgs, recalls)]}
    return res
