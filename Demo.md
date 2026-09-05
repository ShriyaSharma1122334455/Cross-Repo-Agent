# Demo

Living document. Update it as things start working and as things break. At any point in the build it should describe **what actually runs today**, not what's planned.

## The one thing this demo must prove

> The agent distinguishes "imports it" from "actually breaks."

Everything else — the PR generation, the report formatting, the deployment — is supporting material. A judge who watches five minutes and takes away only that one idea has understood the project.

The corollary shapes the whole script: **the moments where the agent takes no action are the most important moments.** Anyone can flag every repo that imports a library. Clearing two repos with specific reasons is what a grep can't do.

## Fixtures

Four consumer repos, four verdicts, two of them "no action."

| Repo               | Setup                                               | Verdict                | What it proves                    |
| ------------------ | --------------------------------------------------- | ---------------------- | --------------------------------- |
| `checkout-service` | Calls `charge()` positionally, ignores return value | `mechanically_fixable` | The agent can fix and verify      |
| `billing-worker`   | Branches on old `null` return to trigger retry      | `needs_human`          | The agent knows when _not_ to act |
| `reporting-api`    | Imports the lib, only uses `formatAmount()`         | `unaffected`           | Beats grep                        |
| `legacy-admin`     | Pinned to `payments-lib@1.x`                        | `unaffected`           | Beats a dependency graph          |

**The provider PR changes one function in two ways at once:**

```
- charge(amount, currency, customer_id)   // returns null on failure
+ charge(amount, currency, customer)      // throws on failure
```

A signature change (mechanical) and a return-contract change (semantic) in a single diff. This is deliberate: it's what lets one PR produce two different verdicts on two different consumers, which is the entire argument of the project compressed into one change.

## Script (5:00)

### 0:00–0:40 — The problem

Not slides of bullet points. One sentence of setup, then the actual pain:

> "In a monorepo, if you break a caller, CI tells you before you merge. In a polyrepo — which is what most companies actually run — you change a shared library, announce it in Slack, and find out who you broke when their pager goes off."

Then the gap, stated precisely:

> "The tools that exist tell you who _imports_ your library. That's cheap to compute and mostly noise. Nobody tells you who _breaks_."

Show the PR diff on screen while saying it. Point out that it changes the signature _and_ the failure behavior — foreshadowing, and it takes four seconds.

### 0:40–1:00 — Trigger

PR opens. Agent starts. Don't narrate architecture here — no "and now it invokes the discovery tool." Just let it run and say what it's doing in human terms: "it's working out what changed, then finding everyone who depends on this."

### 1:00–2:15 — The clearing (the real opening argument)

This is the section most people would put last. Put it first.

Walk through both `unaffected` verdicts and read the agent's reasons off the screen:

- `reporting-api` — imports `payments-lib`, no call sites for `charge`, only uses `formatAmount()`
- `legacy-admin` — declares `^1.2.0`, change ships in `2.0`, will never receive it

Then say the line that lands:

> "A dependency graph flags both of these. So does grep. Two false alarms that a human would have had to chase down — and the agent has explained, with file and line, why neither one needs to be looked at."

Make sure the traces are visible on screen. Real paths, real line numbers.

### 2:15–3:15 — The fix

`checkout-service`. Show the verdict and trace, then the generated patch, then — this is the part to dwell on — the verification step: patch applied, `npm install`, tests pass, _then_ the PR opens.

> "It doesn't open a PR because it thinks the fix is right. It opens a PR because it ran the tests."

Show the actual PR on GitHub. Real artifacts sell hard; a screenshot of a real PR beats any amount of terminal output.

### 3:15–4:15 — The refusal (the strongest moment)

`billing-worker`. Slow down here.

Show the call site: line 47 branches on `charge()` returning null to trigger a retry. Show the agent's reasoning:

> "This consumer depends on the old null-return contract for retry logic. The new version throws instead, so the retry path becomes unreachable and failures propagate uncaught. A mechanical signature fix would compile cleanly and silently break error handling."

Then the point:

> "It could have fixed the signature here. The transformation is obvious. It refused — because the obvious fix would compile, pass a lazy review, and break error handling in production. It filed an issue for the code owner instead."

An agent that knows the limits of its own confidence is a more sophisticated artifact than one that fixes everything, and this is the thirty seconds where that's visible.

### 4:15–4:45 — The report

One comment on the provider PR: 2 affected, 1 auto-fixed with a link, 1 escalated with a link, 2 cleared with reasons. Author reads one comment, understands the whole blast radius, doesn't open another tab.

Then state the boundary explicitly:

> "It never merges. Everything here is a proposal waiting on a human."

### 4:45–5:00 — Close

What it generalizes to — deprecations, internal API migrations, shared library upgrades at polyrepo scale — and then, briefly, what's real:

> "Real GitHub API, real repos, real PRs. The consumer repos are purpose-built fixtures, not a production codebase."

Say it plainly. Volunteering the boundary reads as confidence; being caught at it reads as overselling.

## Pacing notes

**Timing is tight and the temptation is to cut the clearing section.** Don't. Cut the close, cut the generalization, cut the architecture explanation — but the two `unaffected` verdicts are the differentiator and they get their 75 seconds.

**Never explain the architecture on camera.** No "single agent with tools, here's the loop." Judges have the README and the diagram. Airtime spent on architecture is airtime not spent on judgment.

**Don't say "AI" or "LLM" more than once.** Say what it did: it read the call site, it saw the retry branch, it refused to patch. The reasoning is the impressive part; the fact that a model is involved is not.

## Fallback paths

Ordered by how much you lose. Know which tier you're on before you press record.

**Tier 0 — everything live.** Webhook fires, agent runs, PR appears in real time.
_Risk:_ webhook latency, rate limits, model latency, network. Highest risk of the four.

**Tier 1 — manual trigger, live run.** Skip the webhook, `POST /analyze` directly. Removes the least reliable dependency and costs you nothing narratively — no judge cares whether a webhook fired.
**This should be the default.** Tier 0 is a flex, not a requirement.

**Tier 2 — replayed run.** `scripts/replay.py` against cached model responses. Everything real except the model calls; PRs and issues already exist and are shown live on GitHub. Fast, deterministic, still shows real artifacts. Perfectly respectable if you say what you're doing.

**Tier 3 — recorded run with live narration.** Pre-recorded terminal + GitHub walkthrough, narrated over. For the submitted video this is fine and arguably better — it's five minutes of your best take instead of five minutes of luck.

**Never do:** mocked output, fake PR screenshots, or a "simulated" run presented as live. If a judge asks "is that a real PR?" the answer must be yes.

## Recording checklist

- [ ] Fixtures reset to clean state (`fixtures/setup.sh`) — no leftover PRs from testing
- [ ] Provider PR closed and reopened, or a fresh one created
- [ ] Idempotency state cleared for these fixtures
- [ ] Terminal font large enough to read on a laptop
- [ ] Browser zoom set so PR diffs and traces are legible
- [ ] Notifications off, tabs closed
- [ ] Cached responses warm if running Tier 2
- [ ] Under 5:00 with 15 seconds of slack
- [ ] Watched once at full size with the sound on

## Update log

Keep this current. It's how you know what your demo actually is at any moment.

| Date | Working end-to-end | Demo tier | Notes |
| ---- | ------------------ | --------- | ----- |
|      |                    |           |       |
