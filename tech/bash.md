# Bash

## What it is

Bash is a **shell**: a program that reads commands and runs them. A file of commands is a **shell script**. Bash is the normal shell on Linux and macOS, and GitHub's runners (including Windows ones, through Git Bash) have it, so workflow steps here set `shell: bash`.

<!-- words -->

<details>
<summary><b>Words this note uses, in case they are new to you</b> (click to open)</summary>

- **environment variable**: A named piece of text that is handed to a program by whoever starts it, for example `HOME` or `CI`. Programs read them to learn about the setting they run in.
- **stream**: A flow of data that is written or read piece by piece, such as the text a program prints.
- **regular expression**: A compact pattern that describes text, such as `^[0-9]{12}$` (exactly twelve digits). Tools use them to find or check text. Often shortened to **regex**.
- **checksum**: A short fingerprint computed from a file's content. If one byte changes the fingerprint changes, so comparing fingerprints shows whether a file is the one you expected.
- **SHA**: A family of hash functions. A Git **commit SHA** is a 40-character hexadecimal fingerprint that names one exact commit.
- **commit**: A saved snapshot of a project's files in Git, with a message and an author. Every commit has a unique 40-character name (its SHA).
- **branch**: A movable name for a line of commits in Git. `main` is the usual name of the primary line.
- **tag**: A name attached to a commit in Git, usually a version such as `v1.0.0`. Unlike a commit's SHA, a tag can be moved to another commit.
- **workflow**: A GitHub Actions automation described in a YAML file under `.github/workflows/`. It names the events that start it and the jobs it runs.
- **CI**: Continuous integration: running checks (build, tests, linters) automatically every time code changes.
- **HTTP**: The protocol (agreed rules) that web browsers and servers use to talk. A request names a **method** (`GET` to read, `POST` to create, `PATCH` to change part, `PUT` to replace, `DELETE` to remove) and an address; the answer carries a **status code** (200 means success, 404 not found, 500 server problem).
- **JSON**: A plain-text format for structured data: objects `{ "name": "value" }`, lists `[1, 2]`, texts in double quotes, numbers, `true`, `false`, `null`. It has no comments.
- **Docker**: A tool that builds images and runs containers.
- **array**: An ordered list of values.
- **list**: An ordered collection of values written one after another.
- **string**: A piece of text in a program.
- **folder**: A container for files and other folders on disk (also called a directory).
- **version**: A number such as `1.2.3` that names one release of software (major.minor.patch).
- **dictionary**: A Python mapping from keys to values, written `{"key": value}`.

</details>

<!-- /words -->

## Why this repository uses it

Most logic in this repository is in small scripts and in workflow `run:` blocks: validating the action's input, running a consumer locally, demonstrating a moved tag, and applying organization policy. ShellCheck (see `shellcheck.md`) keeps them honest.

## Where it appears

| Path | What it does with Bash |
| --- | --- |
| `.github/actions/setup-toolchain/validate-inputs.sh` | Rejects a bad Python version with an error that names the input. |
| `scripts/run_consumer.sh` | Resolves the platform refs, unpacks the commits, runs `act` against them. |
| `scripts/demo_moved_tag.sh` | The lesson's step 5 on a throwaway clone. |
| `scripts/org-policy.sh` | The organization pin policy as `gh api` calls, with a dry-run mode. |
| `scripts/install-actionlint.sh` | Downloads and verifies a pinned `actionlint` for CI. |
| `.github/workflows/pin-check.yml` | A `run:` block of Bash that greps every `uses:`. |
| `Makefile` | Recipes are shell commands. |

## How it works underneath

The first line `#!/usr/bin/env bash` (the **shebang**) tells the operating system which program runs the file. Bash reads line by line. Each command is a **process** that ends with an **exit code**: 0 is success, anything else is failure, and `$?` holds the last one. A **pipe** `a | b` sends the output of `a` into `b`. **Standard output** carries results, **standard error** carries messages; `>` redirects a stream to a file, `2>&1` joins error to output. Always quote variables (`"$x"`) so spaces do not split them.

## Walkthrough of this repository's use

### Safety line

```bash
set -euo pipefail
```

