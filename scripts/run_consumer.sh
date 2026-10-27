#!/usr/bin/env bash
# Run a consumer's CI locally with act, against the platform commits GitHub would pick.
#
# The consumer's workflow says `uses: sumitsr/platform-ci/.github/workflows/build-test.yml@v1` (or a full SHA).
# GitHub resolves that ref when the run starts; this script resolves it the same way in this repository's git history
# (pipeline/platform_refs.py), unpacks each commit with `git archive`, and tells act to use those folders instead of
# cloning from github.com (act's --local-repository).
#
# usage: scripts/run_consumer.sh SERVICE [WORKFLOW_FILE] [extra act arguments...]
#   PLATFORM_GIT=/path/to/clone  resolve refs in another clone (the moved-tag demo does this)
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
platform="${PLATFORM_REPO:-sumitsr/platform-ci}"
service="${1:?usage: scripts/run_consumer.sh SERVICE [WORKFLOW_FILE] [act arguments...]}"
workflow="${2:-$root/consumers/$service/.github/workflows/ci.yml}"
workflow="$(cd "$(dirname "$workflow")" && pwd)/$(basename "$workflow")"
repo="${PLATFORM_GIT:-$root}"
python="${PYTHON:-$root/.venv/bin/python}"
checkouts="$root/build/platform"
flags=()

while IFS=$'\t' read -r ref commit kind path; do
  dir="$checkouts/$commit"
  if [[ ! -d "$dir" ]]; then
    mkdir -p "$dir"
    git -C "$repo" archive "$commit" | tar -x -C "$dir"
  fi
  flags+=(--local-repository "$platform@$ref=$dir")
  echo "resolved ${path#"$platform"/}@${ref:0:12} -> ${commit:0:12} ($kind)"
done < <("$python" -m pipeline.platform_refs "$workflow" --platform "$platform" --repo "$repo")

flags+=(--concurrent-jobs 1)

# Run from the repository root so act reads .actrc (the runner image), with the consumer's folder as its workspace.
exec act push -C "consumers/$service" -W "$workflow" "${flags[@]}" "${@:3}"
