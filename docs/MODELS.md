# BYOK and local model contract

Status: required behavior; adapters and credential handling are not implemented yet.

## Modes and roles

No-model mode provides manual evidence entry, lexical retrieval, simulation, planning,
and export. Local mode uses a user-configured local inference endpoint. BYOK mode
uses a user-selected provider and their own API key. Mixed-role configurations are
allowed only when deliberately configured and clearly shown.

Chat/reasoning, embeddings, and reranking are independent roles. Each configuration
records adapter, endpoint, model ID/revision where available, declared capabilities,
limits, context policy, and a credential reference. Do not assume one model supports
all roles or that a compatible endpoint implements every optional protocol feature.

## Provider boundary

Start with one native BYOK adapter and one configurable compatible endpoint adapter,
then add providers through the same contract. Verify supported behavior for local
servers such as Ollama, LM Studio, llama.cpp, or vLLM at implementation time; naming
them here is a compatibility target, not a claim of tested integration.

Adapters expose supported roles, streaming/structured-output behavior, input/output
limits, usage availability, cancellation, timeouts, retry semantics, and typed errors.
Capability probing must not leak private context. Use a fixed public test payload.
Unsupported abilities produce an actionable error or an explicitly selected fallback.

## Context and privacy

Store keys in the operating system credential store. Persist only references.
Redact headers, keys, and source content from diagnostic logs. Changing an endpoint
or role must not carry permission to send an existing workspace silently.

The application constructs an inspectable context packet: purpose, selected snippets,
source IDs/locations, destination, role, estimated size/cost, and allowed disclosure.
A policy gate validates it before transport. Strict local-only policy rejects remote
destinations; loopback addressing does not by itself guarantee that the user's model
server has no upstream cloud behavior. Explain that configuration boundary honestly.

No local failure can automatically fall back to a cloud provider. No-model operation
must remain available when a provider is offline or a key is absent. No telemetry or
background model download is enabled merely by opening a workspace.

## Reliability and cost

Stream responses with cancellation and bounded buffers. Retry only safe operations
with explicit limits; do not silently repeat a charged request whose outcome is
unknown. Distinguish missing usage from zero usage. Cost estimates use dated provider
configuration and remain estimates when prices or actual usage are unavailable.

Limits cover input/output tokens, request count, time, concurrency, and spend. Reserve
budget before concurrent calls where needed. Spending caps are best-effort when a
provider lacks reliable usage or billing data; do not promise provider-side enforcement.

## Model output and indexes

Model extraction creates proposed claims with supporting source locations and review
state. Validate structured output as untrusted input. Do not allow model text to write
accepted records, control shell commands, or change hsim during a run.

Embedding configuration includes model revision, dimensions, metric, normalization,
chunking version, and content hashes. Changes require a new index generation. A query
uses the same compatible embedding space as its index. Reranking is optional, retains
source/permission filtering, and cannot turn similarity into factual certainty.

## Acceptance suite

Use offline fake servers for success, streaming, malformed output, unsupported roles,
timeout, cancellation, rate limit, missing usage, permission denial, credential absence,
and local-to-cloud fallback prevention. Test mixed-role disclosure independently.
No live model calls or paid usage are implied by ordinary test execution.
