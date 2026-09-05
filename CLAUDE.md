# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## State of the repository

This repo currently contains only planning documents in `context/` (`spec.md`, `tech-stack.md`, `architecture.md`, `agents.md`, `file-structure.md`). No source code, `pyproject.toml`, tests, or build tooling exist yet — this file will need build/lint/test commands added once the project is scaffolded (see `context/file-structure.md` for the intended layout, under `blast-radius-agent/`).

## What this project is

**BlastRadiusAgent**: a single Python agent, built on the Strands Agents SDK, that watches a shared TypeScript/JavaScript library repo. When a PR changes the library, it determines which consumer repos in the org **actually break** (not just import the library), and for each one: clears it with a reason, opens a verified PR for mechanical fixes, or files an issue for a human when the break is semantic. It posts one consolidated report on the provider PR and never merges anything.

The core value proposition, and the thing every design decision defends: **grounded reasoning**. tree-sitter deterministically locates call sites; the model only ever reasons about call sites it was actually given, and every verdict — including "unaffected" ones — must cite real file:line evidence. A trace citing a line that doesn't exist, or reasoning about code never retrieved, is the single failure mode that would sink this project's credibility. See "Failure modes to guard against" in `context/agents.md`.

## Architecture (read `context/architecture.md` and `context/agents.md` for full detail)

Single agent, tool-orchestrated, driven by a GitHub webhook (with a manual `POST /analyze` fallback for demo reliability). Five strictly sequential phases; only phase 3 parallelizes (across consumers, not across agents):

1. **Understand the change** — `get_pr_diff` → `extract_change_contract` (cheap-tier model). Produces a `ChangeContract` of `SymbolChange`s, each marked `mechanically_expressible`. Everything downstream reasons against this structured object, never the raw diff.
2. **Narrow candidates** — `find_consumers` → `check_version_constraint`, in that order deliberately: cheap filters (manifest declares package? version range accepts target?) clear repos *before* any code is read. Ordering here is load-bearing for cost.
3. **Per-consumer loop (the product)** — `get_call_sites` (tree-sitter, deterministic, zero model involvement) → `analyze_usage` (strong-tier model call, judges only what it was shown) → one `Verdict`: `unaffected`, `mechanically_fixable`, or `needs_human`. A repo with multiple call sites takes its **most severe** verdict. Low confidence on `mechanically_fixable` downgrades to `needs_human` — the agent may be unsure, but may not act while unsure.
4. **Act, differentiated by verdict** — `mechanically_fixable`: `generate_patch` → `verify_patch` (Docker, `npm install && npm test`, no credentials mounted, untrusted code) → `open_pr`. A verification failure downgrades to `needs_human` rather than opening a broken PR. `needs_human`: `resolve_owner` (CODEOWNERS, then git blame) → `file_issue`. Every write checks action state for idempotency first — force-pushed provider PRs get updated artifacts, never duplicates.
5. **Report** — one comment on the provider PR listing every verdict with its reason, including cleared ones. Updates its own prior comment on re-runs. The agent stops here; it never merges.

**Why one agent, not several**: every phase shares the same input, change contract, and escalation model, with no independent judgment between stages — splitting would add coordination failure modes for nothing. This is a documented decision (see "Why not multi-agent" in `context/agents.md`); don't reintroduce Strands Graph/Swarm/Subagent patterns without revisiting that argument first.

### State (three kinds, don't conflate them)

- **Run state** — in-memory, dies with the run (change contract, candidates, verdicts).
- **Action state** — DynamoDB in deployment, SQLite locally. The only durable state; exists solely for idempotency, keyed `{provider_repo}#{pr_number}#{symbol}#{consumer_repo}`.
- **Development cache** — local, disposable, model responses keyed on (change contract hash + call site content hash). Never deployed; exists to keep fixture-tuning cheap.

The agent is otherwise deliberately stateless: no memory across PRs, no learned preferences. Each run is a pure function of (PR diff, current consumer repo state).

### Trust boundaries

- Consumer repo code is untrusted — `verify_patch` runs `npm install && npm test` in an isolated container (`deploy/Dockerfile.verify`) with no credentials mounted, since `postinstall` scripts execute arbitrary code.
- Model output is untrusted until verified — a generated patch is never opened as a PR on model confidence alone; it must apply, build, and pass tests first, or it becomes an issue instead.

## Tech stack (see `context/tech-stack.md`)

- **Agent language: Python 3.11+**, using the **Strands Agents SDK**. The **analysis target is TypeScript/JavaScript** — do not confuse the two; no agent code is written in TS/JS.
- **Models**: Claude via Amazon Bedrock, tiered — cheap/fast tier for change-contract extraction, strong tier for usage-breakage reasoning and patch generation (don't economize on these two).
- **Parsing: tree-sitter + tree-sitter-typescript**, strictly deterministic, no model calls. This is architectural, not incidental — the `parsing/` package must never import a model client (see `context/file-structure.md`).
- **GitHub integration**: PyGithub (or `httpx` where awkward), authenticated as a GitHub App.
- **Webhook receiver**: FastAPI, with `smee.io`/ngrok for local dev.
- **Verification**: Docker (`Dockerfile.verify`, isolated from the main `Dockerfile`).
- **State**: DynamoDB (deployed) / SQLite (local).
- **Hosting**: Bedrock AgentCore Runtime, with Lambda+Fargate as a fallback if AgentCore proves painful.
- **Observability**: OpenTelemetry, built into Strands.

Explicitly excluded: any frontend framework, vector DB/RAG (retrieval is AST-query-based, not semantic), Step Functions/EventBridge/SQS, and multi-agent primitives.

## Scope discipline

Per `context/spec.md`: single provider repo per run, direct dependencies only, TypeScript/JavaScript + npm manifests only, consumers within one GitHub org, proposals only (PRs/issues) — never auto-merge. Explicitly out of scope: multi-language support, transitive dependency analysis, detecting independently-fixed consumers, real-time dashboards/Slack integration, and multi-agent architecture. When in doubt about whether to build something, check "Out of Scope" in `context/spec.md` first — the six-week build budget assumes these stay cut.

## Changelog

Every change you make to this repo must be logged in `CHANGELOG.md` at the repo root, under an `## [Unreleased]` heading, before you consider the task done. Add a bullet describing what changed and why (not a diff dump) under the appropriate subheading (`Added`, `Changed`, `Fixed`, `Removed`) — follow [Keep a Changelog](https://keepachangelog.com/) conventions. Do this as part of the same turn as the code change, not as a separate follow-up task.

## The line this project must not cross

If call sites were ever found by text search and handed to a model asked "is this broken?", this degrades to grep with an LLM stapled on. The value is in tree-sitter deterministically extracting *how* a symbol is used (arguments, return-value consumption, surrounding error handling) and the model reasoning only over that grounded evidence. Any change to `get_call_sites` or `analyze_usage` should be checked against this line.
