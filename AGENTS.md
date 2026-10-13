# Legacy branch instructions

This branch preserves the old implementation. Read `README.md`, `PROJECT.md`, and
`CLAUDE.md` before changing it. New Horizon development belongs on `main`.

- Do not change legacy production code merely to match v2 architecture.
- Keep originals read-only and back up SQLite through its backup API, not a raw
  file copy while WAL is active.
- Treat dated research and model probabilities as conditional evidence.
- Use the configured human Git identity. Never add coding-agent co-author
  trailers, generated-by signatures, or coding-agent attribution to commits,
  pull requests, documentation, or source. Keep third-party license notices.
- Keep commits focused and comments limited to contracts, rationale, invariants,
  or non-obvious behavior. Do not narrate ordinary code or add decorative banners.
- Read applicable nested instructions before changing legacy subdirectories.
