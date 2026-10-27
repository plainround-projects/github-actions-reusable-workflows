# Make

## What it is

Make is a command-line tool that runs named recipes from a file called `Makefile`. A recipe is a **target**: a name, what it depends on (its **prerequisites**), and shell commands. Make can rebuild only what is out of date by comparing file times, and projects also use it as a short list of named commands (`make test`).

## Why this repository uses it

A reader should need only `make run`, `make test` and `make lint`. A Makefile gives the same commands on a laptop and in CI.

## Where it appears

| Path | What it does with Make |
| --- | --- |
| `Makefile` | Targets: `install`, `up`, `run`, `run-v1`, `run-all`, `demo-moved-tag`, `secrets-report`, `test`, `lint`, `format`, `audit`, `check`, `down`, `clean`, `help`. |
| `.github/workflows/ci.yml` | `make lint BIN=`, `make audit BIN=`, `make test BIN=`. |

## How it works underneath

Make reads the Makefile, picks the target you named, builds its prerequisites first, then runs its recipe. A target that names a file is rebuilt only if a prerequisite is newer. A name that is not a file belongs under `.PHONY`. Each recipe line starts with a **tab** and runs in its own shell; `@` hides the echo of a line, `-` ignores its failure. `$(NAME)` expands a variable; in a recipe a shell variable needs `$$name`.

## Walkthrough of this repository's use

```make
STAMP := .venv/.installed
BIN ?= $(if $(CI),,.venv/bin/)
DEPS := $(if $(CI),,$(STAMP))
PYTHON ?= $(shell command -v python3.13 || command -v python3.12 || command -v python3.11 || command -v python3.10)
ACT_IMAGE := gha-projects-act-runner:ubuntu-24.04
-include .env
PLATFORM_REPO ?= sumitsr/platform-ci
export PYTHONDONTWRITEBYTECODE ?= 1
```

`:=` assigns once. `?=` assigns only if unset, so `make lint BIN=` overrides. GitHub sets `CI`, so in CI `BIN` and `DEPS` are empty (tools come from the `PATH`; no venv is built). `-include .env` reads `.env` if it exists and does not fail if it is missing. `export` passes a variable to every recipe's environment; `PYTHONDONTWRITEBYTECODE=1` stops Python writing `.pyc` files.

```make
$(STAMP): requirements.txt pyproject.toml
	$(PYTHON) -m venv .venv
	.venv/bin/pip install -q --require-hashes -r requirements.txt
	touch $@
```

The environment is rebuilt only when the lock file or `pyproject.toml` is newer than `.venv/.installed` (`touch $@` updates it; `$@` is the target name).

```make
run: ## run the action's test workflow and svc-orders through build-test locally with act (Docker needed)
	act push --concurrent-jobs 1 -W .github/workflows/test-setup-toolchain.yml
	scripts/run_consumer.sh svc-orders

run-v1:
	scripts/run_consumer.sh svc-orders $(CURDIR)/demo/consumer-on-tag.yml
```

`$(CURDIR)` is the folder Make runs in; `run-v1` passes an absolute path because the script runs `act` from the repository root with the consumer as workspace.

```make
test: $(DEPS)
	$(BIN)python -m pytest --cov --cov-report=term-missing --cov-fail-under=95
	@for service in svc-orders svc-billing svc-search; do \
	  $(BIN)python -m pytest -q -p no:cacheprovider consumers/$$service || exit 1; \
	done
```

The first line tests the platform's own tools with a 95 percent coverage floor. The loop tests each consumer separately: each has its own `pyproject.toml` that sets its import path, and separate runs keep their test modules apart. `|| exit 1` stops at the first failure.

```make
lint: $(DEPS)
	$(BIN)ruff check .
	$(BIN)ruff format --check .
	$(BIN)mypy
	actionlint
	shellcheck scripts/*.sh .github/actions/*/*.sh
	$(BIN)python -m pipeline.pins --internal $(PLATFORM_REPO) --allowlist allowed-actions.txt
```

Six checks. The last verifies every `uses:` is pinned, that the platform's own action is pinned to its latest change, and that every external action is on `allowed-actions.txt`.

## Try it yourself

1. `make help` lists the targets with their one-line text.
2. `make -n lint` prints the six commands without running them.
3. `CI=true make -n test` prints them without the `.venv/bin/` prefix.
4. `make secrets-report` prints the three-row table.
5. `make demo-moved-tag` (Docker needed) ends with `RESULT: the consumer on @v1 ran the changed code; the consumer on the commit did not.`

## Mistakes people make

- Spaces instead of a tab at the start of a recipe line ("missing separator").
- Forgetting `.PHONY`.
- `$id` instead of `$$id` in a recipe.
- Expecting state to carry over between recipe lines.
- GNU Make 4 features on macOS's Make 3.81.

## Check yourself

1. What does `?=` do? *(Sets a variable only if it is not already set.)*
2. Why is `DEPS` empty in CI? *(The workflow already installed the tools.)*
3. What does `touch $@` do? *(Updates the stamp file named by the target.)*
4. Why does the consumer loop use `|| exit 1`? *(To stop at the first failing service.)*
5. What does `-include .env` do when the file is missing? *(Nothing; no error.)*

## Further reading

- GNU Make manual: https://www.gnu.org/software/make/manual/make.html
