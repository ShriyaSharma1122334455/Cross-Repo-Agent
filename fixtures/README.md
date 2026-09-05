# Fixtures

Five repos: one provider, four consumers. Together they prove the agent
reaches all three verdicts correctly, and reaches `unaffected` for two
different reasons (no call sites vs. version constraint).

The scenario: `payments-lib` ships a PR that changes `charge()` in two ways
at once — exactly the "one symbol, two kinds of change" case
`context/agents.md` calls out as the good Phase 1 behavior:

1. **Signature (mechanical):** argument order changes from
   `charge(cardToken, amount)` to `charge(amount, cardToken)`.
2. **Return contract (semantic):** a declined charge used to resolve `null`;
   it now throws `PaymentDeclinedError`.

`payments-lib`'s `main` branch holds the pre-change (`1.2.0`) code that every
consumer below is written against. `setup.sh` opens a PR from a
`breaking-change-v2` branch (the `2.0.0` code in `payments-lib/v2/`) into
`main` — that PR is what the agent is pointed at for the demo.

## payments-lib (provider)

The shared library. `index.js` / `package.json` at the repo root are the
`1.2.0` state (`main`). `v2/index.js` / `v2/package.json` are the `2.0.0`
state that `setup.sh` pushes to `breaking-change-v2` and opens as a PR.

## checkout-service → `mechanically_fixable`

Calls `charge(cart.cardToken, cart.totalCents)` and uses `result.id`
directly — it never branches on a `null` return, so the null-vs-throw change
doesn't touch its logic. The only thing that breaks it is the argument
order, which is a pure, verifiable, deterministic transformation: swap the
two arguments at the call site. `src/checkout.js:8`.

## billing-worker → `needs_human`

Calls `charge(invoice.cardToken, invoice.amountCents)` and branches on
`result === null` to decide whether to schedule a retry (`src/settle.js:12`).
This repo needs the same argument-order fix as `checkout-service`, but a
mechanical fix that stops there would compile and pass a naive smoke test
while silently breaking the retry path: under `2.0.0`, a decline throws
instead of returning `null`, so the `retryQueue.scheduleRetry` branch
becomes unreachable and a declined charge now propagates as an uncaught
exception instead of queuing for retry. This is the spec's canonical
"mechanical fix would compile but change behavior" case — it must be
flagged for a human, not auto-fixed.

## reporting-api → `unaffected` (imports, never calls)

Imports only `getTransactionHistory` from `payments-lib`
(`src/history.js:1`) and never references `charge`. `get_call_sites` for
`charge` against this repo returns `[]`; the agent must still state a reason
("imports the package but has no call sites for `charge`"), not just
silently omit the repo.

## legacy-admin → `unaffected` (version constraint)

Declares `"payments-lib": "^1.2.0"` in `package.json`, which excludes
`2.0.0`. This repo does call `charge()` with the pre-2.0 argument order
(`src/refund.js:8`), but that's irrelevant to the verdict — `find_consumers`
/ `check_version_constraint` must clear it in Phase 2, before any of its
code is read. If the agent ever opens `src/refund.js` to reach this
verdict, that's a bug in phase ordering, not a feature.

## Running these locally

Each consumer's `package.json` declares `payments-lib` by plain semver range
(no private registry involved in this demo). To run a consumer's own test
suite locally against a given `payments-lib` state:

```sh
cd fixtures/payments-lib && npm install && npm link
cd ../checkout-service && npm link payments-lib && npm test
```

`setup.sh` doesn't do this step — it only creates/resets the GitHub repos
and the demo PR. Local linking is a dev convenience for running a
consumer's tests by hand outside the verification container.
