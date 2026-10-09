"""SQLite storage with numbered migrations.

One local file holds structured records, temporal claims, full-text index,
embeddings, simulation runs and the execution log. See docs/DECISIONS.md D-003
for why a single SQLite file was chosen over a graph or vector database.
"""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT / "data" / "horizon.sqlite3"


def db_path() -> Path:
    return Path(os.environ.get("HORIZON_DB", DEFAULT_DB))


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


MIGRATIONS: list[str] = [
    # 1: core knowledge model
    """
    CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);

    CREATE TABLE source(
      id TEXT PRIMARY KEY,
      kind TEXT NOT NULL,            -- url | local_file | workbook | user_statement | agent_research
      url TEXT, local_ref TEXT, title TEXT, publisher TEXT,
      source_date TEXT,              -- date the source itself carries
      accessed_at TEXT,              -- when it was read
      quality TEXT,
      independence_group TEXT,       -- sources sharing a group are not independent evidence
      recorded_at TEXT NOT NULL
    );

    CREATE TABLE organization(
      id TEXT PRIMARY KEY, name TEXT NOT NULL, parent TEXT, url TEXT, kind TEXT,
      countries TEXT, opp_count INTEGER, notes TEXT, origin TEXT, raw_json TEXT, recorded_at TEXT
    );
    CREATE UNIQUE INDEX org_name ON organization(name);

    CREATE TABLE opportunity(
      id TEXT PRIMARY KEY, name TEXT NOT NULL, org_id TEXT REFERENCES organization(id), org_name TEXT,
      type_raw TEXT, type_canonical TEXT, mechanism TEXT,
      access_class TEXT NOT NULL,
      status_raw TEXT, applications_open_raw TEXT,
      description TEXT, detail TEXT, why_it_matters TEXT,
      official_url TEXT, application_url TEXT,
      deadline_utc TEXT, deadline_raw TEXT, deadline_tz_raw TEXT, deadline_quality TEXT,
      opens_at TEXT, starts_at TEXT, ends_at TEXT,
      rolling INTEGER, recurrence TEXT, next_cycle TEXT,
      country TEXT, region TEXT, remote TEXT, location_mode TEXT,
      intl_allowed TEXT, undergrad_eligible TEXT, student_required TEXT,
      eligibility_text TEXT, money_text TEXT, value_tags TEXT,
      rel_researcher TEXT, rel_developer TEXT, rel_founder TEXT,
      sheet_eligibility TEXT, sheet_eligibility_reason TEXT,
      confidence TEXT, verification_result TEXT, verification_scope TEXT, last_verified TEXT,
      info_gaps TEXT, notes TEXT, action_required TEXT, next_action_date TEXT,
      origin TEXT NOT NULL, views TEXT, raw_json TEXT,
      recorded_at TEXT NOT NULL, updated_at TEXT
    );

    CREATE TABLE claim(
      id TEXT PRIMARY KEY,
      subject_type TEXT NOT NULL, subject_id TEXT NOT NULL,
      predicate TEXT NOT NULL, value TEXT, value_norm TEXT,
      source_id TEXT REFERENCES source(id),
      source_date TEXT, accessed_at TEXT,
      valid_from TEXT, valid_to TEXT,
      verification_method TEXT, evidence_grade TEXT,
      status TEXT NOT NULL DEFAULT 'active',  -- active | superseded | contradicted | retracted
      superseded_by TEXT, contradicts TEXT,
      recorded_at TEXT NOT NULL, recorded_by TEXT, notes TEXT
    );
    CREATE INDEX claim_subject ON claim(subject_type, subject_id, predicate);

    CREATE TABLE person(
      id TEXT PRIMARY KEY, name TEXT, role TEXT, org_id TEXT, public_email TEXT,
      contact_type TEXT, relationship TEXT, source_ref TEXT, notes TEXT, origin TEXT, recorded_at TEXT
    );

    CREATE TABLE event(
      id TEXT PRIMARY KEY, name TEXT, location TEXT, category TEXT, when_text TEXT, starts_on TEXT,
      time_text TEXT, venue TEXT, topic TEXT, fee TEXT, availability TEXT, source_url TEXT,
      evidence TEXT, origin TEXT, raw_json TEXT, recorded_at TEXT
    );

    CREATE TABLE edge(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      src_type TEXT, src_id TEXT, rel TEXT, dst_type TEXT, dst_id TEXT,
      weight REAL, inferred INTEGER NOT NULL DEFAULT 0, confidence TEXT,
      claim_id TEXT, notes TEXT, recorded_at TEXT
    );
    CREATE INDEX edge_src ON edge(src_type, src_id);
    CREATE INDEX edge_dst ON edge(dst_type, dst_id);

    CREATE TABLE hypothesis(
      id TEXT PRIMARY KEY, target_org TEXT, target_role TEXT, public_lead TEXT, problem TEXT,
      evidence_json TEXT, why_me TEXT, demo_needed TEXT, demo_effort_low REAL, demo_effort_high REAL,
      collab_form TEXT, access_mechanism TEXT, access_evidence TEXT, invalidators_json TEXT,
      next_step TEXT, classification TEXT, upside TEXT, risks TEXT, status TEXT DEFAULT 'open',
      origin TEXT, recorded_at TEXT
    );

    CREATE TABLE outreach_target(
      id TEXT PRIMARY KEY, priority INTEGER, wave TEXT, entity TEXT, contact TEXT, public_email TEXT,
      contact_type TEXT, ask TEXT, why_fit TEXT, pitch TEXT, opening_evidence TEXT, caveats TEXT,
      source1 TEXT, source2 TEXT, research_date TEXT, status TEXT, last_contacted TEXT,
      follow_up TEXT, org_id TEXT, person_id TEXT, origin TEXT, raw_json TEXT
    );

    CREATE TABLE search_gap(id TEXT PRIMARY KEY, workstream TEXT, gap TEXT, origin TEXT);

    CREATE TABLE profile_item(
      id TEXT PRIMARY KEY, dimension TEXT NOT NULL, key TEXT NOT NULL, label TEXT, value TEXT,
      evidence_status TEXT,   -- measured | reported | user-supplied | planned | unknown | assumed
      source_ref TEXT, notes TEXT, editable INTEGER DEFAULT 1, updated_at TEXT
    );

    CREATE TABLE parameter(
      id TEXT PRIMARY KEY, name TEXT UNIQUE NOT NULL, description TEXT, unit TEXT,
      dist TEXT NOT NULL, params_json TEXT NOT NULL,
      origin TEXT NOT NULL,  -- observed_base_rate | published_empirical | historical_user | calibrated | expert_judgment | scenario_assumption | illustrative_placeholder | unknown
      sources_json TEXT, evidence_grade TEXT, transferability TEXT, notes TEXT, updated_at TEXT
    );
    CREATE TABLE parameter_history(
      id INTEGER PRIMARY KEY AUTOINCREMENT, param_id TEXT, changed_at TEXT, before_json TEXT,
      after_json TEXT, reason TEXT
    );

    CREATE TABLE objective_profile(
      id TEXT PRIMARY KEY, name TEXT, description TEXT, config_json TEXT, builtin INTEGER, updated_at TEXT
    );

    CREATE TABLE strategy(
      id TEXT PRIMARY KEY, name TEXT, description TEXT, spec_json TEXT NOT NULL,
      origin TEXT, created_at TEXT, updated_at TEXT
    );

    CREATE TABLE sim_run(
      id TEXT PRIMARY KEY, created_at TEXT, label TEXT, model_version TEXT, dataset_version TEXT,
      seed INTEGER, scenario_json TEXT, objective_id TEXT, strategies_json TEXT, params_json TEXT,
      algorithm TEXT, n_worlds INTEGER, horizon_weeks INTEGER, diagnostics_json TEXT,
      results_json TEXT, warnings_json TEXT, limitations_json TEXT, duration_ms INTEGER
    );

    CREATE TABLE action_item(
      id TEXT PRIMARY KEY, created_at TEXT, title TEXT, kind TEXT, reason TEXT, objective TEXT,
      evidence TEXT, prerequisites TEXT, effort_hours REAL, attention TEXT, automation TEXT,
      dependencies TEXT, outcomes TEXT, risk TEXT, success_criteria TEXT, failure_criteria TEXT,
      due TEXT, review_on TEXT, alternatives TEXT, unlocks TEXT, horizon TEXT, status TEXT DEFAULT 'todo',
      opportunity_id TEXT, strategy_action TEXT, sim_run_id TEXT, origin TEXT, updated_at TEXT
    );

    CREATE TABLE outcome(
      id TEXT PRIMARY KEY, recorded_at TEXT, action_id TEXT, event_type TEXT, result TEXT,
      param_name TEXT, successes INTEGER, trials INTEGER, notes TEXT
    );

    CREATE TABLE forecast(
      id TEXT PRIMARY KEY, created_at TEXT, question TEXT, prob REAL, resolve_by TEXT,
      resolved_at TEXT, outcome INTEGER, sim_run_id TEXT, notes TEXT
    );

    CREATE TABLE media(
      id TEXT PRIMARY KEY, created_at TEXT, sim_run_id TEXT, strategy_id TEXT, kind TEXT,
      spec_json TEXT, path TEXT, captions_path TEXT, format TEXT, duration_s REAL,
      renderer TEXT, status TEXT, error TEXT
    );

    CREATE TABLE research_log(
      id TEXT PRIMARY KEY, created_at TEXT, workstream TEXT, question TEXT, finding TEXT,
      sources_json TEXT, status TEXT
    );

    CREATE TABLE revision(
      id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, table_name TEXT, row_id TEXT,
      before_json TEXT, after_json TEXT, actor TEXT, undone INTEGER DEFAULT 0
    );

    CREATE TABLE doc_embedding(
      doc_type TEXT, doc_id TEXT, model TEXT, dim INTEGER, vec BLOB, text_hash TEXT,
      PRIMARY KEY(doc_type, doc_id, model)
    );

    CREATE VIRTUAL TABLE doc_fts USING fts5(
      doc_type UNINDEXED, doc_id UNINDEXED, title, body, tokenize = 'porter unicode61'
    );
    """,
]


