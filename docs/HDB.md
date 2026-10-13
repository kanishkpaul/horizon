# hdb contract

Status: design contract; no runtime API is implemented yet.

hdb is Horizon's database and evidence library. It owns durable records, documents,
retrieval, model adapters, and archive storage. It does not assign utility or run
simulations.

## Authoritative records

SQLite stores sources, documents, located chunks, proposed claims, accepted claim
revisions, contradictions/supersession, observations, case revisions, action/execution
records, forecasts, indexing intent, and artifact manifests. Source originals remain
read-only or content-addressed. Corrections create revisions rather than erase history.

An accepted claim retains subject, predicate, value/unit, source and location,
recorded/access/valid times where available, verification method, origin, confidence
meaning, review state, and supersession links. Do not merge confidence grades with
statistical probabilities or treat repeated copies as independent evidence.

Observation records distinguish pending, resolved, censored, failed, and missing
measurement where relevant. Document and model outputs enter proposed state. A user
or authorized application review accepts them explicitly.

## Derived indexes

Lexical and vector indexes reference authoritative records. A chunk retains its
source span, content hash, extraction version, acceptance/visibility metadata, and
source revision. An embedding retains model/provider revision, dimensions, metric,
normalization, and generation. Do not compare incompatible vectors.

The vector adapter provides validated upsert/delete, filtered search, generation
identity, persistence/recovery, rebuild, and availability operations. Give backend
failure a visible degraded state and preserve lexical retrieval. Retrieval results
include source locations and signals; similarity never becomes an evidence grade.

For two stores, persist an outbox with the authoritative transaction. Indexing retries
must be idempotent. Query filters verify current accepted/visible revisions even if
an index update is delayed. A deleted source must not remain retrievable from stale
vector metadata. Model changes build a new generation and switch only when complete.

## Documents and model access

Importers have typed inputs, bounded parsing, preservation rules, and location-aware
outputs. hdb's role-specific provider interfaces live beside import/retrieval
adapters; SDK types remain private. Credentials are references resolved by the
application credential store, never database fields containing secret values.

Model calls receive explicitly permitted context, limits, and cancellation. Returned
text, extracted claims, usage, and errors are typed at the boundary. See `MODELS.md`.
Proposed changes do not bypass ordinary record validation and review.

## Transactions and artifacts

Validate a mutation before its transaction. Related outcome, action status, parameter
revision, and audit changes commit together or not at all. Do not hold write locks
across network calls or simulation. Use a bounded single-writer path with explicit
read connections and busy/retry behavior where appropriate.

Run archives store immutable manifests, checksums, and numerical artifacts without
depending on hsim implementation types. Publish files and record pointers through
a recoverable sequence; handle interrupted writes and orphan artifacts explicitly.
Missing arrays produce an honest summary-only state, not a replay claim.

Workspace backup/export includes authoritative SQLite, source artifacts, and manifests
through a consistent snapshot. Derived indexes can be omitted if marked rebuildable.
Never export API keys. Restore checks versions, hashes, references, and integrity.

## Extension and checks

Adding a model, importer, reranker, or vector backend follows `FEATURES.md`. Removing
one retains accepted records and readable artifacts. Test duplicate imports,
supersession, atomic rollback, WAL backup/recovery, stale-index exclusion, interrupted
reindexing, permission isolation, and adapter failure.

References: [SQLite](https://www.sqlite.org/whentouse.html),
[SQLite backup API](https://www.sqlite.org/backup.html),
[LanceDB](https://docs.lancedb.com/), [sqlite-vec](https://alexgarcia.xyz/sqlite-vec/).
