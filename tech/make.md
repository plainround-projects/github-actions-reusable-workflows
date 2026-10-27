# Make

## What it is

Make is a command-line tool that runs named recipes from a file called `Makefile`. A recipe is a **target**: a name, what it depends on (its **prerequisites**), and shell commands. Make can rebuild only what is out of date by comparing file times, and projects also use it as a short list of named commands (`make test`).

<!-- words -->

<details>
<summary><b>Words this note uses, in case they are new to you</b> (click to open)</summary>

- **shell**: The program inside a terminal that reads what you type and starts other programs. Bash is a shell.
- **PATH**: An environment variable listing the folders where the shell looks for programs. Typing `node` works because the folder holding `node` is in `PATH`.
- **hash**: A fixed-length fingerprint computed from some data. The same data always gives the same hash; any change gives a different one. SHA-256 and SHA-1 are two ways of computing one.
- **repository**: A project's folder of files together with its complete history of changes. On GitHub, a repository is a page with those files, issues and pull requests.
- **workflow**: A GitHub Actions automation described in a YAML file under `.github/workflows/`. It names the events that start it and the jobs it runs.
- **runner**: The computer, usually a virtual machine, on which GitHub runs a job. It starts clean for every job.
- **image**: A read-only package that holds everything needed to start a container: a file system plus settings. A running **container** is made from an image.
- **Docker**: A tool that builds images and runs containers.
- **lock file**: A file that records the exact version, and a checksum, of every package that was installed, so that everyone installs exactly the same thing.
- **cache**: A saved copy of something slow to produce (such as downloaded packages), kept so the next run can reuse it.
- **list**: An ordered collection of values written one after another.
- **folder**: A container for files and other folders on disk (also called a directory).
- **test**: A small program that uses your code and checks that the answer is the one you expected.
- **pytest**: A Python test framework: it finds functions named `test_...`, runs them, and reports failures.

</details>

<!-- /words -->

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

<!-- walk:Makefile -->
### `Makefile`, line by line

Lines 1 to 12:

```make
# make help lists every target.   make up | run | test | lint | down

STAMP := .venv/.installed
# In CI (the CI variable is set) the tools are already on the PATH from the workflow's own install step.

BIN ?= $(if $(CI),,.venv/bin/)
DEPS := $(if $(CI),,$(STAMP))
PYTHON ?= $(shell command -v python3.13 || command -v python3.12 || command -v python3.11 || command -v python3.10)
ACT_IMAGE := gha-projects-act-runner:ubuntu-24.04
-include .env
PLATFORM_REPO ?= sumitsr/platform-ci
export PYTHONDONTWRITEBYTECODE ?= 1

.PHONY: help install up run run-v1 run-all demo-moved-tag test lint format audit secrets-report check down clean
```

