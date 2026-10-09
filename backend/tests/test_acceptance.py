"""End-to-end acceptance tests through the HTTP API (brief Part 28).

They run against a temporary copy of the real database, so they never touch your data.
Skipped if the database has not been built yet (`uv run horizon rebuild`).
"""
import importlib
import sqlite3

import pytest

from horizon.db import DEFAULT_DB

pytestmark = pytest.mark.skipif(not DEFAULT_DB.exists(), reason="run `uv run horizon rebuild` first")


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("db") / "horizon.sqlite3"
    # consistent snapshot including uncheckpointed WAL pages (a plain file copy would miss them)
    src, dst = sqlite3.connect(DEFAULT_DB), sqlite3.connect(tmp)
    src.backup(dst)
    src.close(), dst.close()
    mp = pytest.MonkeyPatch()
    mp.setenv("HORIZON_DB", str(tmp))
    from fastapi.testclient import TestClient
    import horizon.api as api
    importlib.reload(api)
    api._con = None
    yield TestClient(api.app)
    mp.undo()


def test_01_import_preserves_original_fields(client):
    ov = client.get("/api/overview").json()
    assert ov["counts"]["opportunities"] >= 501
    o = client.get("/api/opportunities/AIO-00001").json()["opportunity"]
    assert len(o["raw"]) == 163  # every original column kept


def test_02_04_search_and_semantic_neighbours(client):
    r = client.get("/api/search", params={"q": "ACL rolling review deadline", "mode": "hybrid"}).json()
    assert r["results"] and {"lexical", "dense"} & set(r["results"][0]["signals"])
    d = client.get("/api/opportunities/AIO-00049").json()
    assert d["similar"] and "not evidence" in d["similarity_note"]


def test_03_23_24_evidence_and_verified_vs_hypothesis(client):
    d = client.get("/api/opportunities/AIO-00042").json()
    grades = {c["evidence_grade"] for c in d["claims"]}
    assert grades & {"A", "B"}
    assert any(c["status"] == "superseded" for c in client.get("/api/research").json()["contradictions"])
    hyps = client.get("/api/hypotheses").json()
    assert hyps and all(h["classification"] in ("evidence_supported_potential_collaboration",
                                                  "speculative_created_opportunity_hypothesis") for h in hyps)


def test_05_06_relationships_and_dependencies(client):
    g = client.get("/api/graph").json()
    assert any(n["kind"] == "self" for n in g["nodes"]) and g["edges"]
    m = client.get("/api/model").json()
    assert m["unlocks"]["consumes"] and any(c["kind"] == "requires" for c in m["unlocks"]["consumes"])


def test_07_objectives_editable(client):
    p = client.put("/api/objectives", json={"name": "test values", "weights": {"peer_reviewed": 3}, "risk": {"measure": "mean"}}).json()
    assert any(x["id"] == p["id"] for x in client.get("/api/objectives").json()["profiles"])


def test_08_target_opportunity_enters_model(client):
    client.post("/api/shortlist/AIO-00222", json={})
    m = client.get("/api/model").json()
    assert any(a["id"] == "opp_AIO-00222" for a in m["actions"])


def test_09_15_simulation_assumptions_uncertainty_and_change(client):
    base = client.post("/api/simulate", json={"strategies": ["barbell", "research_first"], "n_worlds": 800, "seed": 5}).json()
    assert base["parameters_used"] and base["limitations"] and base["analysis"]["convergence"]
    assert base["analysis"]["dominance"]["ids"]
    alt = client.post("/api/simulate", json={"strategies": ["barbell", "research_first"], "n_worlds": 800, "seed": 5,
                                             "scenario": {"preset": "adverse"}}).json()
    assert alt["analysis"]["ranking"][0]["score"] != base["analysis"]["ranking"][0]["score"]
    re = client.post(f"/api/runs/{base['id']}/reanalyze", json={"objective": "research_impact"}).json()
    assert re["ranking"]


def test_16_theater_spec_matches_run(client):
    run = client.get("/api/runs").json()[0]["id"]
    spec = client.get("/api/theater/spec", params={"run": run, "strategy": "barbell", "world": 0}).json()
    assert spec["run_id"] == run and spec["scenes"][0]["kind"] == "intro" and spec["scenes"][-1]["kind"] == "outro"


def test_19_20_plan_outcome_calibration_and_undo(client):
    plan = client.post("/api/plan/generate", json={}).json()
    assert plan["items"]
    item = next(i for i in plan["items"] if i["strategy_action"])
    before = next(p for p in client.get("/api/parameters").json()["parameters"] if p["name"] == "p_reply_faculty")
    r = client.post("/api/outcomes", json={"action_id": item["id"], "strategy_action": "outreach_faculty",
                                           "successes": 1, "trials": 5, "weight": 0.5}).json()
    assert r["param_update"]["param"] == "p_reply_faculty"
    after = next(p for p in client.get("/api/parameters").json()["parameters"] if p["name"] == "p_reply_faculty")
    assert after["dist"] != before["dist"] and after["origin"] == "calibrated"
    client.post("/api/undo", json={})
    restored = next(p for p in client.get("/api/parameters").json()["parameters"] if p["name"] == "p_reply_faculty")
    assert restored["dist"] == before["dist"]


def test_21_22_persistence_and_export(client):
    csv = client.get("/api/export/opportunities.csv")
    assert csv.status_code == 200 and csv.text.count("\n") > 500
    run = client.get("/api/runs").json()[0]["id"]
    assert client.get(f"/api/export/run-{run}.json").status_code == 200


def test_25_limits_are_stated(client):
    run = client.get(f"/api/runs/{client.get('/api/runs').json()[0]['id']}").json()
    assert any("not predictions" in l for l in run["limitations"])