`-e` stops at the first failing command, `-u` makes using an unset variable an error, `-o pipefail` makes a pipeline fail if any part fails. Every script starts with it, except the inline `pin-check` block, which uses `set -uo pipefail` because it inspects failures itself.

### `validate-inputs.sh`

```bash
version="${INPUT_PYTHON_VERSION:-}"
requirements="${INPUT_REQUIREMENTS_FILE:-}"

if [[ ! "$version" =~ ^3\.[0-9]{1,2}(\.[0-9]{1,2})?$ ]]; then
  echo "::error title=setup-toolchain::python-version must look like 3.12 or 3.12.7, got '${version}'"
  exit 1
fi
```

`${NAME:-}` is the value of `NAME`, or empty text if unset (needed under `-u`). `[[ ... =~ REGEX ]]` tests a regular expression: `3`, a dot, one or two digits, optionally another dot and one or two digits. `::error title=...::message` is a GitHub **workflow command**: printing it makes the log show a red annotation. The action sets the two variables from `inputs.*` through `env:` rather than pasting them into the script, so the strings `"3.12; rm -rf /"` or `"$(id)"` stay text and fail the pattern.

### `run_consumer.sh`

```bash
root="$(cd "$(dirname "$0")/.." && pwd)"
platform="${PLATFORM_REPO:-sumitsr/platform-ci}"
service="${1:?usage: scripts/run_consumer.sh SERVICE [WORKFLOW_FILE] [act arguments...]}"
workflow="${2:-$root/consumers/$service/.github/workflows/ci.yml}"
workflow="$(cd "$(dirname "$workflow")" && pwd)/$(basename "$workflow")"
```

`$0` is the script path; `dirname` its folder; `cd ... && pwd` turns it into an absolute path. `${1:?message}` stops with the message if the first argument is missing. `${2:-default}` uses a default. The last line makes the workflow path absolute even if the caller gave a relative one.

```bash
while IFS=$'\t' read -r ref commit kind path; do
  dir="$checkouts/$commit"
  if [[ ! -d "$dir" ]]; then
    mkdir -p "$dir"
    git -C "$repo" archive "$commit" | tar -x -C "$dir"
  fi
  flags+=(--local-repository "$platform@$ref=$dir")
  echo "resolved ${path#"$platform"/}@${ref:0:12} -> ${commit:0:12} ($kind)"
done < <("$python" -m pipeline.platform_refs "$workflow" --platform "$platform" --repo "$repo")
```

`read -r` reads one line and splits it on the separator in `IFS` (a tab) into four variables. `done < <(command)` feeds the loop with the command's output (a **process substitution**), which keeps the loop in the current shell so `flags` survives. `[[ ! -d "$dir" ]]` tests that a directory does not exist. `flags+=(...)` appends to an array. `${path#"$platform"/}` removes the shortest matching prefix; `${ref:0:12}` is the first twelve characters.

```bash
log="$(mktemp)"
trap 'rm -f "$log"' EXIT
if act push -C "consumers/$service" -W "$workflow" "${flags[@]}" "${@:3}" 2>&1 | tee "$log"; then
  exit 0
fi
if grep -q "Job succeeded" "$log" && ! grep -q "Job failed" "$log"; then
  exit 0
fi
exit 1
```

`mktemp` makes a unique temporary file; `trap ... EXIT` removes it however the script ends. `"${@:3}"` expands every argument from the third on. `tee` copies output to the screen and to the log. A busy Docker daemon can make `act` exit with an error after a job already succeeded, so the log is checked.

### `demo_moved_tag.sh`

```bash
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
...
python3 - "$marker" <<'PY'
import pathlib, sys
...
PY
```

