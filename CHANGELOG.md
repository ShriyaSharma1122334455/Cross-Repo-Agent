# Changelog

All notable changes to this project are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- `CLAUDE.md` — guidance for Claude Code, summarizing architecture, tech stack, and scope from `context/`.
- `README.md` — project overview.
- `.gitignore` — excludes `context/`, Python artifacts, env/secrets, local state, and OS/editor files.
- `tasks.md` — ordered build tickets derived from `context/spec.md`, `architecture.md`, and `agents.md`.
- `testing.md` — eval set and per-task-type definition of done.
- Changelog-maintenance instructions in `CLAUDE.md`.
- `CHANGELOG.md`.
- T01: project skeleton — `pyproject.toml`, `.env.example`, `docker-compose.yml` (agent + dynamodb-local stub), `src/blast_radius/__init__.py`. Verified `pip install -e .`, `import blast_radius`, and `pytest` (0 tests) all succeed.
- T02: `src/blast_radius/config.py` — `Config` dataclass loading from env, with required vars (`GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY_PATH`, `GITHUB_WEBHOOK_SECRET`, `TARGET_ORG`) raising `ConfigError` when missing, and defaults for model tiers, AWS region, confidence threshold, and state backend.
- T03: `src/blast_radius/models/` — plain dataclasses for `ChangeContract`/`SymbolChange` (`change.py`), `ConsumerCandidate`/`CallSite` (`consumer.py`), `Verdict`/`ReasoningTrace`/`Citation`/`Confidence` (`verdict.py`), and `RunResults`/`ConsumerResult`/`ActionRecord` (`run.py`). All frozen, stdlib-only imports (`dataclasses`, `enum`), no I/O. Verified every model constructs, is immutable, and the package has zero imports from `tools/`, `github/`, `state/`, or a model client.
