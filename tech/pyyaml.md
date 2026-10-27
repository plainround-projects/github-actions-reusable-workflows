# PyYAML

## What it is

PyYAML is a Python **library**: code someone else wrote that you install and import. It reads YAML text (see `yaml.md`) and turns it into Python dictionaries, lists, strings and numbers. This repository pins version 6.0.2.

<!-- words -->

<details>
<summary><b>Words this note uses, in case they are new to you</b> (click to open)</summary>

- **SHA**: A family of hash functions. A Git **commit SHA** is a 40-character hexadecimal fingerprint that names one exact commit.
- **commit**: A saved snapshot of a project's files in Git, with a message and an author. Every commit has a unique 40-character name (its SHA).
- **tag**: A name attached to a commit in Git, usually a version such as `v1.0.0`. Unlike a commit's SHA, a tag can be moved to another commit.
- **repository**: A project's folder of files together with its complete history of changes. On GitHub, a repository is a page with those files, issues and pull requests.
- **secret**: A value such as a password stored in a repository's settings. Workflows can read it, but GitHub hides it in logs.
- **YAML**: A plain-text format for structured data that uses indentation instead of braces. GitHub workflows are YAML files.
- **dependency**: A package that your project needs in order to work.
- **list**: An ordered collection of values written one after another.
- **boolean**: A value that is either true or false.
- **UTF-8**: The usual way of storing text as bytes, able to represent every written language.
- **version**: A number such as `1.2.3` that names one release of software (major.minor.patch).
- **assert**: A statement that checks something is true and fails loudly if it is not.
- **runtime**: The program that runs your code (Node.js runs JavaScript).
- **dictionary**: A Python mapping from keys to values, written `{"key": value}`.

</details>

<!-- /words -->

## Why this repository uses it

Three tools read workflow files as data. `pipeline/pins.py` checks that every `uses:` names a full commit SHA, a local path or a digest. `pipeline/platform_refs.py` finds the references a consumer's workflow makes to this platform (and follows them into the reusable workflow and the action). `pipeline/secrets_report.py` reads each consumer's `secrets:` form and the shared workflow's declarations. The tests also assert facts about `build-test.yml`, the action and `pin-check.yml`. Searching text would be fragile, so they parse the YAML.

## Where it appears

| Path | What it does with PyYAML |
| --- | --- |
| `pipeline/pins.py`, `pipeline/platform_refs.py`, `pipeline/secrets_report.py` | `yaml.safe_load(...)` on workflow and action files. |
| `tests/test_build_test_workflow.py`, `test_setup_toolchain_action.py`, `test_pin_check_workflow.py` | `yaml.safe_load` then assertions. |
| `requirements.in`, `requirements.txt` | Pin `PyYAML==6.0.2` and its hashes. |
| `pyproject.toml` | Lists it as the one runtime dependency of the tools. |
| `requirements.in` | Also `types-PyYAML`, so mypy can check calls. |

## How it works underneath

PyYAML is a **parser**. It reads characters, splits them into tokens (words, colons, dashes, indentation), builds a tree, and converts the tree into Python objects. `yaml.safe_load(text)` does this with a short list of allowed types. The non-safe `yaml.load` can build any Python object named in the file, which makes loading an untrusted file a security hole; that is why only `safe_load` is used. The YAML rules PyYAML follows are version 1.1, where `on`, `yes` and `no` are booleans (see `yaml.md`).

## Walkthrough of this repository's use

```python
def declared_secrets(callee: Mapping[Any, Any]) -> set[str]:
    triggers = callee.get("on", callee.get(True)) or {}
    return set(((triggers.get("workflow_call") or {}).get("secrets") or {}).keys())
```

After `safe_load`, a workflow is a dictionary. PyYAML reads the bare key `on` as the boolean `True`, so the code looks under `"on"` and under `True`. Each `or {}` turns a missing or empty section into an empty dictionary so `.get` is safe. The result is the set of secret names the reusable workflow declares.

```python
def passes(job: Mapping[str, Any]) -> str | dict[str, Any] | None:
    value = job.get("secrets")
    if value is None or value == "inherit":
        return value
    return dict(value)
```

A calling job's `secrets:` is either absent (`None`), the word `inherit`, or a mapping of names. The three shapes become the three rows of the table: `none`, `inherit`, named.

```python
for step in (document.get("runs") or {}).get("steps") or []:
    if "uses" in step:
        yield str(step["uses"])
```

A composite action keeps its steps under `runs.steps`, a workflow under `jobs.NAME.steps`. `uses_values` reads both so the pin checker covers actions too.

```python
files = sorted(path for pattern in patterns for path in root.glob(pattern))
```

with patterns `.github/workflows/*.y*ml`, `.github/actions/**/action.y*ml` and `consumers/*/.github/workflows/*.y*ml`. `glob` finds files; `**` crosses folders; `*.y*ml` matches `.yml` and `.yaml`. Each file is read as UTF-8 text and parsed.

## Try it yourself

1. `.venv/bin/python -c "import yaml; print(yaml.__version__)"` prints `6.0.2`.
2. `.venv/bin/python -c "import yaml; print(yaml.safe_load('a: [1, 2]\nb: {c: x}'))"` prints `{'a': [1, 2], 'b': {'c': 'x'}}`.
3. `.venv/bin/python -c "import yaml; yaml.safe_load('a: !!python/object/apply:os.system [echo hi]')"` ends with a `yaml.constructor.ConstructorError`: the safe loader refuses the Python-object tag.
4. `.venv/bin/python -m pipeline.secrets_report` prints the table built from the three consumers' YAML.
5. `.venv/bin/python -m pipeline.pins` parses every workflow and action and prints the all-pinned line.

## Mistakes people make

- Using `yaml.load` without a safe loader on a file you did not write.
- Forgetting that `on:` becomes `True`.
- Reading a file without `encoding="utf-8"` and getting garbled text on Windows (the matrix tests run there).
- Installing PyYAML but not `types-PyYAML`, so mypy cannot check the calls.

## Check yourself

1. What does `safe_load` return for a mapping? *(A Python dict.)*
2. Why not `yaml.load`? *(It can construct arbitrary Python objects, so a hostile file can run code.)*
3. What is `types-PyYAML` for? *(Type hints for the library, used by mypy.)*
4. Why does `uses_values` check `"uses" in job` before looking at steps? *(A job can call a reusable workflow directly with a job-level `uses`.)*
5. Which version of the YAML rules does PyYAML follow? *(1.1.)*

## Further reading

- PyYAML documentation (pinned: 6.0.2): https://pyyaml.org/wiki/PyYAMLDocumentation