`mktemp -d` makes a temporary folder. `python3 - "$marker" <<'PY' ... PY` runs Python code written inline (a **here-document**: everything up to the line `PY` is fed to the program's input; quoting `'PY'` stops Bash from expanding `$` inside). The script ends by exiting non-zero unless the `@v1` log contains the marker and the commit-pinned log does not:

```bash
if grep -q -- "$marker" "$work/tag.log" && ! grep -q -- "$marker" "$work/commit.log"; then
```

`--` ends option parsing so a marker starting with `-` would not be taken as a flag.

### `org-policy.sh`

```bash
gh_api() {
  if [[ "${DRY_RUN:-0}" == "1" ]]; then
    printf 'gh api'
    printf ' %q' "$@"
    printf '\n'
  else
    gh api "$@"
  fi
}
```

A **function**. With `DRY_RUN=1` it prints the command (`%q` shell-quotes each argument) instead of running it. `"$@"` is all the arguments, each kept whole.

```bash
while IFS= read -r line; do
  line="${line%%#*}"
  line="${line//[[:space:]]/}"
  [[ -n "$line" ]] && patterns+=(-f "patterns_allowed[]=$line@*")
done <"$root/allowed-actions.txt"
```

Reads the allowed list line by line: `${line%%#*}` strips a comment, `${line//[[:space:]]/}` deletes all whitespace, blank lines are skipped, and the rest become `-f patterns_allowed[]=...` options.

### `install-actionlint.sh`

The installer uses these pieces: `declare -A` for checksums by platform, `case "$(uname -s)-$(uname -m)"` to choose the download, `curl --fail --silent --show-error --location --retry 3`, `sha256sum --check --status`, and `trap` to delete the archive. A wrong checksum aborts before anything is unpacked.

### The inline `pin-check` script

```bash
bad=$(grep -nE '^[[:space:]-]*uses:' $files \
  | grep -vE 'uses:[[:space:]]*"?(\./|docker://[^[:space:]]+@sha256:[0-9a-f]{64})' \
  | grep -vE 'uses:[[:space:]]*"?[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+@[0-9a-f]{40}("|[[:space:]]|$)' || true)
```

First `grep -nE` lists every `uses:` line with its line number. Each `grep -v` removes lines that are acceptable: local paths and digest-pinned images, then references that end in `@` plus exactly 40 hex characters. What is left is the offenders. `|| true` keeps `set -e` from stopping when nothing is left. `$files` is left unquoted on purpose so it splits into file names (the `# shellcheck disable=SC2086` line above it says so).

<!-- walk:.github/actions/setup-toolchain/validate-inputs.sh -->
### `.github/actions/setup-toolchain/validate-inputs.sh`, line by line

Lines 1 to 7:

```bash
#!/usr/bin/env bash
# Fail early, with a message that names the input, when the action is given a version it cannot install.

# Reads INPUT_PYTHON_VERSION and INPUT_REQUIREMENTS_FILE from the environment (set by action.yml).

set -euo pipefail

version="${INPUT_PYTHON_VERSION:-}"
requirements="${INPUT_REQUIREMENTS_FILE:-}"
```

Shebang, comments and `set -euo pipefail` (stop on error, unset variable is an error, a pipeline fails if any part fails). `version="${INPUT_PYTHON_VERSION:-}"` reads the environment variable, or the empty text if it is unset (`${name:-default}` with an empty default).

Lines 9 to 19:

```bash
if [[ ! "$version" =~ ^3\.[0-9]{1,2}(\.[0-9]{1,2})?$ ]]; then
  echo "::error title=setup-toolchain::python-version must look like 3.12 or 3.12.7, got '${version}'"
  exit 1
fi

if [[ -z "$requirements" ]]; then
  echo "::error title=setup-toolchain::requirements-file must not be empty"
  exit 1
fi

echo "setup-toolchain: python ${version}, cache keyed on ${requirements}"
```

`[[ ! "$version" =~ ^3\.[0-9]{1,2}(\.[0-9]{1,2})?$ ]]` tests the version against a regular expression: `3`, a literal dot, one or two digits, and optionally another dot with one or two digits. `3.12` and `3.12.7` pass; `latest`, `3`, `2.7`, `3.12; rm -rf /` fail. On failure `echo "::error title=setup-toolchain::..."` prints a **workflow command**: GitHub turns a line starting with `::error` into a visible error annotation with a title, and `exit 1` stops the script. `[[ -z "$requirements" ]]` is true if the text is empty; the second check rejects an empty file name. The last line reports the accepted values. Because the inputs are only variables and are compared as data, a hostile string cannot become a command.

<!-- /walk:.github/actions/setup-toolchain/validate-inputs.sh -->

<!-- walk:scripts/run_consumer.sh -->
### `scripts/run_consumer.sh`, line by line

Lines 1 to 11:

```bash
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
```

The header explains the idea: a consumer's workflow says `uses: sumitsr/platform-ci/...@v1` (or a SHA). GitHub resolves that ref when a run starts. This script resolves it the same way in this repository's Git history (with `pipeline/platform_refs.py`), unpacks each commit with `git archive`, and tells `act` to use those folders instead of cloning from github.com (`--local-repository`). Usage: `scripts/run_consumer.sh SERVICE [WORKFLOW_FILE] [extra act arguments...]`; the variable `PLATFORM_GIT` points to another clone.

Lines 13 to 21:

```bash
root="$(cd "$(dirname "$0")/.." && pwd)"
platform="${PLATFORM_REPO:-sumitsr/platform-ci}"
service="${1:?usage: scripts/run_consumer.sh SERVICE [WORKFLOW_FILE] [act arguments...]}"
workflow="${2:-$root/consumers/$service/.github/workflows/ci.yml}"
workflow="$(cd "$(dirname "$workflow")" && pwd)/$(basename "$workflow")"
repo="${PLATFORM_GIT:-$root}"
python="${PYTHON:-$root/.venv/bin/python}"
checkouts="$root/build/platform"
flags=()
```

Variables. `root` is the repository root (see `lab.sh`-style `cd "$(dirname "$0")/.."`). `platform="${PLATFORM_REPO:-sumitsr/platform-ci}"` uses the variable or a default. `service="${1:?usage: ...}"` requires the first argument. `workflow="${2:-...}"` is the second argument or the service's own `ci.yml`. The next line turns it into an absolute path (`dirname` of the file, `cd` there, `pwd`, then `/` and `basename`). `repo` is where refs are resolved (default: this repository). `python` is the interpreter (default: the repository's `.venv`). `checkouts` is where unpacked commits go. `flags=()` starts an empty array.

