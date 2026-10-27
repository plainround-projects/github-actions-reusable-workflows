# pip-audit

## What it is

pip-audit is a Python tool that checks installed or listed packages against databases of known security problems (**vulnerabilities**) and reports any match. This repository pins pip-audit 2.7.3.

<!-- words -->

<details>
<summary><b>Words this note uses, in case they are new to you</b> (click to open)</summary>

- **exit code**: A number a program leaves behind when it ends. 0 means success; any other number means failure. Build systems read it to decide whether a step passed.
- **repository**: A project's folder of files together with its complete history of changes. On GitHub, a repository is a page with those files, issues and pull requests.
- **CI**: Continuous integration: running checks (build, tests, linters) automatically every time code changes.
- **package**: In Python, a folder with an `__init__.py` file that can be imported as a unit; also a bundle of code installed with pip.
- **list**: An ordered collection of values written one after another.
- **version**: A number such as `1.2.3` that names one release of software (major.minor.patch).
- **pytest**: A Python test framework: it finds functions named `test_...`, runs them, and reports failures.

</details>

<!-- /words -->

## Why this repository uses it

The template says dependencies are pinned and checked by the CI's audit step. Pinned versions never change by themselves, so a flaw found later would go unnoticed. While building the repository, `pip-audit` flagged `pytest==8.3.3` (the version the lesson suggested); the locks now use 9.0.3.

## Where it appears

| Path | What it does with pip-audit |
| --- | --- |
| `Makefile` | `audit`: `pip-audit --no-deps --disable-pip -r requirements.txt`. |
| `.github/workflows/ci.yml` | `make audit BIN=` in the lint job. |
| `requirements.txt` | Pins pip-audit 2.7.3. |

## How it works underneath

pip-audit reads the list of exact versions and asks a vulnerability service (by default the Python Packaging Advisory Database, through PyPI) whether each package version has a known advisory. It prints a table of findings and exits non-zero if there are any. It needs network access.

## Walkthrough of this repository's use

```bash
pip-audit --no-deps --disable-pip -r requirements.txt
```

`-r FILE` checks the packages in a requirements file instead of the environment. `--no-deps` stops pip-audit resolving dependencies itself, because the lock already lists them all. `--disable-pip` stops it calling pip to set up an environment; with a fully pinned, hashed file that is not needed. Only the platform tools' lock is audited by `make audit`; the consumers' locks contain only pytest and what pytest needs, which is a subset.

On success it prints `No known vulnerabilities found`. On failure it prints a table with the package, version, advisory id and fixed version.

## Try it yourself

1. `make audit` (needs network) ends with `No known vulnerabilities found`.
2. `.venv/bin/pip-audit --version` prints `pip-audit 2.7.3`.
3. `printf 'pytest==8.3.3\n' > /tmp/old.txt && .venv/bin/pip-audit --no-deps --disable-pip -r /tmp/old.txt` lists the advisory and exits 1.
4. `cd consumers/svc-orders && ../../.venv/bin/pip-audit --no-deps --disable-pip -r requirements.txt` audits a consumer's lock.

## Mistakes people make

- Running it only on the developer's machine, never in CI.
- Ignoring a finding without noting why.
- Treating "no known vulnerabilities" as "secure"; it only knows published advisories.

## Check yourself

1. What does it compare? *(Exact package versions against a database of known advisories.)*
2. Why `--no-deps`? *(The lock already lists every package.)*
3. What is its exit code when it finds something? *(Non-zero.)*
4. Why did the lock move to pytest 9.0.3? *(8.3.3 had a known advisory.)*
5. Why does it need network? *(It queries the advisory database.)*

## Further reading

- pip-audit 2.7: https://github.com/pypa/pip-audit/tree/v2.7.3#readme
