# Tasks

Build order follows `context/file-structure.md`: models + parsing first, then the verdict-producing core (the product), then grounding tests, then state/actions, then verification, then report/server, then deploy, with adversarial tests running continuously once the core works.

Ticket IDs are ordered; do them in order unless a "Depends on" line says otherwise. Each ticket should land as one PR.

---

## Phase 0 — Scaffolding

### T01 — Project skeleton
**Build:** `pyproject.toml` (Python 3.11+, deps: `strands-agents`, `strands-agents-tools`, `tree-sitter`, `tree-sitter-typescript`, `pygithub`, `fastapi`, `uvicorn`, `httpx`, `boto3`, `pytest`), `.env.example`, empty `src/blast_radius/` package with `__init__.py`, `docker-compose.yml` stub (agent + dynamodb-local).
**Files:** `pyproject.toml`, `.env.example`, `docker-compose.yml`, `src/blast_radius/__init__.py`
**Acceptance:** `pip install -e .` succeeds; `python -c "import blast_radius"` succeeds; `pytest` runs (0 tests, no errors).
**Depends on:** none.

### T02 — Config module
**Build:** `config.py` — env var loading, model tier names (cheap/strong), target org name, thresholds (e.g. confidence cutoff for mechanical-fix downgrade).
**Files:** `src/blast_radius/config.py`
**Acceptance:** `Config` loads from env with sane defaults; missing required var raises a clear error at startup, not mid-run.
**Depends on:** T01.

---

## Phase 1 — Models + parsing (can you extract call sites correctly at all)

### T03 — Data models
**Build:** Plain dataclasses only, no logic/I/O: `ChangeContract`, `SymbolChange` (with `mechanically_expressible: bool`); `ConsumerCandidate`, `CallSite` (file, line, snippet, args_passed, return_consumed, surrounding_context); `Verdict`, `ReasoningTrace`, `Confidence`; `RunResults`, `ActionRecord`.
**Files:** `src/blast_radius/models/__init__.py`, `change.py`, `consumer.py`, `verdict.py`, `run.py`
**Acceptance:** Every field named in `context/architecture.md`'s `ChangeContract`/`CallSite` structures exists with correct types; models have no imports from `tools/`, `github/`, or any model client.
**Depends on:** T01.

### T04 — Parsing seam (LanguageAnalyzer interface)
**Build:** `LanguageAnalyzer` ABC defining the contract a language implementation must satisfy (e.g. `find_imports`, `find_call_sites`). This is the pluggability seam for a future second language — only TS/JS implements it.
**Files:** `src/blast_radius/parsing/__init__.py`, `parsing/interface.py`
**Acceptance:** ABC has no concrete logic; imports nothing from `tools/` or any model client (enforced by a lint check or test in T06).
**Depends on:** T03.

### T05 — TypeScript call-site extraction
**Build:** `typescript.py` implementing `LanguageAnalyzer` via tree-sitter + tree-sitter-typescript; `queries/imports.scm` and `queries/call_sites.scm` AST queries. Extracts per call site: file, line, snippet, args passed, whether return value is consumed, surrounding context (try/catch, null checks, branching).
**Files:** `src/blast_radius/parsing/typescript.py`, `parsing/queries/imports.scm`, `parsing/queries/call_sites.scm`
**Acceptance:** Given a small TS snippet with a known call site, returns a `CallSite` with correct file/line/snippet. Empty file / no matching symbol returns `[]`, not an error. **This file and its imports contain zero references to any model client — this is checked, not assumed.**
**Depends on:** T04, T03.

### T06 — Call-site extraction tests
**Build:** Unit tests against hand-written TS fixtures (inline strings or tiny files) covering: plain call, call with args, call whose return is discarded, call inside try/catch, call inside a null check/branch. Include a static-analysis test asserting `parsing/` imports nothing from `tools/usage_analysis.py` or any Bedrock/model client module.
**Files:** `tests/conftest.py`, `tests/unit/test_call_sites.py`
**Acceptance:** All cases pass; the "no model imports in parsing/" test fails loudly if ever violated.
**Depends on:** T05.

---

## Phase 2 — The product: change contract + usage analysis + verdicts

