#!/usr/bin/env bash
# Lesson step 6 and the first stretch: enforce the pinning policy for a whole organization, with the gh CLI.
#
#   usage:  DRY_RUN=1 scripts/org-policy.sh ORG       print the commands, change nothing
#           scripts/org-policy.sh ORG                 apply them (needs organization owner rights)
#
# 1. Actions must be pinned to a full-length commit SHA (a tag that moves is refused at run time).
# 2. Only the actions on allowed-actions.txt may run.
# 3. A ruleset makes the pin check a required workflow in every repository of the organization.
#
# Nothing here is run by `make` or CI, and it was not run while writing it: a personal account has no organization.
set -euo pipefail

org="${1:?usage: scripts/org-policy.sh ORG}"
root="$(cd "$(dirname "$0")/.." && pwd)"

if [[ ! "$org" =~ ^[A-Za-z0-9_.-]+$ ]]; then
  echo "org-policy: '$org' is not an organization name" >&2
  exit 2
fi

gh_api() {
  if [[ "${DRY_RUN:-0}" == "1" ]]; then
    printf 'gh api'
    printf ' %q' "$@"
    printf '\n'
  else
    gh api "$@"
  fi
}

echo "1. require full-length commit SHAs"
gh_api -X PUT "orgs/$org/actions/permissions" -f enabled_repositories=all -f allowed_actions=selected -F sha_pinning_required=true

echo "2. the allowed list"
patterns=()
while IFS= read -r line; do
  line="${line%%#*}"
  line="${line//[[:space:]]/}"
  [[ -n "$line" ]] && patterns+=(-f "patterns_allowed[]=$line@*")
done <"$root/allowed-actions.txt"
gh_api -X PUT "orgs/$org/actions/permissions/selected-actions" -F github_owned_allowed=false "${patterns[@]}"

echo "3. a ruleset that requires the pin-check workflow on every repository's default branch"
ruleset="$root/docs/org-ruleset.json"
if [[ "${DRY_RUN:-0}" == "1" ]]; then
  echo "gh api -X POST orgs/$org/rulesets --input $ruleset"
else
  gh api -X POST "orgs/$org/rulesets" --input "$ruleset"
fi
