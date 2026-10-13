# hdb instructions

Follow root `AGENTS.md` and `docs/CODE_STYLE.md`. Read `docs/HDB.md` and `MODELS.md`
before changes. This library does not depend on hsim or a UI framework.

- Preserve original evidence and revision history. Model extraction creates proposed
  claims; it cannot silently accept facts or change simulation inputs.
- Validate writes before a transaction; related mutations commit atomically.
- Keep SQLite authoritative and vector indexes regenerable. Account for stale
  generations, deletes, permission filtering, and interrupted indexing.
- Keys are credential references, not database values. Keep context and keys out of logs.
- Support BYOK, local, and no-model modes. Never add automatic local-to-cloud fallback.
- Importers and providers need bounded input/output, explicit errors, and cancellation.
- Test idempotence, rollback, backup/recovery, source spans, and denied/failed adapters.
- Comments explain provenance, transaction boundaries, or non-obvious recovery choices.
- Never add coding-agent attribution or co-author trailers.