def connect(path: Path | None = None) -> sqlite3.Connection:
    p = Path(path) if path else db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(p, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    migrate(con)
    return con


def migrate(con: sqlite3.Connection) -> None:
    con.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY, applied_at TEXT)"
    )
    done = {r[0] for r in con.execute("SELECT version FROM schema_migrations")}
    for i, sql in enumerate(MIGRATIONS, start=1):
        if i in done:
            continue
        con.executescript(sql)
        con.execute("INSERT INTO schema_migrations VALUES(?, ?)", (i, now_iso()))
        con.commit()


@contextmanager
def tx(con: sqlite3.Connection):
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise


def rows(con: sqlite3.Connection, sql: str, args: tuple | list = ()) -> list[dict]:
    return [dict(r) for r in con.execute(sql, args)]


def one(con: sqlite3.Connection, sql: str, args: tuple | list = ()) -> dict | None:
    r = con.execute(sql, args).fetchone()
    return dict(r) if r else None


def set_meta(con: sqlite3.Connection, key: str, value) -> None:
    con.execute(
        "INSERT INTO meta VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, json.dumps(value)),
    )


def get_meta(con: sqlite3.Connection, key: str, default=None):
    r = con.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return json.loads(r[0]) if r else default


def record_revision(con, table: str, row_id: str, before: dict | None, after: dict | None, actor="user"):
    con.execute(
        "INSERT INTO revision(created_at, table_name, row_id, before_json, after_json, actor) VALUES(?,?,?,?,?,?)",
        (now_iso(), table, row_id, json.dumps(before, default=str), json.dumps(after, default=str), actor),
    )
