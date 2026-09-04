# BlastRadiusAgent

A single Python agent, built on the [Strands Agents SDK](https://github.com/strands-agents), that watches a shared TypeScript/JavaScript library repo. When a PR changes the library, it determines which consumer repos in the org **actually break** — not just import the library — and for each one: clears it with a reason, opens a verified PR for mechanical fixes, or files an issue for a human when the break is semantic. It posts one consolidated report on the provider PR and never merges anything.

## The problem

In a monorepo, changing a shared library is manageable — tooling finds every caller and CI breaks immediately. In a polyrepo, none of that exists: you change an internal library, announce it in Slack, and wait to find out who you broke.

Existing tooling (dependency graphs, code search, Dependabot) answers **who imports this package**, which is mostly noise. The question that matters is **who actually breaks, and can it be fixed automatically?** Answering that means reading how each consumer uses the changed thing and reasoning about whether the change violates that usage.

## What it does

For each consumer repo, BlastRadiusAgent reaches one of three verdicts:

- **Unaffected** — imports the library but doesn't touch what changed, or is pinned to a version that won't receive it. No action, but the reason is recorded.
- **Broken, mechanically fixable** — a deterministic transformation (renamed symbol, reordered arguments). The agent writes the fix, verifies it builds and passes tests in an isolated container, and opens a PR.
- **Broken, needs a human** — the break involves meaning, not just shape (e.g. a function that returned `null` now throws). A mechanical fix would compile but silently change behavior, so the agent refuses to auto-fix, files an issue routed to the code owner, and explains why.

It then posts one consolidated report on the original PR: what's affected, what it fixed, what needs attention, and what it cleared and why.

**A human approves every merge. The agent proposes; it never merges.**

## Why every verdict carries evidence

"billing-worker: BREAKS" gets ignored. "billing-worker line 47 calls `charge()` and branches on a null return to trigger retry — this change throws instead, so the retry path becomes unreachable" gets acted on, because it can be verified in ten seconds without opening the repo.

Every verdict — including "unaffected" ones — cites real file paths, real line numbers, and the actual call site, built only from code the agent actually retrieved. tree-sitter deterministically locates call sites; the model only ever reasons about call sites it was given. A trace citing a line that doesn't exist, or reasoning about code never retrieved, is the failure mode this project is designed around avoiding.

## Architecture

Single agent, tool-orchestrated, driven by a GitHub webhook (with a manual `POST /analyze` fallback). Five strictly sequential phases; only phase 3 parallelizes, across consumers:

1. **Understand the change** — fetch the PR diff, extract a structured `ChangeContract` of symbol-level changes.
2. **Narrow candidates** — cheap filters (manifest declares package? version range accepts target?) clear repos before any code is read.
3. **Per-consumer loop** — tree-sitter extracts call sites deterministically; a model reasons only over what it's given and returns one verdict per repo.
4. **Act, differentiated by verdict** — verified PR for mechanical fixes, issue filed to the code owner for anything semantic.
5. **Report** — one comment on the provider PR listing every verdict with its reason, including cleared ones.

See `context/architecture.md` and `context/agents.md` for full detail, and `context/spec.md` for scope.

## Tech stack

- **Agent: Python 3.11+**, Strands Agents SDK. **Analysis target: TypeScript/JavaScript** (no agent code is written in TS/JS).
- **Models**: Claude via Amazon Bedrock — cheap tier for change-contract extraction, strong tier for usage-breakage reasoning and patch generation.
- **Parsing**: tree-sitter + tree-sitter-typescript, strictly deterministic, no model calls.
- **GitHub integration**: PyGithub, authenticated as a GitHub App.
- **Webhook receiver**: FastAPI.
- **Verification**: Docker, isolated, no credentials mounted.
- **State**: DynamoDB (deployed) / SQLite (local), for idempotency only.
- **Hosting**: Bedrock AgentCore Runtime (Lambda+Fargate fallback).

See `context/tech-stack.md` for the full breakdown and rationale.

## Scope

Single provider repo per run, direct dependencies only, TypeScript/JavaScript + npm manifests, consumers within one GitHub org, proposals only (PRs/issues) — never auto-merge.

Out of scope: multi-language support, transitive dependency analysis, detecting independently-fixed consumers, real-time dashboards/Slack integration, multi-agent architecture. See "Out of Scope" in `context/spec.md`.

## Status

Planning stage — only design docs exist in `context/` so far. No source code, build tooling, or tests yet.

## License

Apache 2.0.
