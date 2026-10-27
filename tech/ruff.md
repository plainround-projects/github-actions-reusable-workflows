# Ruff

## What it is

Ruff is a **linter** and a **formatter** for Python, written in Rust. A linter reads source code without running it and reports likely mistakes and style problems. A formatter rewrites code into one agreed layout (line breaks, quotes, spacing). Ruff does both, very fast. This repository pins ruff 0.8.4.

<!-- words -->

<details>
<summary><b>Words this note uses, in case they are new to you</b> (click to open)</summary>

- **repository**: A project's folder of files together with its complete history of changes. On GitHub, a repository is a page with those files, issues and pull requests.
- **CI**: Continuous integration: running checks (build, tests, linters) automatically every time code changes.
- **list**: An ordered collection of values written one after another.
- **docstring**: A text in triple quotes at the start of a Python file, class or function that documents it; tools and people can read it.
- **comprehension**: A short way to build a list, set or dictionary from a loop in one expression, such as `[x * 2 for x in items if x > 0]`.
- **pytest**: A Python test framework: it finds functions named `test_...`, runs them, and reports failures.

</details>

<!-- /words -->

## Why this repository uses it

The template requires a linter and a formatter configured in the repository and run in CI. One tool does both for the platform's tools and for the three consumers' source and tests. `make lint` and the CI lint job run it.

## Where it appears

| Path | What it does with ruff |
| --- | --- |
| `pyproject.toml` | `[tool.ruff]`, `[tool.ruff.lint]`, `[tool.ruff.lint.per-file-ignores]`. |
| `Makefile` | `lint` runs `ruff check .` and `ruff format --check .`; `format` runs `ruff check --fix .` and `ruff format .`. |
| `requirements.txt` | The pin `ruff==0.8.4` and its hashes. |

## How it works underneath

Ruff parses each Python file into a tree (the **abstract syntax tree**), then runs rules over the tree. Each rule has a code: a letter group and a number (`E501` line too long, `I001` imports not sorted). `ruff check` prints findings and exits non-zero if any exist; `--fix` applies the safe automatic fixes. `ruff format` is a formatter compatible with the Black style; with `--check` it only reports files that would change.

## Walkthrough of this repository's use

```toml
[tool.ruff]
line-length = 120
target-version = "py310"
src = ["pipeline", "tests", "consumers/svc-orders/src", "consumers/svc-billing/src", "consumers/svc-search/src"]
extend-exclude = ["build"]
```

`line-length = 120` is the wrap width. `target-version = "py310"` is the oldest Python to support. `src` lists the folders of first-party code (the import-sorting rule needs to know what is "ours"), including each consumer's `src`. `extend-exclude = ["build"]` skips `build/`, where `act` unpacks platform commits.

```toml
[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "SIM", "N", "C4", "RUF", "PT", "D100", "D101", "D102", "D103", "D104"]
```

| Code | Family |
| --- | --- |
| `E` | pycodestyle errors (long lines) |
| `F` | pyflakes (unused imports, undefined names) |
| `I` | import order |
| `B` | bugbear (likely bugs) |
| `UP` | upgrade to newer syntax allowed by `target-version` |
| `SIM` | simplifications |
| `N` | naming |
| `C4` | comprehension style |
| `RUF` | ruff's own rules |
| `PT` | pytest style |
| `D100`..`D104` | docstrings required on public modules, classes, methods, functions, packages |

```toml
[tool.ruff.lint.per-file-ignores]
"tests/**" = ["D"]
"consumers/*/tests/**" = ["D"]
```

Tests, including the consumers', need no docstrings.

`make lint` runs `ruff check .` (rules) and `ruff format --check .` (layout, report only); `make format` applies fixes.

## Try it yourself

1. `.venv/bin/ruff --version` prints `ruff 0.8.4`.
2. `.venv/bin/ruff check .` prints `All checks passed!`.
3. `.venv/bin/ruff format --check .` prints `NN files already formatted`.
4. `printf 'import os\n' > /tmp/x.py && .venv/bin/ruff check /tmp/x.py` reports `F401 ... imported but unused` (and `D100`, because the file has no docstring).
5. `.venv/bin/ruff rule D103` explains one rule.

## Mistakes people make

- Running the formatter and the linter in different tools with different widths.
- Silencing a rule everywhere instead of for the one file that needs it.
- Not setting `target-version`, so ruff suggests syntax newer than the oldest supported Python.
- Letting `--fix` rewrite files in CI; CI here only checks.

## Check yourself

1. Linter versus formatter? *(A linter reports problems; a formatter rewrites layout.)*
2. What does `--check` do on `ruff format`? *(Reports files that would change and exits non-zero, without writing.)*
3. Why `target-version = "py310"`? *(So suggestions respect the oldest supported Python.)*
4. What do `D100` to `D104` require? *(Docstrings on public modules, classes, methods, functions and packages.)*
5. Why are tests exempt from `D`? *(Their names are written as behavior; docstrings would be noise.)*

## Further reading

- Ruff 0.8 documentation: https://docs.astral.sh/ruff/
- Rule list: https://docs.astral.sh/ruff/rules/
