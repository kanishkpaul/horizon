# Horizon contributor instructions

Read and follow [AGENTS.md](AGENTS.md) before any change. It is the canonical
instruction file for all coding assistants and contributors. Also read
[docs/CODE_STYLE.md](docs/CODE_STYLE.md) and the scoped `AGENTS.md` for `hsim` or
`hdb` before editing that component.

Never add coding-agent co-author trailers, generated-by signatures, or coding-agent
attribution to commits, pull requests, documentation, or source. Use the configured
contributor identity. Preserve third-party license notices.

New development belongs on `main`. `old` is the preserved legacy implementation.
Do not restore the old backend, personal models, or private data into the new tree.
Read `docs/THESIS.md` and `docs/STATUS.md`. The current public gate is in
`docs/BUILD_PLAN.md`; detailed planning stays in ignored `.local/BUILD_PLAN.md`.
Use the local plan when available for an assigned task, never publish its backlog,
and continue from public acceptance conditions when it is absent. Report actual checks
and remaining limitations without claiming planned abilities are implemented.