Lines 23 to 31:

```bash
while IFS=$'\t' read -r ref commit kind path; do
  dir="$checkouts/$commit"
  if [[ ! -d "$dir" ]]; then
    mkdir -p "$dir"
    git -C "$repo" archive "$commit" | tar -x -C "$dir"
  fi
  flags+=(--local-repository "$platform@$ref=$dir")
  echo "resolved ${path#"$platform"/}@${ref:0:12} -> ${commit:0:12} ($kind)"
done < <("$python" -m pipeline.platform_refs "$workflow" --platform "$platform" --repo "$repo")
```

The loop reads the output of the Python tool line by line: `while IFS=$'\t' read -r ref commit kind path; do ... done < <(command)`. `IFS=$'\t'` makes tab the field separator, so each line splits into four variables; `read -r` keeps backslashes; `< <(command)` feeds the command's output to the loop (**process substitution**). For each reference: `dir` is a folder named after the commit; if it does not exist (`! -d`), create it and extract the commit into it with `git -C "$repo" archive "$commit" | tar -x -C "$dir"` (`git archive` writes the files of a commit as a tar stream; `tar -x -C` unpacks into a folder). `flags+=(--local-repository "$platform@$ref=$dir")` appends two words to the array. The `echo` prints a summary using text slicing: `${path#"$platform"/}` removes the repository prefix; `${ref:0:12}` and `${commit:0:12}` take the first twelve characters.

Lines 33 to 46:

```bash
flags+=(--concurrent-jobs 1)

# Run from the repository root so act reads .actrc (the runner image), with the consumer's folder as its workspace.

log="$(mktemp)"
trap 'rm -f "$log"' EXIT
if act push -C "consumers/$service" -W "$workflow" "${flags[@]}" "${@:3}" 2>&1 | tee "$log"; then
  exit 0
fi
# A busy Docker daemon can time out while act removes the job's volumes, after the job itself succeeded.

if grep -q "Job succeeded" "$log" && ! grep -q "Job failed" "$log"; then
  echo "run_consumer: act reported a Docker cleanup error after the job succeeded" >&2
  exit 0
fi
exit 1
```

