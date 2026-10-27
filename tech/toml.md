# TOML

## What it is

TOML is a text format for configuration: `[section]` headers, `key = value` lines, quoted text and lists in square brackets. `pyproject.toml` is the file Python tools agree to read for project settings. Each tool opens the file and reads only its own section.

<!-- words -->

<details>
<summary><b>Words this note uses, in case they are new to you</b> (click to open)</summary>

- **repository**: A project's folder of files together with its complete history of changes. On GitHub, a repository is a page with those files, issues and pull requests.
- **workflow**: A GitHub Actions automation described in a YAML file under `.github/workflows/`. It names the events that start it and the jobs it runs.
- **package**: In Python, a folder with an `__init__.py` file that can be imported as a unit; also a bundle of code installed with pip.
- **library**: A package of ready-made code that your program calls.
- **dependency**: A package that your project needs in order to work.
- **lock file**: A file that records the exact version, and a checksum, of every package that was installed, so that everyone installs exactly the same thing.
- **function**: A named piece of code that takes inputs (parameters), does something, and may return a result.
- **list**: An ordered collection of values written one after another.
- **folder**: A container for files and other folders on disk (also called a directory).
- **version**: A number such as `1.2.3` that names one release of software (major.minor.patch).
- **test**: A small program that uses your code and checks that the answer is the one you expected.
- **runtime**: The program that runs your code (Node.js runs JavaScript).
- **pytest**: A Python test framework: it finds functions named `test_...`, runs them, and reports failures.

</details>

<!-- /words -->

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

<!-- walk:pyproject.toml -->
### `pyproject.toml`, line by line

Lines 1 to 9:

```toml
[project]
name = "platform-ci"
version = "2.0.0"
description = "A shared GitHub Actions platform: a reusable workflow, a composite action, three consumers and the tools that test them."
readme = "README.md"
requires-python = ">=3.10"
license = { text = "MIT" }
authors = [{ name = "Sumit Srivastava" }]
dependencies = ["PyYAML==6.0.2"]
```

The `[project]` table: the project's name (`platform-ci`), version (`2.0.0`), description, readme file, the oldest Python (`>=3.10`), the license (`{ text = "MIT" }` is an inline table), the authors (a list of inline tables) and `dependencies = ["PyYAML==6.0.2"]`, the one package the tools import.

Lines 44 to 49:

```toml
[tool.coverage.run]
source = ["pipeline"]
branch = true

[tool.coverage.report]
show_missing = true
```

`[tool.coverage.run]` tells coverage to measure only the `pipeline` package (`source`) and to count **branches** (each side of an `if`), not just lines. `[tool.coverage.report]` with `show_missing = true` lists the line numbers that no test ran.

<!-- /walk:pyproject.toml -->

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
