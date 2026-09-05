#!/usr/bin/env bash
# Creates (or resets) the five demo fixture repos on GitHub and opens the
# breaking-change PR on payments-lib. Safe to re-run: each repo's content is
# rebuilt from this directory and force-pushed, so re-running always leaves
# the repos in exactly the state described in fixtures/README.md.
#
# Requires: `gh` CLI, authenticated, with repo-create scope in $TARGET_ORG.
#
# Usage: TARGET_ORG=my-org fixtures/setup.sh

set -euo pipefail

FIXTURES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_ORG="${TARGET_ORG:?TARGET_ORG env var is required (e.g. TARGET_ORG=my-org fixtures/setup.sh)}"
VISIBILITY="${FIXTURE_REPO_VISIBILITY:-private}"
REMOTE_URL_BASE="${FIXTURE_REMOTE_URL_BASE:-https://github.com}"

CONSUMER_REPOS=(checkout-service billing-worker reporting-api legacy-admin)
PROVIDER_REPO=payments-lib

log() { printf '==> %s\n' "$*"; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "error: '$1' is required but not on PATH" >&2
    exit 1
  }
}

require_cmd gh
require_cmd git

# Pushes $src_dir as the sole content of $branch on $TARGET_ORG/$repo,
# creating the repo first if it doesn't exist. Force-pushes so re-running
# always resets history and content, never accumulates stale commits.
push_repo_branch() {
  local repo="$1" branch="$2" src_dir="$3" commit_message="$4"

  local work_dir
  work_dir="$(mktemp -d)"
  trap 'rm -rf "$work_dir"' RETURN

  cp -r "$src_dir"/. "$work_dir"/
  rm -rf "$work_dir/v2" # payments-lib's v2/ overlay dir must never ship as-is
  rm -rf "$work_dir/node_modules" "$work_dir/package-lock.json" # never ship a dev's local install

  git -C "$work_dir" init -q -b "$branch"
  git -C "$work_dir" add -A
  git -C "$work_dir" -c user.name="blast-radius-fixtures" \
    -c user.email="fixtures@blast-radius.invalid" \
    commit -q -m "$commit_message"

  if gh repo view "$TARGET_ORG/$repo" >/dev/null 2>&1; then
    log "repo $TARGET_ORG/$repo exists, resetting $branch"
  else
    log "creating $TARGET_ORG/$repo"
    gh repo create "$TARGET_ORG/$repo" --"$VISIBILITY" >/dev/null
  fi

  git -C "$work_dir" remote add origin "$REMOTE_URL_BASE/$TARGET_ORG/$repo.git"
  git -C "$work_dir" push --force origin "$branch"
}

log "resetting provider repo: $PROVIDER_REPO"
push_repo_branch "$PROVIDER_REPO" main "$FIXTURES_DIR/$PROVIDER_REPO" \
  "payments-lib 1.2.0 (pre-change baseline)"

# The breaking-change branch is the v1 tree with v2/'s files overlaid on top.
v2_work_dir="$(mktemp -d)"
trap 'rm -rf "$v2_work_dir"' EXIT
cp -r "$FIXTURES_DIR/$PROVIDER_REPO"/. "$v2_work_dir"/
rm -rf "$v2_work_dir/v2"
cp -r "$FIXTURES_DIR/$PROVIDER_REPO/v2"/. "$v2_work_dir"/
push_repo_branch "$PROVIDER_REPO" breaking-change-v2 "$v2_work_dir" \
  "payments-lib 2.0.0: charge() argument order + throws on decline"
rm -rf "$v2_work_dir"

log "opening/updating breaking-change PR on $PROVIDER_REPO"
existing_pr="$(gh pr list --repo "$TARGET_ORG/$PROVIDER_REPO" \
  --head breaking-change-v2 --state open --json number --jq '.[0].number // empty' || true)"
if [ -n "$existing_pr" ]; then
  log "PR #$existing_pr already open for breaking-change-v2, leaving it as-is"
else
  gh pr create --repo "$TARGET_ORG/$PROVIDER_REPO" \
    --base main --head breaking-change-v2 \
    --title "charge(): reorder arguments, throw on decline instead of returning null" \
    --body "Two changes to \`charge()\`: argument order becomes (amount, cardToken), and a declined charge now throws \`PaymentDeclinedError\` instead of resolving \`null\`. See fixtures/README.md in blast-radius-agent for what each consumer's expected verdict is." \
    >/dev/null
fi

for repo in "${CONSUMER_REPOS[@]}"; do
  log "resetting consumer repo: $repo"
  push_repo_branch "$repo" main "$FIXTURES_DIR/$repo" \
    "$repo fixture: initial state"
done

log "done. Provider PR: $REMOTE_URL_BASE/$TARGET_ORG/$PROVIDER_REPO/pulls"
