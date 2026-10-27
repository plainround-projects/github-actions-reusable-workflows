# TOML

## What it is

TOML is a text format for configuration: `[section]` headers, `key = value` lines, quoted text and lists in square brackets. `pyproject.toml` is the file Python tools agree to read for project settings. Each tool opens the file and reads only its own section.

## Why this repository uses it

One file holds the metadata of the platform's tooling and the settings of ruff, mypy, pytest and coverage. Each consumer service has its own small `pyproject.toml` that sets only the test paths.

## Where it appears

| Path | What it does with TOML |
| --- | --- |
| `pyproject.toml` | Metadata and the settings of ruff, mypy, pytest and coverage for the platform's tools and for linting the consumers. |
| `consumers/svc-orders/pyproject.toml`, `svc-billing`, `svc-search` | Name, version and `[tool.pytest.ini_options]` for each service. |

## How it works underneath

A section name like `[tool.ruff.lint]` means "inside `tool`, inside `ruff`, inside `lint`". `[[tool.mypy.overrides]]` (double brackets) adds one more item to a list of tables. Python 3.11 added a TOML reader to its standard library (`tomllib`); the lock file adds the small `tomli` package for Python 3.10.

## Walkthrough of this repository's use

```toml
[project]
name = "platform-ci"
version = "2.0.0"
requires-python = ">=3.10"
dependencies = ["PyYAML==6.0.2"]
```

The tools package: the oldest Python allowed and its one runtime dependency. The version tracks the latest release of the shared workflow.

```toml
[tool.ruff]
line-length = 120
target-version = "py310"
src = ["pipeline", "tests", "consumers/svc-orders/src", "consumers/svc-billing/src", "consumers/svc-search/src"]
extend-exclude = ["build"]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["D"]
"consumers/*/tests/**" = ["D"]
```

`src` tells ruff where first-party code lives (it needs this to sort imports correctly), including the three consumers' `src` folders. `extend-exclude` skips the `build/` folder where `act` unpacks platform commits. Docstring rules are off in tests.

```toml
[tool.mypy]
python_version = "3.10"
strict = true
files = ["pipeline", "tests", "consumers"]
mypy_path = ["consumers/svc-orders/src", "consumers/svc-billing/src", "consumers/svc-search/src"]
explicit_package_bases = true
exclude = ["build/"]

[[tool.mypy.overrides]]
module = ["tests.*", "test_orders", "test_billing", "test_search", "conftest"]
disallow_untyped_defs = false
```

`mypy_path` lists where to find the packages `orders`, `billing` and `search`. The override relaxes the "every function needs hints" rule for test modules only; the consumers' tests are named `test_orders` and so on, so those names are listed.

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
addopts = "-ra --strict-markers"
markers = ["act: runs a workflow with act and needs Docker (make run)"]
```

`pythonpath = ["."]` lets tests import `pipeline` from the repository root. `markers` registers a marker name so `--strict-markers` accepts it.

```toml
[tool.coverage.run]
source = ["pipeline"]
branch = true
```

Coverage is measured on the `pipeline` package, counting branches, and the Makefile requires 95 percent.

A consumer's file:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

Inside a consumer, `src` is the import path, so `import orders` works without installing the service.

## Try it yourself

1. `.venv/bin/python -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); print(d['project']['version'], list(d['tool']))"` prints `2.0.0 ['ruff', 'mypy', 'pytest', 'coverage']`.
2. `.venv/bin/python -c "import tomllib; print(tomllib.load(open('consumers/svc-orders/pyproject.toml','rb'))['tool']['pytest']['ini_options'])"` prints `{'testpaths': ['tests'], 'pythonpath': ['src']}`.
3. `cd consumers/svc-orders && ../../.venv/bin/python -m pytest -q` runs that service's tests using its own file.

## Mistakes people make

- Forgetting quotes around text values.
- Single brackets where double are needed for a list of tables.
- Putting one tool's settings in two files.
- Running a consumer's tests from the wrong folder so its `pythonpath` is not used.

## Check yourself

1. Which section does ruff read? *(`[tool.ruff]` and its sub-sections.)*
2. What does `pythonpath = ["src"]` do in a consumer? *(Puts its `src` folder on the import path.)*
3. What does `branch = true` mean? *(Coverage counts each side of a decision.)*
4. Why is `mypy_path` set? *(So mypy finds the consumers' packages under their `src` folders.)*
5. Why does the platform version in `pyproject.toml` matter? *(It records which release of the shared workflow the tools match.)*

## Further reading

- TOML 1.0: https://toml.io/en/v1.0.0
- `pyproject.toml` specification: https://packaging.python.org/en/latest/specifications/pyproject-toml/
