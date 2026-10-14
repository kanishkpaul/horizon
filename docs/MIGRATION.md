# Legacy preservation and migration

## Branch split

The source checkout was on `integrate/lifesim` at
`25c9f9a4dffdb2a7f8b32ebda0c4653879169f62`. Its local `main` pointed to
`f184729`; the later commit includes the complete lifesim snapshot. `old` starts
from the later commit and adds the root README/instructions and previously untracked
audit files. Its preservation commit is `d59aeaa`.

The new `main` descends from this preserved history and replaces its working tree
with the v2 foundation. No force-push or history rewrite is required. The legacy
implementation is reachable both through `old` and the history of `main`.

Legacy production source blobs must match the source snapshot. README and instruction
updates are intentional; the old code is not silently repaired during preservation.

## Private assets

Before the split, a consistent SQLite backup and copies of original inputs, simulation
archives, rendered media, and untracked audit files were saved outside the repository
and hashed. SQLite integrity returned `ok`. This backup is private and is not part
of a public distribution. Development environments and regenerable build artifacts
are not included in that data backup.

A branch push does not preserve ignored files. Restore private workspaces separately.
Do not copy a live WAL database as an ordinary file. Use SQLite's backup API and verify
integrity, references, and archive checksums after restore.

## Reuse policy

| Legacy material | Treatment |
|---|---|
| Evidence/claim concepts and useful formats | Review and adapt to versioned hdb contracts |
| Importers | Port only required, tested preservation behavior |
| Simulator and analysis | Use as reference; port reviewed algorithms after fixing semantics |
| Known failing examples | Translate into synthetic regression tests |
| UI components | Reuse selectively against new application contracts |
| Personal profiles, outreach, originals | Private user import only; never default fixtures |
| lifesim dynamics/reference percentiles | Experimental assumptions, not empirical truth |
| Old run summaries | Historical, summary-only when arrays/snapshots are missing |

Do not merge the legacy tree back wholesale. Define the receiving contract and its
acceptance test before porting a feature. A translation that reproduces old outputs
can still reproduce an old defect.

## Data migration

Build a read-only legacy importer only after hdb has versioned storage. Preserve
source IDs, raw originals, provenance, dates, revisions, and missing-data flags.
Report unsupported or ambiguous fields rather than drop them. Produce a migration
manifest and count/hash/reference checks. Keep the old database unchanged and verify
restoration before adopting the new workspace.

Do not claim old runs are replayable without their complete inputs and arrays.
Changing embedding model, dimensions, or chunking requires rebuilding derived indexes.

## Repository visibility

The owner made the repository public on 2026-10-14, with its existing history. The
clean v2 tree does not remove personal information from that history: the `old`
branch and earlier commits contain tracked personal context and research records,
and they are public along with it.

Before each release, review release contents, licenses, source documents, fixtures,
contact information, and model redistribution rights. Rewriting published history
requires a separate explicit instruction.
