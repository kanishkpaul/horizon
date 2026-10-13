# Security and private data

Horizon is designed for local ownership of sensitive evidence and decisions. The
current tree is a foundation, not a deployed application; the following behaviors
are requirements for future implementation.

## Storage and secrets

Store API keys in the operating system credential store. Store references to keys
in settings, not key values. Exclude keys, personal documents, workspaces, database
files, vector indexes, logs containing user context, and private run archives from
Git. Backups and exports must explain what data they contain and exclude secrets.

SQLite and ordinary vector indexes do not provide encryption merely because they
are local. Do not promise encryption at rest until its implementation and recovery
behavior are tested. Document the protection provided by the host OS.

## Model and document boundaries

Local, BYOK, and no-model modes have explicit capability and context permissions.
No automatic cloud fallback is allowed. Endpoint changes require user-visible
configuration; arbitrary endpoint URLs are not instructions to disclose a workspace.
Logs should use job IDs and redacted metadata, not document text or authorization
headers. Usage estimates must identify when a provider does not supply actual usage.

Treat imported text and model responses as untrusted data. Extract proposed claims
and actions into validated typed objects, with source references and a review step.
Do not execute instructions embedded in sources. Model output does not directly
write accepted evidence, change a simulation, run shell commands, or contact others.

## Reporting

Do not put credentials or private documents into public issues. Report a suspected
vulnerability privately to the repository owner through an already available
private channel. No dedicated reporting address or response-time promise is claimed.

Before public release, review both the release tree and Git history for personal
context and redistribution rights. See `docs/MIGRATION.md`.