Add `--concurrent-jobs 1`. Run from the repository root so `act` reads `.actrc`, with `-C consumers/$service` as the workspace and `-W` for the workflow file; `"${@:3}"` passes any arguments from the third on. The output goes through `tee "$log"` (`tee` shows it and also saves it to a file). `mktemp` makes the log file and `trap 'rm -f "$log"' EXIT` removes it at exit. Success exits 0. Otherwise, if the log says `Job succeeded` and not `Job failed`, a Docker clean-up error after a good job is tolerated with exit 0; anything else exits 1.

<!-- /walk:scripts/run_consumer.sh -->

<!-- walk:scripts/demo_moved_tag.sh -->
### `scripts/demo_moved_tag.sh`, line by line

Lines 1 to 8:

```bash
#!/usr/bin/env bash
# Lesson step 5, locally: move the v1 tag to a changed commit and see who notices.

#
# Works on a throwaway clone, so this repository's tags are never touched. A consumer that calls the shared workflow

# by the tag `@v1` runs the changed code on its next run without changing anything itself; a consumer that calls it

# by the full commit of v1.0.0 does not. Exits 0 only when exactly that happens.

set -euo pipefail
```

The lesson's step 5 locally: move the tag `v1` to a changed commit and see who notices. It works on a throwaway clone so this repository's tags are never touched. It exits 0 only when the consumer on the tag runs the changed code and the consumer on the commit does not.

Lines 9 to 15:

```bash
root="$(cd "$(dirname "$0")/.." && pwd)"
marker="THIS CODE WAS CHANGED AFTER RELEASE"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

git clone -q --no-hardlinks "$root" "$work/platform-ci"
original="$(git -C "$work/platform-ci" rev-parse 'v1.0.0^{commit}')"
```

`marker` is the text the changed code will print. `work="$(mktemp -d)"` makes a temporary folder; `trap 'rm -rf "$work"' EXIT` deletes it at the end. `git clone -q --no-hardlinks "$root" "$work/platform-ci"` copies this repository (`--no-hardlinks` copies the files instead of sharing them, so nothing can touch the original). `original` is the commit that `v1.0.0` points to (`rev-parse 'v1.0.0^{commit}'`).

Lines 17 to 30:

```bash
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
git -c user.name=attacker -c user.email=attacker@example.invalid tag -f -a v1 -m "moved" >/dev/null
echo "v1 was ${original:0:12}, now points to $(git rev-parse --short=12 'v1^{commit}')"
```

The "malicious" commit. `git checkout -q --detach "$original"` checks out that commit without a branch. `python3 - "$marker" <<'PY' ... PY` runs Python code from a **here-document**: the `'PY'` in quotes means the shell does not expand anything inside; the `-` makes Python read the program from standard input and `"$marker"` becomes `sys.argv[1]`. The code inserts one extra step `- run: echo "<marker>"` in front of the secret-names step of `build-test.yml`. Then two Git commands with `-c user.name=... -c user.email=...` (one-time identity settings) commit the change and move the tag (`tag -f -a v1 -m moved`: `-f` replaces, `-a` makes an annotated tag). The `echo` shows the old and new commits.

Lines 32 to 40:

```bash
sed "s/ORIGINAL_COMMIT/$original/" "$root/demo/consumer-on-commit.yml" >"$work/on-commit.yml"
cp "$root/demo/consumer-on-tag.yml" "$work/on-tag.yml"

cd "$root"
export PLATFORM_GIT="$work/platform-ci"
echo "== svc-orders, calling the shared workflow by the tag @v1"
scripts/run_consumer.sh svc-orders "$work/on-tag.yml" >"$work/tag.log" 2>&1 || { cat "$work/tag.log"; exit 1; }
echo "== svc-search, calling the shared workflow by the full commit of v1.0.0"
scripts/run_consumer.sh svc-search "$work/on-commit.yml" >"$work/commit.log" 2>&1 || { cat "$work/commit.log"; exit 1; }
```

`sed "s/ORIGINAL_COMMIT/$original/"` fills the placeholder in the commit demo file. The two demo workflows are put in the work folder. `export PLATFORM_GIT="$work/platform-ci"` makes `run_consumer.sh` resolve refs in the clone. The script runs `svc-orders` with the workflow that calls `@v1` and `svc-search` with the one that calls the commit, each time sending output to a log file; `|| { cat "$work/tag.log"; exit 1; }` shows the log and fails if the run itself fails.

