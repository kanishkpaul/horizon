# Decisions

**D-001: Durable project location.** The session started in a temporary scratch workspace that is deleted with the session. The system must persist, so it lives at `~/Developer/project-horizon` under git. Private originals (CV, evidence ledger, workbooks) are gitignored; only their checksums are tracked.

**D-002: Local-first, single process.** FastAPI serves both the API and the built React app on `127.0.0.1:8765`. There are no cloud services and no accounts. Embeddings are computed locally (fastembed, ONNX, CPU).

**D-003: One SQLite file instead of graph/vector databases.** About 1.3k documents, about 3.6k claims and typed edges. SQLite gives transactions, FTS5 (BM25), WAL, backups (`VACUUM INTO`) and zero operations. Exact cosine search in numpy takes < 5 ms. Neo4j, Qdrant, pgvector or HNSW would add maintenance with no decision value at this scale. Revisit above ~100k documents.

**D-004: Temporal claims are the unit of fact.** Facts carry valid, recorded, source and access times, a grade and a verification method. New evidence supersedes old evidence but never deletes it. Workbook claims are capped at grade B, because Horizon did not read their sources itself.

**D-005: A stochastic AND/OR state-transition simulator, not a graph shortest path and not an MDP solver.** Prerequisites are conditions on state; outcomes add state; some actions create others. Policies are priority lists plus rules, which are explainable and editable. An exact MDP/POMDP solve or RL was rejected: the probabilities are mostly judgment, so an optimal policy would mostly be optimising noise.

**D-006: Vectorise across worlds.** All worlds advance together each week, giving about 40–100 ms per strategy for 3,000 worlds. That makes interactive what-ifs recompute exactly instead of relying on cached approximations.

**D-007: Common random numbers via keyed streams.** Each random quantity is drawn from a stream keyed by (seed, purpose, name), which gives paired comparisons and reproducibility.

**D-008: Natural-unit metrics plus several value models.** There is no single "life score". Eight value models (balanced, research, compensation, entrepreneurial, optionality, autonomy, robust/CVaR, bounded upside) each support hard constraints.

**D-009: Binned EVPPI with a permutation noise floor.** Transparent and cheap. Regression EVPPI (Strong & Oakley) is the documented upgrade.

**D-010: Strategy search by NSGA-II over action subsets.** Prerequisites are repaired automatically and standard contingency rules attached. Results go through scenario-regret and adversarial review before they are trusted.

**D-011: Video by frame capture of the same React component.** Remotion and Motion Canvas were considered. Stepping the app's own `TheaterFrame` in headless Chromium (Playwright, using the locally cached browser) and piping PNGs to ffmpeg guarantees that the video and the interactive theater show the same state. Narration uses the macOS `say` voice locally; there are no paid services.

**D-012: Self-hosted fonts.** Fonts are bundled through `@fontsource` so the app works offline and video frames are deterministic. Google Fonts were dropped.

**D-013: Research workers in parallel, results as structured JSONL.** Verification, discovery and base-rate workers wrote graded, sourced records that are ingested as claims, not prose. They were read-only and contacted no one.

**D-014: A revise-and-resubmit action and an adjustable rushed-paper penalty.** Added after the strategy search consistently preferred deferring the register paper. The original model had no second chance after an October rejection and applied the rush penalty even when the paper was finished. Both biases favoured deferral and are now removed. The conditional answer (January unless nearly done *and* validated) survives.

**D-015: Index caching.** `index.html` is served with `Cache-Control: no-cache`, because a cached index pointed browsers at stale hashed bundles.
