# mypy

## What it is

mypy is a **static type checker** for Python. Python lets you write **type hints**, such as `def add(left: int, right: int) -> int`, but the interpreter ignores them. mypy reads them without running the code and reports places where the types do not fit, for example passing text where a number is expected. This repository pins mypy 1.13.0.

## Why this repository uses it

The template asks for typed code checked in CI. Strict checking applies to the platform's tools and to the three consumers' domain, application, infrastructure and interface code. Types document what each function takes and returns.

## Where it appears

| Path | What it does with mypy |
| --- | --- |
| `pyproject.toml` | `[tool.mypy]` with `strict = true` and an override for test modules. |
| `Makefile` | `lint` runs `mypy` with no arguments. |
| `requirements.txt` | Pins mypy 1.13.0 and `types-PyYAML`. |

## How it works underneath

mypy parses every listed file, builds a model of every function's declared types, and checks each call and return against them. It does not execute the program. When a library has no type information, mypy cannot check calls into it. Some libraries ship hints (a `py.typed` file); others have a separate "stubs" package (`types-PyYAML`) with only the signatures.

## Walkthrough of this repository's use

```toml
[tool.mypy]
python_version = "3.10"
strict = true
files = ["pipeline", "tests", "consumers"]
mypy_path = ["consumers/svc-orders/src", "consumers/svc-billing/src", "consumers/svc-search/src"]
explicit_package_bases = true
exclude = ["build/"]
```

`strict = true` turns on all optional strict checks: every function needs hints, untyped calls are errors, `Any` must not leak. `files` is what to check (the three consumers are checked as a folder). `mypy_path` tells mypy where the packages `orders`, `billing` and `search` live (under each consumer's `src`). `explicit_package_bases = true` makes mypy name modules from those paths. `exclude = ["build/"]` skips unpacked platform commits.

```toml
[[tool.mypy.overrides]]
module = ["tests.*", "test_orders", "test_billing", "test_search", "conftest"]
disallow_untyped_defs = false
disallow_incomplete_defs = false
disallow_untyped_calls = false
```

Test functions are named as sentences, so annotating each would be noise. The consumers' test modules are named `test_orders`, `test_billing`, `test_search`, so those names are listed.

Hints you will see in the code: `Mapping[Any, Any]` (any read-only mapping), `str | dict[str, Any] | None` (one of three shapes), `Iterator[str]` (a generator of strings), `Protocol` for the services' ports, and `tuple[OrderLine, ...]` (a tuple of any length). One real catch: `declared_secrets` takes `Mapping[Any, Any]`, not `Mapping[str, Any]`, because a loaded workflow has the key `True` for `on:`.

## Try it yourself

1. `.venv/bin/mypy --version` prints `mypy 1.13.0 (compiled: yes)`.
2. `.venv/bin/mypy` prints `Success: no issues found in NN source files`.
3. `printf 'def f(x: int) -> str:\n    return x\n' > /tmp/y.py && .venv/bin/mypy --strict /tmp/y.py` reports `Incompatible return value type (got "int", expected "str")`.
4. `.venv/bin/mypy --strict pipeline/pins.py` checks one file.

## Mistakes people make

- Believing hints are enforced at run time. They are not.
- Using `Any` to silence an error, which switches checking off for everything it touches.
- `# type: ignore` without an error code; it hides every error on that line, not just the one you meant.
- Forgetting the stubs package for a typed-looking library.

## Check yourself

1. Does Python check type hints when it runs? *(No; mypy does, ahead of time.)*
2. What does `strict = true` do? *(Enables all optional strict checks.)*
3. Why does the `tests.*` override relax `disallow_untyped_defs`? *(Test names are sentences; annotating every test function would be noise.)*
4. What is `types-PyYAML`? *(A stubs package with type hints for PyYAML.)*
5. What does `py.typed` signal? *(That the package ships type hints.)*

## Further reading

- mypy 1.13 documentation: https://mypy.readthedocs.io/en/v1.13.0/
- Type hints cheat sheet: https://mypy.readthedocs.io/en/v1.13.0/cheat_sheet_py3.html
