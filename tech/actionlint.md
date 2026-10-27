# actionlint

## What it is

actionlint is a command-line checker for GitHub Actions workflow files. Like a spell-checker for workflows, it reads the YAML and reports mistakes: unknown keys, wrong types, bad `${{ }}` expressions, undefined job names in `needs`, and (with ShellCheck installed) problems inside `run:` scripts. This repository uses version 1.7.12.

<!-- words -->

<details>
<summary><b>Words this note uses, in case they are new to you</b> (click to open)</summary>

- **shell**: The program inside a terminal that reads what you type and starts other programs. Bash is a shell.
- **exit code**: A number a program leaves behind when it ends. 0 means success; any other number means failure. Build systems read it to decide whether a step passed.
- **checksum**: A short fingerprint computed from a file's content. If one byte changes the fingerprint changes, so comparing fingerprints shows whether a file is the one you expected.
- **repository**: A project's folder of files together with its complete history of changes. On GitHub, a repository is a page with those files, issues and pull requests.
- **workflow**: A GitHub Actions automation described in a YAML file under `.github/workflows/`. It names the events that start it and the jobs it runs.
- **CI**: Continuous integration: running checks (build, tests, linters) automatically every time code changes.
- **JSON**: A plain-text format for structured data: objects `{ "name": "value" }`, lists `[1, 2]`, texts in double quotes, numbers, `true`, `false`, `null`. It has no comments.
- **YAML**: A plain-text format for structured data that uses indentation instead of braces. GitHub workflows are YAML files.
- **version**: A number such as `1.2.3` that names one release of software (major.minor.patch).

</details>

<!-- /words -->

## Why this repository uses it

Workflow mistakes otherwise appear only after a push, on GitHub. This repository has several workflows that call one another with typed inputs, so a typo in an input name is easy to make. `make lint` and CI run `actionlint` to catch it first.

## Where it appears

| Path | What it does with actionlint |
| --- | --- |
| `Makefile` | `lint` runs `actionlint` (it finds `.github/workflows/*.yml` itself). |
| `.github/workflows/ci.yml` | Installs a pinned binary with `scripts/install-actionlint.sh`, then runs `make lint`. |
| `scripts/install-actionlint.sh` | Downloads release 1.7.12 and verifies its SHA-256. |

## How it works underneath

actionlint parses each workflow file into a tree, then checks it in layers: the YAML shape, then the syntax of every `${{ }}` expression, then the types (`matrix.os` exists only if the matrix defines `os`), then the context rules (`needs.lint.result` is valid only when the job needs `lint`). For each `run:` step it passes the script to ShellCheck (`shellcheck.md`) if that program is on the `PATH`. It does not contact GitHub, so it cannot know whether a remote action exists.

## Walkthrough of this repository's use

```bash
actionlint
```

Run from the repository root; no output and exit code 0 mean every workflow passed. It checks, among other things, that a caller's `with:` keys exist in the called workflow (for local calls such as the `consumers` job in `ci.yml`), that `needs` names exist, that expressions like `${{ matrix.service }}` refer to real matrix keys, and, through ShellCheck, the scripts inside `run:` blocks (including the `pin-check.yml` script with its `# shellcheck disable=SC2086` line). It does not fetch remote workflows, so it cannot check that `sumitsr/platform-ci/...@<sha>` exists or that its inputs match; that is what `tests/test_build_test_workflow.py` and the consumer tests are for.

In CI:

```yaml
- run: scripts/install-actionlint.sh
- run: echo "$PWD/.tools/bin" >> "$GITHUB_PATH"
- run: make lint BIN=
```

The installer verifies a checksum, the second step puts the binary on the `PATH` of later steps, and `make lint` finds it.

## Try it yourself

1. `actionlint -version` prints `1.7.12`.
2. `actionlint` prints nothing and exits 0.
3. `git init -q /tmp/w && mkdir -p /tmp/w/.github/workflows && printf 'on: push\njobs:\n  j:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo ${{ matrix.os }}\n' > /tmp/w/.github/workflows/x.yml && (cd /tmp/w && actionlint)` reports `property "os" is not defined`.
4. `actionlint -format '{{json .}}'` prints findings as JSON.

## Mistakes people make

- Believing a clean actionlint run means the workflow works. It cannot see GitHub's servers, secrets or remote actions.
- Skipping ShellCheck, which silently drops the script checks.
- Running a different actionlint version locally and in CI.

## Check yourself

1. What does actionlint read? *(Workflow YAML files.)*
2. What extra checking does ShellCheck add? *(Mistakes inside `run:` shell scripts.)*
3. Does it contact GitHub? *(No.)*
4. How does CI get the binary? *(`scripts/install-actionlint.sh` downloads a pinned release and verifies the checksum.)*
5. What would `matrix.os` without a matrix key cause? *(An error: the property is not defined.)*

## Further reading

- actionlint 1.7 documentation: https://github.com/rhysd/actionlint/blob/v1.7.12/docs/usage.md
- Checks reference: https://github.com/rhysd/actionlint/blob/v1.7.12/docs/checks.md