### T07 — GitHub client (App auth)
**Build:** `github/client.py` — PyGithub wrapper authenticated as a GitHub App (not a PAT), exposing repo/PR/content access needed by later tools.
**Files:** `src/blast_radius/github/__init__.py`, `github/client.py`
**Acceptance:** Client authenticates against a real (or fixture) GitHub App installation and can fetch a known PR's metadata in a manual smoke test.
**Depends on:** T02.

### T08 — `get_pr_diff` tool
**Build:** Fetches raw diff, changed file paths, base/head SHAs for a given repo + PR number. Fails clearly (repo/PR not found → abort run, reported to caller) rather than returning partial garbage.
**Files:** `src/blast_radius/tools/pr_diff.py`
**Acceptance:** Given a real PR, returns a `PRDiff` with non-empty diff text and correct SHAs; given a nonexistent PR, raises a typed error the caller can catch.
**Depends on:** T07.

### T09 — System + extraction prompts
**Build:** `prompts/system.md` (the agent system prompt from `context/agents.md`, verbatim as the draft base), `prompts/extract_contract.md` (instructs the cheap-tier model to extract public API surface changes only — ignore internal refactors/tests/comments/formatting; set `mechanically_expressible` per symbol, erring toward `False`).
**Files:** `src/blast_radius/prompts/system.md`, `prompts/extract_contract.md`
**Acceptance:** Prompts reviewed against the "Phase 1 — good/bad" examples in `context/agents.md` (catches dual-kind changes, doesn't flag renamed private helpers, doesn't mark semantic changes mechanical).
**Depends on:** T01.

### T10 — `extract_change_contract` tool
**Build:** Cheap-tier model call. Takes `PRDiff`, returns `ChangeContract` populated with `SymbolChange` entries per T09's prompt.
**Files:** `src/blast_radius/tools/change_contract.py`
**Acceptance:** On a fixture diff that changes both signature and return contract of one symbol, produces two `SymbolChange` kinds for that symbol. On a diff touching only tests/formatting, produces an empty `changes` list.
**Depends on:** T08, T09, T03.

### T11 — Fixture repos
**Build:** Four consumer repos + one provider (`payments-lib`) proving each verdict path, per `context/spec.md`/`context/file-structure.md`: `checkout-service` (mechanically_fixable), `billing-worker` (needs_human — null-return-to-retry), `reporting-api` (unaffected — imports, never calls), `legacy-admin` (unaffected — pinned to 1.x). `setup.sh` creates/resets them on GitHub; `fixtures/README.md` documents what each proves.
**Files:** `fixtures/README.md`, `fixtures/setup.sh`, `fixtures/payments-lib/`, `fixtures/checkout-service/`, `fixtures/billing-worker/`, `fixtures/reporting-api/`, `fixtures/legacy-admin/`
**Acceptance:** `setup.sh` run twice is idempotent (resets cleanly); each consumer repo's intended verdict is stated in `fixtures/README.md` and matches its actual code.
**Depends on:** T01.

### T12 — `check_version_constraint` + `find_consumers`
**Build:** `tools/version_check.py` — pure semver range check, no model, no network. `github/search.py` — org-wide code search over `package.json` + import statements. `tools/consumers.py` — wraps search into `find_consumers`, applying manifest-declared check, then version constraint, then import check, in that strict order; partial results (e.g. rate-limited) are reported as partial, never silently truncated.
**Files:** `src/blast_radius/tools/version_check.py`, `github/search.py`, `tools/consumers.py`
**Acceptance:** Against the T11 fixtures, `legacy-admin` is cleared by version constraint alone (never reads its code); `reporting-api` and `checkout-service`/`billing-worker` pass through to candidates. Simulated rate-limit returns a result flagged partial, not an incomplete list presented as complete.
**Depends on:** T11, T07.

### T13 — Usage-analysis prompt
**Build:** `prompts/analyze_usage.md` — instructs the strong-tier model per the rules in `context/agents.md`'s system prompt: reason only over given `CallSite`s, cite real file:line, unaffected verdicts require reasons too, low confidence on mechanically_fixable downgrades to needs_human, most-severe verdict wins across call sites.
**Files:** `src/blast_radius/prompts/analyze_usage.md`
**Acceptance:** Reviewed against "Phase 3 — good/bad" examples in `context/agents.md`.
**Depends on:** T01.

