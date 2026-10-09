"""Command line: `uv run horizon <command>`."""
from __future__ import annotations

import argparse
import json
import sys

from . import research_ingest, search
from . import service as S
from .db import DEFAULT_DB, connect
from .ingest import import_all


def main(argv=None):
    ap = argparse.ArgumentParser(prog="horizon")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("rebuild", help="re-import workbooks, research outputs, reindex and reassess")
    sub.add_parser("ingest-research", help="ingest research worker outputs")
    sub.add_parser("reseed", help="reload parameters, objectives and strategies from data/seed (keeps profile)")
    sv = sub.add_parser("serve", help="run the API and app")
    sv.add_argument("--port", type=int, default=8765)
    sv.add_argument("--host", default="127.0.0.1")
    sm = sub.add_parser("simulate", help="run a simulation and print the ranking")
    sm.add_argument("--objective", default="balanced")
    sm.add_argument("--worlds", type=int, default=2000)
    sm.add_argument("--scenario", default="central")
    sub.add_parser("eval-search", help="evaluate retrieval on labelled queries")
    a = ap.parse_args(argv)

    if a.cmd == "serve":
        import uvicorn
        uvicorn.run("horizon.api:app", host=a.host, port=a.port, log_level="info")
        return
    con = connect()
    if a.cmd == "rebuild":
        out = {"import": import_all(con)}
        S.bootstrap(con, embed=False)
        out["research"] = research_ingest.ingest_all(con)
        out["index"] = search.build_index(con)
        out["assessed"] = S.assess_all(con)
        print(json.dumps(out, indent=1, default=str))
    elif a.cmd == "ingest-research":
        print(json.dumps(research_ingest.ingest_all(con), indent=1))
        search.build_index(con)
        S.assess_all(con)
    elif a.cmd == "reseed":
        with con:
            con.execute("DELETE FROM parameter")
            con.execute("DELETE FROM objective_profile WHERE builtin=1")
            con.execute("DELETE FROM strategy WHERE origin='preset'")
        S.seed_parameters(con)
        S.seed_objectives(con)
        S.seed_strategies(con)
        con.commit()
        print("reseeded parameters, objectives and preset strategies")
    elif a.cmd == "simulate":
        r = S.run_simulation(con, scenario={"preset": a.scenario}, objective_id=a.objective, n_worlds=a.worlds)
        for row in r["analysis"]["ranking"]:
            print(f"{row['rank']:2d}. {row['strategy']:22s} score={row['score']:.3f} ± {row['se']:.3f}"
                  f" feasible={row['feasible']}")
        print("warnings:", *r["warnings"], sep="\n  ")
        print("run id:", r["id"])
    elif a.cmd == "eval-search":
        from .search_eval import resolve
        qrels = resolve(con)
        res = search.evaluate_retrieval(con, qrels)
        for m, v in res.items():
            print(m, {k: (round(x, 3) if isinstance(x, float) else [round(y, 3) for y in x]) for k, x in v.items() if k != "per_query"})
        for i, q in enumerate(qrels):
            print(f"  {q['query'][:48]:48s} rel={len(q['relevant']):3d} " +
                  " ".join(f"{m}={res[m]['per_query'][i]['ndcg']:.2f}" for m in res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
