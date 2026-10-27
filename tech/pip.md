# pip, virtual environments and lock files

## What it is

pip is the program that installs Python packages from the Python Package Index (PyPI), a public store of libraries. A **virtual environment** (venv) is a private folder holding its own Python and its own installed packages, so one project's libraries do not mix with another's. A **requirements file** lists what to install. A **lock file** is a requirements file that pins *every* package, including the ones your packages need, to exact versions, and here also to exact file hashes. pip comes with Python (the `setup-python` action and Python 3.13 both provide a recent one).

<!-- words -->

<details>
<summary><b>Words this note uses, in case they are new to you</b> (click to open)</summary>

- **repository**: A project's folder of files together with its complete history of changes. On GitHub, a repository is a page with those files, issues and pull requests.
- **workflow**: A GitHub Actions automation described in a YAML file under `.github/workflows/`. It names the events that start it and the jobs it runs.
- **CI**: Continuous integration: running checks (build, tests, linters) automatically every time code changes.
- **YAML**: A plain-text format for structured data that uses indentation instead of braces. GitHub workflows are YAML files.
- **library**: A package of ready-made code that your program calls.
- **dependency**: A package that your project needs in order to work.
- **folder**: A container for files and other folders on disk (also called a directory).
- **version**: A number such as `1.2.3` that names one release of software (major.minor.patch).
- **pytest**: A Python test framework: it finds functions named `test_...`, runs them, and reports failures.

</details>

<!-- /words -->

## Why this repository uses it

The shared workflow runs `pip install --require-hashes -r requirements.txt` in every consumer, so every consumer needs a fully pinned, hashed lock file. The `setup-toolchain` action keys its cache on the hash of that file, so it must change exactly when a dependency changes. The platform's own tools use the same discipline.

## Where it appears

| Path | What it does with pip |
| --- | --- |
| `requirements.in`, `requirements.txt` | The platform tools (PyYAML, pytest, pytest-cov, ruff, mypy, types-PyYAML, pip-audit): top-level pins and the hashed lock. |
| `consumers/svc-orders/`, `svc-billing/`, `svc-search/` `requirements.in` and `requirements.txt` | Each consumer pins only pytest 9.0.3, with its own lock. |
| `Makefile` | Creates `.venv` and installs the tools lock with `--require-hashes`. |
| `.github/workflows/build-test.yml` | `python -m pip install --require-hashes -r requirements.txt` in the consumer's folder. |
| `.github/workflows/ci.yml` | `pip install --require-hashes -r requirements.txt` for the platform's own jobs. |
| `.github/actions/setup-toolchain/action.yml` | Asks pip where its cache is: `python -m pip cache dir`. |

## How it works underneath

`python -m venv .venv` copies (or links) a Python interpreter into `.venv/bin/` and makes an empty `site-packages` folder. Running `.venv/bin/pip install X` downloads X from PyPI and unpacks it into that folder. When you run `.venv/bin/python`, `import X` finds it there. Nothing outside the folder changes. pip caches the files it downloads in a **cache directory** (`python -m pip cache dir` prints where), and `setup-python`'s `cache: pip` saves and restores that folder between CI runs.

A **hash** is a fingerprint computed from a file's bytes. If one byte differs, the fingerprint differs.

## Walkthrough of this repository's use

### The input and the lock

```text
PyYAML==6.0.2
pytest==9.0.3
pytest-cov==5.0.0
ruff==0.8.4
```

`==` pins one exact version. The lock (`requirements.txt`) lists these and everything they need, each with environment markers and hashes, for example `colorama==0.4.6 ; sys_platform == 'win32' \ --hash=sha256:...`. A consumer's lock is shorter: pytest and what it needs.

### Install with hashes

```bash
.venv/bin/pip install -q --require-hashes -r requirements.txt
```

`-q` is quiet; `--require-hashes` refuses a package that has no hash or whose download does not match; `-r FILE` reads a requirements file. In the shared workflow the step runs in the consumer's folder (`defaults.run.working-directory`), so each consumer installs its own lock.

### The cache directory, in the action

```yaml
- id: pip-dir
  shell: bash
  run: echo "path=$(python -m pip cache dir)" >> "$GITHUB_OUTPUT"
- id: cache
  uses: actions/cache@... # v6.1.0
  with:
    path: ${{ steps.pip-dir.outputs.path }}
```

`python -m pip cache dir` prints where pip keeps downloaded files (different on Linux, macOS and Windows). The step writes `path=...` to the file named by `$GITHUB_OUTPUT`, which is how a step publishes an output, and the cache step reads it. The cache key includes `hashFiles(inputs.requirements-file)`, so changing the lock changes the key.

### Why a lock

A consumer cannot be affected by a new release of a library until someone updates the lock and CI passes. With hashes, a replaced file is refused even at the same version.

<!-- walk:requirements.in -->
### `requirements.in`, line by line

Lines 1 to 8:

```text
# Tools for the platform repository itself (the pipeline package and its tests, lint and audit).

PyYAML==6.0.2
pytest==9.0.3
pytest-cov==5.0.0
ruff==0.8.4
mypy==1.13.0
types-PyYAML==6.0.12.20241230
pip-audit==2.7.3
```

The input of the lock: a comment, then the seven tools the platform repository needs, each with an exact version after `==`: PyYAML (reads YAML), pytest and pytest-cov (tests and coverage), ruff (lint and format), mypy (types), types-PyYAML (type information for PyYAML), pip-audit (vulnerability check). `uv pip compile` turns this file into the hashed `requirements.txt`.

<!-- /walk:requirements.in -->

## Try it yourself

1. `.venv/bin/pip --version` shows the pip and Python in the venv.
2. `.venv/bin/pip list | head` lists installed tools.
3. `grep -c "^[a-z]" requirements.txt consumers/svc-orders/requirements.txt` counts locked packages (the tools lock is much longer).
4. `python3 -m pip cache dir` prints pip's cache folder on your machine.
5. `head -3 consumers/svc-orders/requirements.txt` shows the header and the first marker line (`colorama ... sys_platform == 'win32'`).

## Mistakes people make

- Running `pip install` without a venv and changing the system Python.
- Forgetting to activate or to call `.venv/bin/pip`, then installing into the wrong place.
- Hand-editing a lock file; regenerate it (see `uv.md`).
- Using `--require-hashes` with a file that has an unhashed line: pip stops with an error.
- Assuming a lock made on macOS works on Windows; a non-universal lock misses `colorama` and the like. This one is universal.

## Check yourself

1. What does a virtual environment isolate? *(The installed packages and the interpreter copy, per project.)*
2. What does `--require-hashes` guarantee? *(Every installed file matches a hash in the file.)*
3. What does `; sys_platform == 'win32'` mean? *(The package is installed only on Windows.)*
4. What does `-r requirements.txt` do? *(Installs every package listed in that file.)*
5. Why does changing `requirements.txt` cause a cache miss? *(The cache key contains the file's hash.)*

## Further reading

- pip user guide, requirement specifiers, hash-checking mode: https://pip.pypa.io/en/stable/topics/secure-installs/
- `venv`: https://docs.python.org/3.12/library/venv.html
- Environment markers: https://peps.python.org/pep-0508/