### T14 — `analyze_usage` tool
**Build:** Strong-tier model call. Takes `SymbolChange` + `list[CallSite]`, returns a `Verdict` with reasoning trace and confidence. Trace must cite file:line from the given `CallSite` objects only.
**Files:** `src/blast_radius/tools/usage_analysis.py`
**Acceptance:** On `checkout-service` fixture call sites → `mechanically_fixable`. On `billing-worker` (null-check-then-retry pattern) → `needs_human`, with the trace explicitly naming what a naive fix would break. On `reporting-api` (import, no call sites) → `unaffected` with a stated reason, without calling the model (empty call-site list short-circuits).
**Depends on:** T13, T05, T03, T11.

### T15 — Verdict aggregation
**Build:** Logic that, given multiple `Verdict`s for one consumer (one per changed symbol / call site group), returns the single most-severe verdict for that repo (`needs_human` > `mechanically_fixable` > `unaffected`).
**Files:** `src/blast_radius/tools/usage_analysis.py` (aggregation function) or a small `models/verdict.py` helper — colocate with T03/T14, whichever already owns `Verdict`
**Acceptance:** Repo with 3 `mechanically_fixable` + 1 `needs_human` call sites aggregates to `needs_human`. Repo with only `unaffected` verdicts aggregates to `unaffected`.
**Depends on:** T14.

### T16 — Golden-file verdict tests
**Build:** One YAML case per scenario (mirroring the four fixtures plus edge cases) describing input call sites and expected verdict; `test_verdicts.py` runs each through `analyze_usage` (or a cached response, if T22 lands first) and checks the verdict matches.
**Files:** `tests/verdicts/cases/*.yaml`, `tests/verdicts/test_verdicts.py`
**Acceptance:** All four fixture-derived cases pass with the correct verdict; adding a new case requires only a new YAML file, no code change.
**Depends on:** T14, T11.

### T17 — Aggregation unit test
**Build:** `test_aggregation.py` covering severity ordering and the "partial fix is worse than no fix" rule from `context/agents.md`.
**Files:** `tests/unit/test_aggregation.py`
**Acceptance:** Test fails if aggregation ever picks anything but the most severe verdict present.
**Depends on:** T15.

---

## Phase 3 — Grounding tests (verify traces are honest before building on them)

### T18 — Line-reference grounding test
**Build:** `test_trace_line_refs.py` — for every verdict produced against a fixture, parse the reasoning trace's cited file:line references and assert each line exists in the actual retrieved file content.
**Files:** `tests/grounding/test_trace_line_refs.py`
**Acceptance:** Passes against all T11 fixtures; fails if a prompt/model change ever causes a fabricated line number (test this by temporarily injecting a bad reference and confirming the test catches it, then revert).
**Depends on:** T14, T11.

### T19 — No-phantom-code grounding test
**Build:** `test_no_phantom_code.py` — asserts every code snippet or symbol mentioned in a reasoning trace appears in the `CallSite` snippets actually passed to `analyze_usage`, not invented.
**Files:** `tests/grounding/test_no_phantom_code.py`
**Acceptance:** Passes against all fixtures; this and T18 are treated as release-blocking — a failure here blocks merging any change to `analyze_usage` or its prompt.
**Depends on:** T14, T11.

---

## Phase 4 — State + actions (writes, with idempotency from the start)

### T20 — Action store interface + SQLite backend
**Build:** `state/store.py` — `ActionStore` ABC (`get`, `put`, keyed by `{provider_repo}#{pr_number}#{symbol}#{consumer_repo}`, storing verdict, action_taken, artifact_url, timestamps, change_contract_hash). `state/sqlite.py` — local implementation.
**Files:** `src/blast_radius/state/__init__.py`, `state/store.py`, `state/sqlite.py`
**Acceptance:** Round-trip put/get works; same key with a changed `change_contract_hash` is distinguishable from an unchanged re-run.
**Depends on:** T03, T02.

### T21 — DynamoDB backend
**Build:** `state/dynamo.py` implementing the same `ActionStore` ABC against DynamoDB (or dynamodb-local via `docker-compose.yml`).
**Files:** `src/blast_radius/state/dynamo.py`, update `docker-compose.yml`
**Acceptance:** Same test suite as T20 (parametrized over both backends) passes against dynamodb-local.
**Depends on:** T20.