Lines 42 to 53:

```bash
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
```

The verdict. `grep -- "$marker"` searches for the marker (`--` ends the options so a marker starting with `-` would be safe); `|| true` keeps `set -e` from stopping when there is no match. The result is good only if the tag's log contains the marker and the commit's log does not; then it prints the RESULT line and exits 0; otherwise it prints `unexpected` to standard error and exits 1.

<!-- /walk:scripts/demo_moved_tag.sh -->

<!-- walk:scripts/org-policy.sh -->
### `scripts/org-policy.sh`, line by line

Lines 1 to 12:

```bash
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
```

The header: enforce the pinning policy for a whole organization with the `gh` CLI. Three things: (1) Actions must be pinned to a full-length commit SHA; (2) only the actions on `allowed-actions.txt` may run; (3) a ruleset makes the pin check a required workflow in every repository. The comment is honest: it is not run by `make` or CI, and was not run, because a personal account has no organization. `DRY_RUN=1` prints the commands.

Lines 14 to 20:

```bash
org="${1:?usage: scripts/org-policy.sh ORG}"
root="$(cd "$(dirname "$0")/.." && pwd)"

if [[ ! "$org" =~ ^[A-Za-z0-9_.-]+$ ]]; then
  echo "org-policy: '$org' is not an organization name" >&2
  exit 2
fi
```

`org` is the required first argument; `root` is the repository root. A regular expression check rejects names with odd characters (an organization name is letters, digits, `_`, `.`, `-`) and exits with code 2.

Lines 22 to 30:

```bash
gh_api() {
  if [[ "${DRY_RUN:-0}" == "1" ]]; then
    printf 'gh api'
    printf ' %q' "$@"
    printf '\n'
  else
    gh api "$@"
  fi
}
```

The helper `gh_api`: in a dry run it prints `gh api` and each argument shell-quoted (`printf ' %q' "$@"`) so you can read or paste the command; otherwise it runs `gh api "$@"`.

Lines 32 to 42:

```bash
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
```

Step 1: `PUT orgs/$org/actions/permissions` with `enabled_repositories=all`, `allowed_actions=selected` and `sha_pinning_required=true` (`-f` sends text, `-F` sends a typed value). Step 2 builds the allowed list: `patterns=()` is an empty array; the loop reads `allowed-actions.txt` line by line (`done <"$root/allowed-actions.txt"`); `${line%%#*}` removes a trailing `#` comment (the longest match of `#*` from the end), `${line//[[:space:]]/}` deletes all whitespace; non-empty lines are appended as `-f "patterns_allowed[]=<pattern>@*"` (`[[ -n "$line" ]] && patterns+=(...)` appends only when the line is not empty). Then `PUT orgs/$org/actions/permissions/selected-actions` sends them with `github_owned_allowed=false`.

Lines 44 to 50:

```bash
echo "3. a ruleset that requires the pin-check workflow on every repository's default branch"
ruleset="$root/docs/org-ruleset.json"
if [[ "${DRY_RUN:-0}" == "1" ]]; then
  echo "gh api -X POST orgs/$org/rulesets --input $ruleset"
else
  gh api -X POST "orgs/$org/rulesets" --input "$ruleset"
fi
```

Step 3: the ruleset is the JSON file `docs/org-ruleset.json`. In a dry run the command is printed; otherwise `gh api -X POST orgs/$org/rulesets --input <file>` sends the file as the request body.

<!-- /walk:scripts/org-policy.sh -->

<!-- walk:scripts/install-actionlint.sh -->
### `scripts/install-actionlint.sh`, line by line

Lines 1 to 10:

```bash
#!/usr/bin/env bash
# Install a pinned actionlint into ./.tools/bin and verify its SHA-256 before unpacking.

# Usage: scripts/install-actionlint.sh   (Linux amd64 or arm64; on a Mac use `brew install actionlint`)

set -euo pipefail

VERSION="1.7.12"
declare -A SUMS=(
  [linux_amd64]="8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8"
  [linux_arm64]="325e971b6ba9bfa504672e29be93c24981eeb1c07576d730e9f7c8805afff0c6"
)
```

