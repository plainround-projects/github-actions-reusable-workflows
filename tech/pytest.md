# pytest (with pytest-cov and coverage)

## What it is

pytest is a Python tool that finds and runs tests. A **test** is a function that runs some code and checks the result with `assert`; if the check fails, the test fails. pytest runs files named `test_*.py` and functions named `test_*`. `pytest-cov` is a plugin that uses `coverage` to measure which lines the tests ran. Pinned: pytest 9.0.3, pytest-cov 5.0.0 for the platform tools; each consumer pins only pytest 9.0.3.

## Why this repository uses it

The shared workflow needs a test command to run. Each consumer has tests so `build-test.yml` has something real to execute. The platform's own tools and workflow files are tested too: the pin checker, the ref resolver, the secrets report, and the structure of `build-test.yml` and `pin-check.yml`.

## Where it appears

| Path | What it does with pytest |
| --- | --- |
| `tests/test_pins.py`, `test_platform_refs.py`, `test_secrets_report.py` | Tools, tested against throwaway Git repositories. |
| `tests/test_setup_toolchain_action.py` | The action's metadata and its input-validation script. |
| `tests/test_build_test_workflow.py` | The reusable workflow's contract; the consumers' 8-to-10-line files; the changelog format. |
| `tests/test_pin_check_workflow.py` | Runs the workflow's shell script on small repositories. |
| `consumers/*/tests/` | Each service's tests (10, 11 and 9). |
| `pyproject.toml`, `consumers/*/pyproject.toml` | Settings. |

## How it works underneath

`python -m pytest` imports each test file, calls each `test_*` function and reports the result. A test passes if it returns without an exception. pytest rewrites `assert` so a failure shows both sides of the comparison. A **fixture** is a helper pytest creates and passes in when a test names it as a parameter (`tmp_path`, `capsys`). Coverage hooks into the interpreter and records which lines (and branches) ran.

## Walkthrough of this repository's use

### Parametrized tests of the action's script

```python
@pytest.mark.parametrize("version", ["", "3", "latest", "3.12; rm -rf /", "2.7", "3.12.7.1", "$(id)"])
def test_anything_else_is_rejected_with_an_error_that_names_the_input(version):
    result = validate(version)
    assert result.returncode == 1
    assert "python-version must look like" in result.stdout
```

`parametrize` runs the test once per value. The values include hostile text; the test proves the script treats them as data and rejects them.

### Running a script from a test

```python
def validate(version: str, requirements: str = "requirements.txt") -> subprocess.CompletedProcess[str]:
    env = {"INPUT_PYTHON_VERSION": version, "INPUT_REQUIREMENTS_FILE": requirements, "PATH": "/usr/bin:/bin"}
    return subprocess.run(["bash", str(SCRIPT)], capture_output=True, text=True, env=env, check=False)
```

The script is run exactly as the action runs it: with the inputs as environment variables, and a minimal `PATH`.

### Throwaway Git repositories

```python
def test_a_moved_tag_resolves_to_a_different_commit_but_a_sha_never_does(repo):
    original = commit(repo, "one")
    git(repo, "tag", "v1")
    moved = commit(repo, "two")
    git(repo, "tag", "-f", "v1")
    assert platform_refs.resolve(repo, "v1") == moved != original
    assert platform_refs.resolve(repo, original) == original
```

`repo` is a fixture that returns an empty Git repository in a temporary folder:

```python
@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q", "-b", "main")
    return tmp_path
```

The chain `a == b != c` means `a == b and b != c`. The test is the lesson's step 5 in miniature.

### Testing a workflow file

```python
WORKFLOW = yaml.safe_load(TEXT)
CALL = WORKFLOW[True]["workflow_call"]

def test_the_v1_input_name_is_gone_so_a_caller_still_using_it_fails_loudly():
    assert "python-version" not in CALL["inputs"]
```

PyYAML reads the key `on` as `True` (see `pyyaml.md`). The tests assert typed inputs, the optional secret, `permissions: {}` at the top and `contents: read` on the job, that no `run:` contains `${{`, and that the action reference is a full SHA.

```python
@pytest.mark.parametrize("workflow", consumers(), ids=lambda p: p.parents[2].name)
def test_a_consumer_workflow_is_under_fifteen_lines_and_only_calls_the_platform(workflow):
```

One generated test per consumer file; `ids=` gives each a readable name such as `svc-orders`.

### Running the pin-check script

`tests/test_pin_check_workflow.py` pulls the `run:` text out of `pin-check.yml` and runs it with `bash -c` in temporary folders holding workflow files with tags, branches, short hashes and digests, and checks the exit code and the lines it prints.

### Configuration and running

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
addopts = "-ra --strict-markers"
```

`make test` runs the platform tests with `--cov --cov-fail-under=95`, then each consumer: `python -m pytest -q -p no:cacheprovider consumers/svc-orders` (and the other two).

## Try it yourself

1. `.venv/bin/python -m pytest -q` ends with `68 passed` (the count can change).
2. `.venv/bin/python -m pytest tests/test_pins.py -v | head` lists test names as sentences.
3. `.venv/bin/python -m pytest -k moved_tag -v` runs the moved-tag test.
4. `cd consumers/svc-billing && ../../.venv/bin/python -m pytest -q` prints `11 passed`.
5. `.venv/bin/python -m pytest --cov --cov-report=term-missing -q | tail -12` prints the coverage table; total is above 95%.

## Mistakes people make

- Tests that depend on the machine's Git identity; these tests pass identities through environment variables.
- Tests that leave files behind; `tmp_path` and `mktemp` avoid it.
- `assert x == y` on floats; money here is cents or `Decimal`.
- Running the consumers' tests from the repository root with the wrong `pythonpath`.

## Check yourself

1. What makes a function a test? *(A name starting with `test` in a file starting with `test_`.)*
2. What is `tmp_path`? *(A fixture that gives a fresh temporary folder.)*
3. Why does the test pass a minimal `PATH`? *(To show the script needs nothing but basic tools.)*
4. What does `parametrize` do? *(Runs one test once for each listed value.)*
5. What does `-p no:cacheprovider` do? *(Disables pytest's cache folder so no files are left.)*

## Further reading

- pytest 9: https://docs.pytest.org/en/9.0.x/
- pytest-cov 5.0: https://pytest-cov.readthedocs.io/en/v5.0.0/
- coverage.py: https://coverage.readthedocs.io/