### T22 — Development response cache
**Build:** `state/cache.py` — local, disposable cache for model responses keyed on (change contract hash + call site content hash). Never used in the deployed path; wired in only when a `--use-cache` / dev-mode flag is set.
**Files:** `src/blast_radius/state/cache.py`
**Acceptance:** Re-running an unmodified fixture in dev mode produces zero new model calls (verified via a call-counting mock).
**Depends on:** T14, T20.

### T23 — Idempotency unit test
**Build:** `test_idempotency.py` — simulates a re-run on the same (change, repo) key and asserts the store reports "existing artifact" rather than allowing a second create.
**Files:** `tests/unit/test_idempotency.py`
**Acceptance:** Test fails if a second `put` for the same key is ever treated as a fresh create instead of an update.
**Depends on:** T20.

### T24 — GitHub writes (idempotent PR/issue creation)
**Build:** `github/writes.py` — create/update PR, create/update issue, both checking `ActionStore` first per T20's key.
**Files:** `src/blast_radius/github/writes.py`
**Acceptance:** Calling twice for the same key updates the existing PR/issue rather than creating a second one (verified against a fixture repo or a mocked GitHub API).
**Depends on:** T20, T07.

### T25 — `resolve_owner` tool
**Build:** CODEOWNERS lookup first, git blame on the affected file paths as fallback. No owner found → issue filed unassigned, noted in the report (not silently dropped).
**Files:** `src/blast_radius/tools/ownership.py`
**Acceptance:** Against a fixture repo with a CODEOWNERS entry for the affected path, returns that owner; against one without, falls back to blame; against neither, returns an explicit "unassigned" result.
**Depends on:** T07.

### T26 — `open_pr` / `file_issue` tools
**Build:** Thin tool wrappers around `github/writes.py`, taking the domain objects (`Patch`, `Verdict`, `Owner`, `ProviderPRContext`) and producing `PRUrl` / `IssueUrl`.
**Files:** `src/blast_radius/tools/actions.py`
**Acceptance:** Matches the signatures in `context/agents.md` exactly; idempotency check happens before any write in both paths.
**Depends on:** T24, T25, T03.

---

## Phase 5 — Verification

### T27 — Verification container
**Build:** `deploy/Dockerfile.verify` — isolated image with Node/npm, no credentials, no AWS/GitHub tokens baked in or mounted at runtime.
**Files:** `deploy/Dockerfile.verify`
**Acceptance:** Building and running the image with no env vars set still succeeds at `npm install && npm test` on a known-good fixture; inspecting the running container shows no credential files or env vars present.
**Depends on:** T11.

### T28 — `verify_patch` tool
**Build:** Applies a `Patch` to a checked-out consumer repo inside T27's container, runs `npm install && npm test`, returns `VerificationResult`. Failure is not an error — it's a signal to downgrade the verdict, handled by the caller.
**Files:** `src/blast_radius/tools/verification.py`
**Acceptance:** A correct patch against `checkout-service` verifies green. A deliberately broken patch verifies red without crashing the run.
**Depends on:** T27.

### T29 — Patch-generation prompt + tool
**Build:** `prompts/generate_patch.md` (strong-tier model). `tools/patch.py` — `generate_patch`, called only for `mechanically_fixable` verdicts.
**Files:** `src/blast_radius/prompts/generate_patch.md`, `tools/patch.py`
**Acceptance:** Against `checkout-service`'s call sites, produces a `Patch` that, when run through T28, verifies green.
**Depends on:** T14, T13 (as a prompt-writing precedent), T28.

---

## Phase 6 — Report + server (the surfaces)

### T30 — Report builder
**Build:** `report/builder.py` — turns `RunResults` into a single markdown comment: counts, links, every verdict with its reason (including cleared ones), matching the "Phase 5 — good" example in `context/agents.md`. `report/template.md` as the base template.
**Files:** `src/blast_radius/report/__init__.py`, `report/builder.py`, `report/template.md`
**Acceptance:** Given a `RunResults` with a mix of all three verdict types plus one `analysis_failed`, produces one comment body where every repo is listed exactly once with a stated reason.
**Depends on:** T03.

### T31 — `post_report` tool
**Build:** Posts (or updates, on re-run) the T30 comment on the provider PR via `github/client.py`.
**Files:** `src/blast_radius/tools/report.py`
**Acceptance:** First run creates one comment; a re-run on the same PR edits that comment instead of posting a second one.
**Depends on:** T30, T07, T20 (to detect "own prior comment").