Shebang, comments (what it does, how to use it: Linux amd64 or arm64; on a Mac use `brew install actionlint`), `set -euo pipefail`, the version `1.7.12` and an associative array `SUMS` with the expected SHA-256 checksum of the download for each platform (`declare -A` makes a dictionary; Bash 4 or newer).

Lines 12 to 26:

```bash
case "$(uname -s)-$(uname -m)" in
  Linux-x86_64) platform="linux_amd64" ;;
  Linux-aarch64) platform="linux_arm64" ;;
  *) echo "install-actionlint: unsupported platform $(uname -sm); install actionlint $VERSION yourself" >&2; exit 1 ;;
esac

dest="${TOOLS_DIR:-.tools}/bin"
mkdir -p "$dest"
archive="$(mktemp)"
trap 'rm -f "$archive"' EXIT
curl --fail --silent --show-error --location --retry 3 \
  "https://github.com/rhysd/actionlint/releases/download/v${VERSION}/actionlint_${VERSION}_${platform}.tar.gz" -o "$archive"
echo "${SUMS[$platform]}  $archive" | sha256sum --check --status || { echo "install-actionlint: checksum mismatch" >&2; exit 1; }
tar -xzf "$archive" -C "$dest" actionlint
echo "installed actionlint ${VERSION} to $dest/actionlint"
```

`case "$(uname -s)-$(uname -m)" in ...` chooses the platform from the operating system and CPU names (`Linux-x86_64`, `Linux-aarch64`); anything else prints an error and exits 1. `dest` is `${TOOLS_DIR:-.tools}/bin`; `mkdir -p` creates it; `mktemp` makes a temporary file and a `trap` removes it at exit. `curl --fail --silent --show-error --location --retry 3 URL -o file` downloads (fail on HTTP errors, quiet except for errors, follow redirects, retry three times). `echo "${SUMS[$platform]}  $archive" | sha256sum --check --status` compares the file with the expected checksum; if they differ it prints `checksum mismatch` and exits 1. `tar -xzf "$archive" -C "$dest" actionlint` unpacks only the file `actionlint`. The last line reports the install.

<!-- /walk:scripts/install-actionlint.sh -->

## Try it yourself

1. `shellcheck scripts/*.sh .github/actions/*/*.sh` prints nothing.
2. `INPUT_PYTHON_VERSION=3.12 INPUT_REQUIREMENTS_FILE=requirements.txt bash .github/actions/setup-toolchain/validate-inputs.sh` prints `setup-toolchain: python 3.12, cache keyed on requirements.txt`.
3. `INPUT_PYTHON_VERSION='3.12; rm -rf /' INPUT_REQUIREMENTS_FILE=x bash .github/actions/setup-toolchain/validate-inputs.sh; echo "exit $?"` prints the `::error` line and `exit 1`; nothing is deleted.
4. `DRY_RUN=1 scripts/org-policy.sh example-org` prints three `gh api` lines.
5. `bash -c 'set -e; false; echo not reached'; echo "exit $?"` prints `exit 1`.

## Mistakes people make

- Unquoted variables.
- No `set -e` so a failed step is ignored.
- Building a command from untrusted text with `eval` or `bash -c "$text"` by accident. (`build-test.yml` runs the caller's command on purpose, via `env`.)
- Assuming macOS's old `/bin/bash` 3.2 has arrays of arrays or `declare -A`.
- Putting `|| true` after everything and hiding real failures.

## Check yourself

1. What do `-e`, `-u`, `pipefail` do? *(Stop on error; error on unset variable; fail a pipeline when any part fails.)*
2. What does `${1:?usage}` do? *(Stops with the message if the argument is missing.)*
3. What is `<<'PY'`? *(A here-document with no expansion inside.)*
4. Why `trap ... EXIT`? *(Cleanup runs however the script ends.)*
5. Why does `validate-inputs.sh` read `INPUT_*` variables? *(So input text never becomes script text.)*

## Further reading

- GNU Bash manual (5.x): https://www.gnu.org/software/bash/manual/bash.html
- Workflow commands (`::error`): https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands
