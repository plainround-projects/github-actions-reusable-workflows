# Bash

## What it is

Bash is a **shell**: a program that reads commands and runs them. A file of commands is a **shell script**. Bash is the normal shell on Linux and macOS, and GitHub's runners (including Windows ones, through Git Bash) have it, so workflow steps here set `shell: bash`.

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