Header comment and variables. `STAMP` is the marker file `.venv/.installed`. `BIN ?= $(if $(CI),,.venv/bin/)`: the folder prefix of tools: empty when the environment variable `CI` is set (in GitHub's CI the tools are already on the PATH), else `.venv/bin/`; `?=` lets the caller override it (`make lint BIN=`). `DEPS` is the marker in a developer's machine and empty in CI. `PYTHON ?= $(shell command -v python3.13 || ...)` finds the newest of Python 3.13, 3.12, 3.11, 3.10 (`command -v` prints the path of a program; `||` tries the next). `ACT_IMAGE` names the runner image. `-include .env` reads an optional `.env` file (the `-` ignores it if missing). `PLATFORM_REPO ?= sumitsr/platform-ci` is the default repository name. `export PYTHONDONTWRITEBYTECODE ?= 1` tells Python not to write `.pyc` files. `.PHONY` lists the command-like targets.

Lines 14 to 25:

```make
help: ## list the targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | sed -E 's/:.*## /\t/' | sort

$(STAMP): requirements.txt pyproject.toml
	$(PYTHON) -m venv .venv
	.venv/bin/pip install -q --require-hashes -r requirements.txt
	touch $@

install: $(DEPS) ## create .venv from the hash-pinned lock file

up: install ## install the tools and build the act runner image (Docker needed for run)
	docker build -q -t $(ACT_IMAGE) ci/act-runner
```

`help` prints the targets. The rule for `$(STAMP)` depends on `requirements.txt` and `pyproject.toml`: it creates the virtual environment (`$(PYTHON) -m venv .venv`; a **virtual environment** is a private folder of installed Python packages for this project), installs the locked tools with hash checking, and `touch`es the marker. `install` just needs the marker. `up` builds the act runner image (needs Docker).

Lines 27 to 41:

```make
# The platform's own test workflow (the composite action), then one consumer through the shared workflow, with act.

run: ## run the action's test workflow and svc-orders through build-test locally with act (Docker needed)
	act push --concurrent-jobs 1 -W .github/workflows/test-setup-toolchain.yml
	scripts/run_consumer.sh svc-orders

run-v1: ## run svc-orders as it was before v2: calling build-test@v1 with python-version (still works)
	scripts/run_consumer.sh svc-orders $(CURDIR)/demo/consumer-on-tag.yml

run-all: ## run all three consumers through build-test locally with act
	scripts/run_consumer.sh svc-orders
	scripts/run_consumer.sh svc-billing
	scripts/run_consumer.sh svc-search

demo-moved-tag: $(DEPS) ## lesson step 5: move v1 in a throwaway clone; the @v1 consumer runs the new code, the SHA one does not
	scripts/demo_moved_tag.sh
```

`run`: first the composite action's own workflow with `act push --concurrent-jobs 1 -W .github/workflows/test-setup-toolchain.yml`, then `scripts/run_consumer.sh svc-orders`. `run-v1` runs `svc-orders` with `demo/consumer-on-tag.yml` (`$(CURDIR)` is Make's current folder). `run-all` runs the three consumers one after another. `demo-moved-tag` runs the script of the same name.

Lines 43 to 50:

```make
secrets-report: $(DEPS) ## what the shared workflow can read, per consumer
	$(BIN)python -m pipeline.secrets_report

test: $(DEPS) ## unit tests of the pipeline tools, the action, the workflows and the three consumers
	$(BIN)python -m pytest --cov --cov-report=term-missing --cov-fail-under=95
	@for service in svc-orders svc-billing svc-search; do \
	  $(BIN)python -m pytest -q -p no:cacheprovider consumers/$$service || exit 1; \
	done
```

`secrets-report` runs `python -m pipeline.secrets_report`. `test` first runs the platform's tests with coverage (`--cov` measures, `--cov-report=term-missing` lists untested lines, `--cov-fail-under=95` fails below 95 percent), then each consumer's tests in a shell `for` loop: `$$service` is written with two dollar signs because Make would otherwise consume one; `|| exit 1` stops at the first failing service; `-p no:cacheprovider` disables pytest's cache folder; `\` continues the line.

Lines 52 to 73:

```make
lint: $(DEPS) ## ruff, format check, mypy, actionlint, pins (full SHA, fresh, allowed)
	$(BIN)ruff check .
	$(BIN)ruff format --check .
	$(BIN)mypy
	actionlint
	shellcheck scripts/*.sh .github/actions/*/*.sh
	$(BIN)python -m pipeline.pins --internal $(PLATFORM_REPO) --allowlist allowed-actions.txt

format: $(DEPS) ## apply ruff's formatting and safe fixes
	$(BIN)ruff check --fix .
	$(BIN)ruff format .

audit: $(DEPS) ## check the locked dependencies for known vulnerabilities
	$(BIN)pip-audit --no-deps --disable-pip -r requirements.txt

check: lint test ## lint plus test

down: ## remove leftover act containers of this project's runner image
	-docker ps -aq --filter "ancestor=$(ACT_IMAGE)" | xargs docker rm -f

clean: down
	rm -rf .venv build .pytest_cache .mypy_cache .ruff_cache .coverage coverage.xml .tools
```

`lint` runs, in order: `ruff check .`, `ruff format --check .`, `mypy`, `actionlint`, `shellcheck scripts/*.sh .github/actions/*/*.sh`, and `python -m pipeline.pins --internal $(PLATFORM_REPO) --allowlist allowed-actions.txt`. `format` applies ruff's safe fixes and formatting. `audit` runs `pip-audit --no-deps --disable-pip -r requirements.txt`. `check` is `lint` plus `test`. `down` removes leftover containers made from the runner image; `clean` depends on `down` and deletes the virtual environment and caches.

<!-- /walk:Makefile -->

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
