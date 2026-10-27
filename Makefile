# make help lists every target.   make up | run | test | lint | down
STAMP := .venv/.installed
# In CI (the CI variable is set) the tools are already on the PATH from the workflow's own install step.
BIN ?= $(if $(CI),,.venv/bin/)
DEPS := $(if $(CI),,$(STAMP))
PYTHON ?= $(shell command -v python3.13 || command -v python3.12 || command -v python3.11 || command -v python3.10)
ACT_IMAGE := plainround-act-runner:ubuntu-24.04
-include .env
export PYTHONDONTWRITEBYTECODE ?= 1

.PHONY: help install up run run-v1 run-all demo-moved-tag test lint format audit secrets-report check down clean

help: ## list the targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | sed -E 's/:.*## /\t/' | sort

$(STAMP): requirements.txt pyproject.toml
	$(PYTHON) -m venv .venv
	.venv/bin/pip install -q --require-hashes -r requirements.txt
	touch $@

install: $(DEPS) ## create .venv from the hash-pinned lock file

up: install ## install the tools and build the act runner image (Docker needed for run)
	docker build -q -t $(ACT_IMAGE) ci/act-runner

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

secrets-report: $(DEPS) ## what the shared workflow can read, per consumer
	$(BIN)python -m pipeline.secrets_report

test: $(DEPS) ## unit tests of the pipeline tools, the action, the workflows and the three consumers
	$(BIN)python -m pytest --cov --cov-report=term-missing --cov-fail-under=95
	@for service in svc-orders svc-billing svc-search; do \
	  $(BIN)python -m pytest -q -p no:cacheprovider consumers/$$service || exit 1; \
	done

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
