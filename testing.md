# Testing

Two things live here: a small eval set that exercises the judgment described in `context/agents.md` (Phase 3's "good/bad" examples and the failure modes list), and a definition of "done" per task *type* in `tasks.md`, so tickets aren't marked complete on vibes.

## Eval set

Each case is a `(SymbolChange, list[CallSite])` pair fed to `analyze_usage`, or a full pipeline run where noted. Expected behavior is checked against the rules in `context/agents.md`'s system prompt, not just the final verdict label — a right verdict with a fabricated or missing reason still fails.

### E1 — Clean mechanical break
**Input:** `charge(amount)` → `charge(amount, currency)`, required new param. Call site: `checkout-service`, one call, `charge(total)`.
**Expected:** `mechanically_fixable`. Trace cites the actual file:line and states the missing argument specifically (not "signature changed").
**Guards against:** vague or generic reasoning that would apply to any signature change.

### E2 — Semantic break disguised as mechanical
**Input:** `charge()` return contract changes from `returns null on failure` to `throws PaymentError`. Call site: `billing-worker`, branches on `null` to trigger a retry.
**Expected:** `needs_human`. Trace names the retry branch specifically and states what a naive try/catch-wrapping fix would get wrong (swallowing the error rather than retrying).
**Guards against:** auto-fixing a semantic break because the signature stayed compatible (failure mode #3, over-fixing).

### E3 — Import without usage
**Input:** `charge()` signature change. Consumer `reporting-api` imports `payments-lib` but has zero call sites for `charge`.
**Expected:** `unaffected`, with the stated reason "imports the package but has no call sites for `charge`" (or equivalent) — not a bare "unaffected" with no reason. `analyze_usage` is not called at all (empty call-site list short-circuits before the model).
**Guards against:** treating "imports" as "affected" (the exact grep-with-LLM failure the project exists to avoid); also checks the empty-list-is-meaningful path from `context/agents.md`.

### E4 — Version-pinned clearance
**Input:** `charge()` change ships in `2.0`. Consumer `legacy-admin` declares `^1.x`.
**Expected:** `unaffected`, decided in Phase 2 (`check_version_constraint`) — the repo's code is never fetched, `get_call_sites` is never invoked for it.
**Guards against:** wasting a code read (and model call) on a repo that was decidable from the manifest alone; ordering violation from `context/architecture.md`'s Phase 2.

### E5 — Two changes on one symbol
**Input:** `charge()` changes both signature (new required param) and return contract (null → throw) in the same PR.
**Expected:** `extract_change_contract` produces two `SymbolChange` entries for `charge`, kind `signature` and `return_contract`. Downstream, a consumer touching only the signature-relevant part still gets evaluated against both.
**Guards against:** collapsing a dual-kind change into one, which is explicitly called out as a "Phase 1 — good" behavior in `context/agents.md`.

### E6 — Low-confidence downgrade
**Input:** A call site where usage is ambiguous (e.g. call site behind a thin local wrapper, so args aren't directly visible) such that the model's own stated confidence on `mechanically_fixable` is low.
**Expected:** Verdict downgrades to `needs_human` regardless of the model's initial lean. Trace states the ambiguity as the reason, not the underlying break.
**Guards against:** "the agent may be unsure but may not act while unsure" (rule 5 in the system prompt) being silently skipped.

### E7 — Partial-fix aggregation
**Input:** One consumer, four call sites for the same changed symbol: three cleanly `mechanically_fixable`, one `needs_human`.
**Expected:** Repo-level verdict is `needs_human` (most severe wins). The agent does not open a PR fixing the three and ignoring the fourth.
**Guards against:** failure mode #4, partial fixes — "a partial fix is worse than no fix."

### E8 — Verification failure downgrade
**Input:** A `mechanically_fixable` verdict whose generated patch, when run through `verify_patch`, fails `npm test` (simulate by fixture with a test that the naive patch doesn't satisfy).
**Expected:** Verdict downgrades to `needs_human`, an issue is filed instead of a PR, and the issue/report explains that an automated fix was attempted and failed verification — not silently retried forever or opened anyway.
**Guards against:** opening a PR that doesn't build (`context/architecture.md`, "Verification is a gate, not a formality").

### E9 — Idempotent re-run
**Input:** Run the pipeline twice against the same provider PR and consumer state, with no changes between runs.
**Expected:** Second run produces the same verdicts, updates the existing PR/issue/report comment (by action-state key) rather than creating duplicates, and — if dev cache is enabled — makes zero new model calls.
**Guards against:** failure mode #5, duplicate artifacts; also validates the `change_contract_hash` distinguishes "re-analyzed, unchanged" from "changed."

### E10 — Ungrounded-trace canary (adversarial, run against the harness itself)
**Input:** Deliberately tamper with a `CallSite`'s line number after retrieval but before the model call (test harness only), or ask a mocked model to cite a line one past the file's actual length.
**Expected:** `tests/grounding/test_trace_line_refs.py` fails loudly and blocks the run/merge. This case exists to prove the grounding tests actually catch the failure they claim to catch, not just that they pass on well-behaved input.
**Guards against:** failure mode #1, ungrounded traces — "the project-killing failure." If this canary doesn't fail when tampered, the grounding tests are theater.

---

## Definition of "done" by task type

`tasks.md` tickets fall into a handful of shapes. Use the matching bar below in addition to each ticket's own acceptance criteria — a ticket isn't done just because its stated acceptance criteria pass if it also fails the bar for its type.

### Data model tickets (e.g. T03)
- No logic, no I/O, no imports from `tools/`, `github/`, `state/`, or any model client.
- Every field named in `context/architecture.md`/`context/agents.md` for that object exists with the documented type.
- Constructible in a one-line test with no mocking required.

### Deterministic tool tickets (e.g. T05 parsing, T12 version check)
- Zero model calls — verified by an explicit "no model client imported" test, not just code review.
- Empty/no-match input returns an empty/negative result, not an exception (empty is a meaningful result per `context/agents.md`).
- Same input always produces the same output (no network, no randomness) unless the tool is explicitly a GitHub API call, in which case failures are typed and distinguishable from empty results.

### Model-call tool tickets (e.g. T10 extract_change_contract, T14 analyze_usage, T29 generate_patch)
- Runs against every relevant eval case above (E1–E9 as applicable) with the expected verdict/output.
- Every output field that claims evidence (file, line, snippet) is traceable to an actual input object — checked by a grounding test, not eyeballed.
- Uses the correct model tier per `context/tech-stack.md` (cheap for extraction, strong for usage/patch) — a ticket using the wrong tier is not done regardless of output quality.
- Confidence/uncertainty is surfaced, not hidden — a low-confidence case (E6) demonstrably downgrades.

### State/idempotency tickets (e.g. T20–T23)
- Running the same operation twice with the same key never creates a second record — proven by a test that asserts count, not just "looks right."
- Distinguishes "same change, re-analyzed" from "change itself moved" via `change_contract_hash`.
- Backend-swap tests (SQLite vs. DynamoDB, if both exist for a ticket) run the identical test suite against both.

### GitHub write tickets (e.g. T24, T26, T31)
- Idempotency check happens before every write, not after — a test that calls the tool twice and asserts only one artifact exists, checked before checking content correctness.
- Failure paths (rate limit, permission error) are retried with backoff and then reported, never silently swallowed.
- Content of the write (PR body, issue body, report comment) includes the reasoning trace's evidence, not a generic message.

### Verification tickets (T27, T28)
- No credentials present in the container at runtime — checked by inspection, not assumed from the Dockerfile alone.
- A known-good patch verifies green; a known-bad patch verifies red without crashing the caller.
- A verification failure is handled as a downgrade path (E8), not surfaced as an unhandled exception.

### Report/orchestration tickets (T30–T34)
- End-to-end run against the fixtures (T11) produces the four expected verdicts in one pass, matching `context/spec.md`'s "What working looks like."
- Cleared (`unaffected`) consumers appear in the report with reasons — omission is a failure, per `context/agents.md`'s "Phase 5 — bad."
- Re-running updates prior artifacts (E9) rather than duplicating them.

### Test tickets themselves (T06, T16–T19, T23, T37)
- A test ticket is only done if it can be shown to fail on bad input, not just pass on good input (see E10's canary requirement) — write the tampered/broken case, confirm the test catches it, then revert to the clean case before merging.
- Grounding tests (T18, T19) are treated as release-blocking: a failure here blocks merging changes to `analyze_usage` or `get_call_sites`, full stop.

### Deploy/infra tickets (T35, T36)
- Runs the same fixture PR through the deployed path (or documented fallback) and produces the same verdicts as the local path — deployment is not done if it changes behavior.
- Billing alarm and no-credential container checks are verified live at least once, not just declared in config.

---

## Explicitly not covered by this eval set

Per `context/spec.md`'s scope, this eval set does not include: multi-language cases, transitive (indirect) dependency breaks, detecting independently-fixed consumers, or multi-repo/multi-PR runs. Adding eval cases for any of these should prompt a scope check against `context/spec.md` first, same as adding tickets to `tasks.md`.
