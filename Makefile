# make help lists every target.   make up | run | test | lint | down
BIN ?= .venv/bin/
PYTHON ?= $(shell command -v python3.13 || command -v python3.12 || command -v python3.11 || command -v python3.10)
STAMP := .venv/.installed
ACT_IMAGE := plainround-act-runner:ubuntu-24.04
-include .env
PLATFORM_REPO ?= sumitsr/platform-ci
export PYTHONDONTWRITEBYTECODE ?= 1

.PHONY: help install up run run-all demo-moved-tag test lint format audit secrets-report check down clean

help: ## list the targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | sed -E 's/:.*## /\t/' | sort

$(STAMP): requirements.txt pyproject.toml
	$(PYTHON) -m venv .venv
	.venv/bin/pip install -q --require-hashes -r requirements.txt
	touch $@

install: $(STAMP) ## create .venv from the hash-pinned lock file

up: install ## install the tools and build the act runner image (Docker needed for run)
	docker build -q -t $(ACT_IMAGE) ci/act-runner

test: $(STAMP) ## unit tests of the pipeline tools, the action, the workflows and the three consumers
	$(BIN)python -m pytest --cov --cov-report=term-missing --cov-fail-under=95

lint: $(STAMP) ## ruff, format check, mypy, actionlint, pins (full SHA, fresh, allowed)
	$(BIN)ruff check .
	$(BIN)ruff format --check .
	$(BIN)mypy
	actionlint
	$(BIN)python -m pipeline.pins --internal $(PLATFORM_REPO) --allowlist allowed-actions.txt

format: $(STAMP) ## apply ruff's formatting and safe fixes
	$(BIN)ruff check --fix .
	$(BIN)ruff format .

audit: $(STAMP) ## check the locked dependencies for known vulnerabilities
	$(BIN)pip-audit --no-deps --disable-pip -r requirements.txt

check: lint test ## lint plus test

down: ## remove leftover act containers
	-docker ps -aq --filter "name=act-" | xargs docker rm -f

clean: down
	rm -rf .venv build .pytest_cache .mypy_cache .ruff_cache .coverage coverage.xml .tools
