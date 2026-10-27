#!/usr/bin/env bash
# Lesson step 5, locally: move the v1 tag to a changed commit and see who notices.
#
# Works on a throwaway clone, so this repository's tags are never touched. A consumer that calls the shared workflow
# by the tag `@v1` runs the changed code on its next run without changing anything itself; a consumer that calls it
# by the full commit of v1.0.0 does not. Exits 0 only when exactly that happens.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
marker="THIS CODE WAS CHANGED AFTER RELEASE"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

git clone -q --no-hardlinks "$root" "$work/platform-ci"
original="$(git -C "$work/platform-ci" rev-parse 'v1.0.0^{commit}')"

# The "malicious" commit: one extra step in the reusable workflow, based on the released commit.
cd "$work/platform-ci"
git checkout -q --detach "$original"
python3 - "$marker" <<'PY'
import pathlib, sys
path = pathlib.Path(".github/workflows/build-test.yml")
text = path.read_text(encoding="utf-8")
anchor = "      - name: List the secret names this workflow can read\n"
step = f'      - run: echo "{sys.argv[1]}"\n'
path.write_text(text.replace(anchor, step + anchor, 1), encoding="utf-8")
PY
git -c user.name=attacker -c user.email=attacker@example.invalid commit -q -am "ci: an extra step"
git tag -f -a v1 -m "moved" >/dev/null
echo "v1 was ${original:0:12}, now points to $(git rev-parse --short=12 'v1^{commit}')"

sed "s/ORIGINAL_COMMIT/$original/" "$root/demo/consumer-on-commit.yml" >"$work/on-commit.yml"
cp "$root/demo/consumer-on-tag.yml" "$work/on-tag.yml"

cd "$root"
export PLATFORM_GIT="$work/platform-ci"
echo "== svc-orders, calling the shared workflow by the tag @v1"
scripts/run_consumer.sh svc-orders "$work/on-tag.yml" >"$work/tag.log" 2>&1 || { cat "$work/tag.log"; exit 1; }
echo "== svc-search, calling the shared workflow by the full commit of v1.0.0"
scripts/run_consumer.sh svc-search "$work/on-commit.yml" >"$work/commit.log" 2>&1 || { cat "$work/commit.log"; exit 1; }

echo
echo "-- by tag, lines containing the marker:"
grep -- "$marker" "$work/tag.log" | sed 's/^/   /' || true
echo "-- by commit, lines containing the marker:"
grep -- "$marker" "$work/commit.log" | sed 's/^/   /' || true

if grep -q -- "$marker" "$work/tag.log" && ! grep -q -- "$marker" "$work/commit.log"; then
  echo "RESULT: the consumer on @v1 ran the changed code; the consumer on the commit did not."
else
  echo "RESULT: unexpected, see the logs above" >&2
  exit 1
fi