### T32 — Tool registry
**Build:** `tools/__init__.py` — registers all tools built so far (T08, T10, T12, T05/T14 wrapper, T29, T28, T25, T26, T31) for Strands.
**Files:** `src/blast_radius/tools/__init__.py`
**Acceptance:** Strands agent can list all registered tools with correct signatures matching `context/agents.md`.
**Depends on:** T08, T10, T12, T14, T26, T28, T29, T31.

### T33 — Agent wiring
**Build:** `agent.py` — Strands agent instance, system prompt (T09) loaded, phases 1–5 wired in strict sequence, phase 3 run per-candidate (parallel or sequential per a config flag — sequential is fine for four fixtures per `context/agents.md`).
**Files:** `src/blast_radius/agent.py`
**Acceptance:** End-to-end run against the T11 fixtures produces the four expected verdicts (`checkout-service` → mechanically_fixable + verified PR opened, `billing-worker` → needs_human + issue filed, `reporting-api` and `legacy-admin` → unaffected, no writes) and one posted report.
**Depends on:** T32, T15, T22.

### T34 — Webhook server
**Build:** `server/app.py` (FastAPI: `/webhook`, `/analyze`, `/health`), `server/webhook.py` (signature verification, event filtering to PR-opened/updated on the provider repo).
**Files:** `src/blast_radius/server/__init__.py`, `server/app.py`, `server/webhook.py`
**Acceptance:** `/health` returns 200. A signed test webhook payload for "PR opened" triggers `agent.py`'s run; an unsigned/invalid payload is rejected with 401, not silently ignored. `POST /analyze {repo, pr_number}` triggers the same run path without a webhook.
**Depends on:** T33.

---

## Phase 7 — Deploy

### T35 — Local dev scripts
**Build:** `scripts/run_local.py` (analyze a PR without the webhook), `scripts/replay.py` (re-run from cached model responses via T22), `scripts/cost_report.py` (token spend by phase, from OpenTelemetry spans or logged usage).
**Files:** `scripts/run_local.py`, `scripts/replay.py`, `scripts/cost_report.py`
**Acceptance:** `run_local.py` against a fixture PR produces the same result as the webhook path. `replay.py` on a cached fixture makes zero live model calls.
**Depends on:** T33, T22.

### T36 — Deployment config
**Build:** `deploy/agentcore/` (Bedrock AgentCore Runtime config), `deploy/Dockerfile` (main agent image, distinct from `Dockerfile.verify`), `deploy/billing_alarm.yaml`.
**Files:** `deploy/agentcore/*`, `deploy/Dockerfile`, `deploy/billing_alarm.yaml`
**Acceptance:** Agent deploys to AgentCore (or the documented Lambda+Fargate fallback) and responds on `/health`. Billing alarm fires in a manual test at its configured threshold.
**Depends on:** T34.

---

## Phase 8 — Adversarial tests (continuous once Phase 2 works, not a final phase — start alongside T14 and keep adding)

### T37 — Adversarial fixture cases
**Build:** Cases designed to fool `get_call_sites`/`analyze_usage`: call site behind a local wrapper, symbol re-exported through a barrel file, aliased import (`import { charge as bill }`), call already wrapped in try/catch.
**Files:** `tests/adversarial/helper_wrapper.py`, `re_export.py`, `aliased_import.py`, `try_catch_wrapped.py`
**Acceptance:** Each case's actual tree-sitter/model behavior is documented (pass or known-limitation) — per `context/tech-stack.md`, if tree-sitter demonstrably fails on one of these, that's the trigger to consider the ts-morph escalation path, not to silently ignore it.
**Depends on:** T14, T05. (Start after T14 lands; add cases incrementally, don't block later phases on full coverage here.)

---

## Explicitly not ticketed (per `context/spec.md` "Out of Scope")

Do not create tickets for: multi-language support beyond the TS/JS `LanguageAnalyzer` implementation, transitive dependency analysis, detecting independently-fixed consumers, auto-merge, monorepo support, real-time dashboards/Slack integration, or any multi-agent (Graph/Swarm/Subagent) architecture. If a future ticket seems to need one of these, check `context/spec.md` first.
