# Changelog

All notable changes to this project are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Fixed
- `fixtures/setup.sh` — `breaking-change-v2` is now branched from the just-pushed `main` (clone → checkout -b → overlay content → commit) instead of built from an independent `git init`. The old approach gave `main` and `breaking-change-v2` unrelated histories, so `gh pr create` failed with "no history in common with main"; under `set -euo pipefail` that aborted the script right after `payments-lib` was created, before any of the four consumer repos were touched.

### Added
- `CLAUDE.md` — guidance for Claude Code, summarizing architecture, tech stack, and scope from `context/`.
- `README.md` — project overview.
- `.gitignore` — excludes `context/`, Python artifacts, env/secrets, local state, OS/editor files, and (as of T11) `node_modules/`/`package-lock.json` from local fixture testing.
- `tasks.md` — ordered build tickets derived from `context/spec.md`, `architecture.md`, and `agents.md`.
- `testing.md` — eval set and per-task-type definition of done.
- Changelog-maintenance instructions in `CLAUDE.md`.
- `CHANGELOG.md`.
- T01: project skeleton — `pyproject.toml`, `.env.example`, `docker-compose.yml` (agent + dynamodb-local stub), `src/blast_radius/__init__.py`. Verified `pip install -e .`, `import blast_radius`, and `pytest` (0 tests) all succeed.
- T02: `src/blast_radius/config.py` — `Config` dataclass loading from env, with required vars (`GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY_PATH`, `GITHUB_WEBHOOK_SECRET`, `TARGET_ORG`) raising `ConfigError` when missing, and defaults for model tiers, AWS region, confidence threshold, and state backend.
- T03: `src/blast_radius/models/` — plain dataclasses for `ChangeContract`/`SymbolChange` (`change.py`), `ConsumerCandidate`/`CallSite` (`consumer.py`), `Verdict`/`ReasoningTrace`/`Citation`/`Confidence` (`verdict.py`), and `RunResults`/`ConsumerResult`/`ActionRecord` (`run.py`). All frozen, stdlib-only imports (`dataclasses`, `enum`), no I/O. Verified every model constructs, is immutable, and the package has zero imports from `tools/`, `github/`, `state/`, or a model client.
- T11: `fixtures/` — one provider (`payments-lib`) and four consumer repos proving each verdict path. The PR bundles a signature change (`charge(cardToken, amount)` → `charge(amount, cardToken)`, mechanical) and a return-contract change (decline resolves `null` → throws `PaymentDeclinedError`, semantic) on the same symbol. `checkout-service` never branches on the return value → `mechanically_fixable`; `billing-worker` branches on `null` to trigger a retry → `needs_human`, since the naive arg-order fix would compile while silently making the retry path unreachable; `reporting-api` imports the library but never calls `charge` → `unaffected`; `legacy-admin` pins `payments-lib` to `^1.2.0`, excluding the change → `unaffected` by version constraint alone. `fixtures/setup.sh` (re)creates/resets all five repos and the breaking-change PR on GitHub via `gh`, force-pushing fresh content each run so re-running is idempotent. Verified each consumer's `npm test` passes standalone against `payments-lib@1.2.0`, and `setup.sh`'s git logic (copy → commit → force-push, `v2/` overlay, `node_modules`/lockfile exclusion) against a mocked `gh` + local bare repos, run twice, produces no duplicate commits.
