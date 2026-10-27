# hdb

Horizon's independent evidence, database, retrieval, and model-access library. SQLite
holds authoritative records; optional vector adapters index derived chunks. BYOK and
local models are replaceable, role-specific adapters, not a dependency of manual use.

Current status: empty library foundation, with no runtime API. The [status](../docs/STATUS.md) records what exists; scope implementation through
an assigned task and public contracts. Read [the contract](../docs/HDB.md),
[model access](../docs/MODELS.md), [coding standard](../docs/CODE_STYLE.md), and
[scoped instructions](AGENTS.md).

Future private modules should follow actual responsibilities: workspace/storage,
sources/claims, import/chunking, retrieval/index adapters, providers, and archives.
Keep SDK types private and create seams when their implementations arrive.
