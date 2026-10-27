# pytest (with pytest-cov and coverage)

## What it is

pytest is a Python tool that finds and runs tests. A **test** is a function that runs some code and checks the result with `assert`; if the check fails, the test fails. pytest runs files named `test_*.py` and functions named `test_*`. `pytest-cov` is a plugin that uses `coverage` to measure which lines the tests ran. Pinned: pytest 9.0.3, pytest-cov 5.0.0 for the platform tools; each consumer pins only pytest 9.0.3.

<!-- words -->

<details>
<summary><b>Words this note uses, in case they are new to you</b> (click to open)</summary>

- **shell**: The program inside a terminal that reads what you type and starts other programs. Bash is a shell.
- **process**: A program while it is running, with its own memory. Starting a program creates a process; when it ends the process is gone.
- **standard output**: The stream where a program writes its normal results (its counterpart, standard error, is for problems).
- **regular expression**: A compact pattern that describes text, such as `^[0-9]{12}$` (exactly twelve digits). Tools use them to find or check text. Often shortened to **regex**.
- **SHA**: A family of hash functions. A Git **commit SHA** is a 40-character hexadecimal fingerprint that names one exact commit.
- **tag**: A name attached to a commit in Git, usually a version such as `v1.0.0`. Unlike a commit's SHA, a tag can be moved to another commit.
- **runner**: The computer, usually a virtual machine, on which GitHub runs a job. It starts clean for every job.
- **secret**: A value such as a password stored in a repository's settings. Workflows can read it, but GitHub hides it in logs.
- **JSON**: A plain-text format for structured data: objects `{ "name": "value" }`, lists `[1, 2]`, texts in double quotes, numbers, `true`, `false`, `null`. It has no comments.
- **YAML**: A plain-text format for structured data that uses indentation instead of braces. GitHub workflows are YAML files.
- **image**: A read-only package that holds everything needed to start a container: a file system plus settings. A running **container** is made from an image.
- **Docker**: A tool that builds images and runs containers.
- **package**: In Python, a folder with an `__init__.py` file that can be imported as a unit; also a bundle of code installed with pip.
- **module**: A file, or a folder of files, that other code can load and use. In Terraform, a module is a folder of configuration used like a function.
- **function**: A named piece of code that takes inputs (parameters), does something, and may return a result.
- **class**: A blueprint for objects: it bundles data and the functions that work on it. `new Name(...)` or `Name(...)` makes an object from it.
- **list**: An ordered collection of values written one after another.
- **string**: A piece of text in a program.
- **boolean**: A value that is either true or false.
- **folder**: A container for files and other folders on disk (also called a directory).
- **assert**: A statement that checks something is true and fails loudly if it is not.
- **framework**: A large library that decides the overall shape of an application.
- **decorator**: A line starting with `@` placed above a Python function or class that changes how it behaves, for example `@dataclass`.
- **docstring**: A text in triple quotes at the start of a Python file, class or function that documents it; tools and people can read it.
- **comprehension**: A short way to build a list, set or dictionary from a loop in one expression, such as `[x * 2 for x in items if x > 0]`.
- **f-string**: A Python text written `f"...{value}..."` in which the parts in braces are replaced by their values.
- **exception**: An error raised while a program runs (`raise ValueError("message")`). Code can catch it with `try`/`except`; if nobody catches it the program stops.
- **tuple**: An unchangeable ordered list of values in Python, written `(a, b)`.
- **dictionary**: A Python mapping from keys to values, written `{"key": value}`.
- **Protocol**: A Python type that describes the methods something must have; any class with those methods satisfies it without inheriting from it.

</details>

<!-- /words -->

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

<!-- walk:consumers/svc-orders/tests/test_orders.py -->
### `consumers/svc-orders/tests/test_orders.py`, line by line

Lines 1 to 6:

```python
import pytest

from orders.application.place_order import PlaceOrder
from orders.domain.order import Order, OrderError, OrderLine
from orders.infrastructure.memory_repository import InMemoryOrders
from orders.interfaces.cli import main
```

Imports. `import pytest` loads the test framework (needed here for `pytest.mark.parametrize` and `pytest.raises`). The other lines import the code under test from each layer of the orders service; they work because `pyproject.toml` puts `src` on the import path.

Lines 9 to 15:

```python
def test_a_line_total_is_quantity_times_unit_price():
    assert OrderLine("pen", 3, 125).total_cents == 375

def test_an_order_total_sums_its_lines():
    order = Order("o-1", (OrderLine("pen", 2, 100), OrderLine("pad", 1, 450)))
    assert order.total_cents == 650
```

Two plain tests. pytest finds every function whose name starts with `test_` in files named `test_*.py` and runs it; no class or registration is needed. A bare `assert condition` is the check: if the condition is false, pytest shows the values on both sides and marks the test failed. Test 1: an `OrderLine("pen", 3, 125)` (three pens at 125 cents) has `total_cents == 375`. Test 2: an `Order` whose lines are 2 x 100 and 1 x 450 totals 650.

Lines 18 to 29:

```python
@pytest.mark.parametrize(
    "build",
    [
        lambda: OrderLine("", 1, 1),
        lambda: OrderLine("pen", 0, 1),
        lambda: OrderLine("pen", 1, -1),
        lambda: Order("o-1", ()),
    ],
)
def test_invalid_orders_are_rejected_with_a_named_error(build):
    with pytest.raises(OrderError):
        build()
```

`@pytest.mark.parametrize("build", [...])` is a decorator that runs one test several times, once for each value in the list; here each value is a **lambda**, a small unnamed function (`lambda: OrderLine("", 1, 1)` builds an invalid line when called). The four cases: an empty sku, a quantity of 0, a negative price, an order with no lines (`()` is an empty tuple). Inside, `with pytest.raises(OrderError):` is a **context manager** that passes the test only if the code in its body raises `OrderError`; here the body calls the lambda.

Lines 32 to 39:

```python
def test_placing_an_order_stores_it_and_a_duplicate_id_is_refused():
    place = PlaceOrder(InMemoryOrders())
    assert place("o-1", [("pen", 1, 100)]).total_cents == 100
    repository = InMemoryOrders()
    place = PlaceOrder(repository)
    place("o-1", [("pen", 1, 100)])
    with pytest.raises(KeyError):
        place("o-1", [("pen", 1, 100)])
```

Placing an order. `place = PlaceOrder(InMemoryOrders())` wires the use case to the in-memory store. The first check: the returned order's total is 100. Then a fresh repository and use case, the order id `o-1` is placed once, and placing it a second time must raise `KeyError`.

Lines 42 to 54:

```python
def test_the_command_prints_the_total_in_currency_units(capsys):
    assert main(["o-9", "pen:2:150", "pad:1:50"]) == 0
    assert capsys.readouterr().out.strip() == "o-9: 3.50"

def test_the_command_reports_an_invalid_order_with_exit_code_1(capsys):
    assert main(["o-9", "pen:0:150"]) == 1
    assert "at least 1" in capsys.readouterr().err

def test_the_command_without_arguments_is_a_usage_error(capsys):
    assert main([]) == 2
    assert "usage" in capsys.readouterr().err
```

The command-line tests use pytest's built-in **fixture** `capsys`. A fixture is a helper that pytest builds and passes to a test that names it as a parameter. `capsys` captures what the code writes to standard output and standard error; `capsys.readouterr()` returns an object with `.out` and `.err`. Test 1: `main(["o-9", "pen:2:150", "pad:1:50"])` returns 0 and prints `o-9: 3.50` (2 x 150 + 1 x 50 = 350 cents). Test 2: quantity 0 returns 1 and the error text contains `at least 1`. Test 3: no arguments returns 2 and the error text contains `usage`.

<!-- /walk:consumers/svc-orders/tests/test_orders.py -->

<!-- walk:consumers/svc-billing/tests/test_billing.py -->
### `consumers/svc-billing/tests/test_billing.py`, line by line

Lines 1 to 12:

```python
from decimal import Decimal

import pytest

from billing.application.issue_invoice import IssueInvoice
from billing.domain.invoice import Invoice, InvoiceError, InvoiceLine
from billing.infrastructure.memory_repository import InMemoryInvoices
from billing.interfaces.cli import main

def invoice(rate="0.0825"):
    return Invoice("i-1", (InvoiceLine("widget", 3, Decimal("19.99")),), Decimal(rate))
```

Imports (`Decimal` for exact numbers) and a helper `invoice(rate="0.0825")` that builds an invoice of three `widget`s at 19.99 with a tax rate that can be overridden. A parameter with a default value (`rate="0.0825"`) can be left out when calling.

Lines 15 to 23:

```python
def test_the_subtotal_is_exact_and_the_tax_is_rounded_half_even_once():
    assert invoice().subtotal == Decimal("59.97")
    assert invoice().tax == Decimal("4.95")
    assert invoice().total == Decimal("64.92")

def test_half_a_cent_rounds_to_the_even_cent():
    assert Invoice("i-2", (InvoiceLine("x", 1, Decimal("0.25")),), Decimal("0.10")).tax == Decimal("0.02")
    assert Invoice("i-3", (InvoiceLine("x", 1, Decimal("0.35")),), Decimal("0.10")).tax == Decimal("0.04")
```

Money tests. 3 x 19.99 is exactly 59.97; tax is 59.97 x 0.0825 = 4.9475 rounded to 4.95; the total is 64.92. The next test shows round-half-even: 0.25 x 0.10 = 0.025 rounds to **0.02** (the even neighbour of 0.02 and 0.03) and 0.35 x 0.10 = 0.035 rounds to **0.04**.

Lines 26 to 37:

```python
@pytest.mark.parametrize(
    "build",
    [
        lambda: InvoiceLine("x", 0, Decimal(1)),
        lambda: InvoiceLine("x", 1, Decimal(-1)),
        lambda: Invoice("i", (), Decimal("0.1")),
        lambda: invoice("1.5"),
    ],
)
def test_invalid_invoices_are_rejected_with_a_named_error(build):
    with pytest.raises(InvoiceError):
        build()
```

Four invalid cases through `parametrize`: a quantity of 0, a negative price, an invoice with no lines, and a tax rate of 1.5 (the helper's rate argument). Each must raise `InvoiceError`.

Lines 40 to 49:

```python
def test_issuing_stores_the_invoice_and_refuses_a_duplicate_id():
    issue = IssueInvoice(InMemoryInvoices())
    issue("i-1", "0.05", [("a", 1, "10.00")])
    with pytest.raises(KeyError):
        issue("i-1", "0.05", [("a", 1, "10.00")])

def test_text_that_is_not_a_number_is_an_invoice_error():
    with pytest.raises(InvoiceError, match="decimal"):
        IssueInvoice(InMemoryInvoices())("i-1", "five", [("a", 1, "10.00")])
```

Issuing: storing an invoice and then issuing the same id again raises `KeyError`; a tax rate given as the text `five` must raise `InvoiceError` whose message matches `decimal` (`match=` is a regular expression searched in the error message).

Lines 52 to 64:

```python
def test_the_command_prints_the_totals(capsys):
    assert main(["i-1", "0.0825", "widget:3:19.99"]) == 0
    assert capsys.readouterr().out.strip() == "i-1: subtotal 59.97 tax 4.95 total 64.92"

def test_the_command_reports_bad_input_with_exit_code_1(capsys):
    assert main(["i-1", "2", "widget:3:19.99"]) == 1
    assert "tax rate" in capsys.readouterr().err

def test_the_command_without_arguments_is_a_usage_error(capsys):
    assert main([]) == 2
    assert "usage" in capsys.readouterr().err
```

Command-line tests with `capsys`: a valid call prints `i-1: subtotal 59.97 tax 4.95 total 64.92` and returns 0; a tax rate of `2` returns 1 with `tax rate` in the error text; no arguments returns 2 with a usage message.

<!-- /walk:consumers/svc-billing/tests/test_billing.py -->

<!-- walk:consumers/svc-search/tests/test_search.py -->
### `consumers/svc-search/tests/test_search.py`, line by line

Lines 1 to 17:

```python
import pytest

from search.application.search_documents import SearchDocuments
from search.domain.index import Document, InvertedIndex, tokenize
from search.infrastructure.jsonl_source import JsonLinesDocuments
from search.interfaces.cli import main

DOCS = [
    Document("a", "Caching makes the build fast"),
    Document("b", "A cache key is a hash of the lock file"),
    Document("c", "Fast builds and fast tests"),
]

class ListSource:
    def documents(self):
        return DOCS
```

Imports, the sample data `DOCS` (three documents) and `ListSource`, a tiny class with a `documents()` method returning that list, enough to satisfy the `DocumentSource` protocol without any file.

Lines 20 to 34:

```python
def test_tokenizing_lowercases_and_drops_stop_words():
    assert tokenize("The Cache, and a KEY!") == ["cache", "key"]

def test_a_query_matches_documents_that_contain_every_term():
    index = InvertedIndex()
    for document in DOCS:
        index.add(document)
    assert index.search("fast build") == [("a", 2)]
    assert index.search("fast cache") == []
    assert index.search("fast") == [("c", 2), ("a", 1)]

def test_a_query_of_only_stop_words_matches_nothing():
    assert InvertedIndex().search("the and") == []
```

Index tests. `tokenize("The Cache, and a KEY!")` gives `["cache", "key"]`: lower-cased, punctuation dropped, the stop words `the`, `and`, `a` removed. Searching: `fast build` matches only document `a` (it must contain every term; the word `build` also appears as `builds` in `c`, but tokens are whole words, so `c` does not match), with score 2; `fast cache` matches nothing; `fast` matches `c` (twice) before `a` (once). A query of only stop words returns `[]`.

Lines 37 to 40:

```python
def test_the_use_case_indexes_a_source_once_and_answers_queries():
    search = SearchDocuments(ListSource())
    assert search("cache key") == [("b", 2)]
    assert search("missing") == []
```

The use case indexes a source once and answers queries: `cache key` finds only `b`, with score 2; `missing` finds nothing.

Lines 43 to 53:

```python
def test_the_file_source_reads_json_lines_and_skips_blank_lines(tmp_path):
    path = tmp_path / "docs.jsonl"
    path.write_text('{"id": "x", "text": "hello world"}\n\n{"id": "y", "text": "world"}\n', encoding="utf-8")
    assert [d.doc_id for d in JsonLinesDocuments(path).documents()] == ["x", "y"]

def test_a_malformed_line_names_the_file_and_the_line(tmp_path):
    path = tmp_path / "docs.jsonl"
    path.write_text('{"id": "x"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match=r"docs.jsonl:1"):
        list(JsonLinesDocuments(path).documents())
```

File source tests use the built-in fixture `tmp_path`, a fresh temporary folder (a `Path`) for each test. A test writes a JSON Lines file with a blank line in the middle and checks that the two documents `x` and `y` come out. A malformed line (`{"id": "x"}` has no `text`) must raise `ValueError` whose message matches `docs.jsonl:1` (the file and line number).

Lines 56 to 70:

```python
def test_the_command_prints_ids_and_scores(tmp_path, capsys):
    path = tmp_path / "docs.jsonl"
    path.write_text('{"id": "x", "text": "hello hello world"}\n{"id": "y", "text": "hello"}\n', encoding="utf-8")
    assert main([str(path), "hello"]) == 0
    assert capsys.readouterr().out.splitlines() == ["x\t2", "y\t1"]

def test_the_command_reports_a_missing_file_with_exit_code_1(tmp_path, capsys):
    assert main([str(tmp_path / "none.jsonl"), "x"]) == 1
    assert "search:" in capsys.readouterr().err

def test_the_command_without_arguments_is_a_usage_error(capsys):
    assert main([]) == 2
    assert "usage" in capsys.readouterr().err
```

Command-line tests: the output for the query `hello` is the two lines `x<TAB>2` and `y<TAB>1` (`\t` is a tab) and exit 0; a missing file gives exit 1 and a message starting `search:`; no arguments gives exit 2.

<!-- /walk:consumers/svc-search/tests/test_search.py -->

<!-- walk:tests/test_pins.py -->
### `tests/test_pins.py`, line by line

Lines 1 to 7:

```python
import subprocess
from pathlib import Path

from pipeline import pins

SHA = "a" * 40
PLATFORM = "sumitsr/platform-ci"
```

Imports: `subprocess` (to run Git in test repositories), `Path`, and `from pipeline import pins` (the module under test). `SHA = "a" * 40` repeats the letter `a` forty times: a fake commit hash. `PLATFORM` is the repository name used in the tests.

Lines 10 to 19:

```python
def write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def git(root: Path, *args: str) -> str:
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    done = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=True, env=env)
    return done.stdout.strip()
```

Test helpers (not tests: they do not start with `test_`). `write(root, relative, text)` creates a file inside a folder: `root / relative` joins paths with the `/` operator that `Path` defines; `path.parent.mkdir(parents=True, exist_ok=True)` creates the folder and any missing parents without complaining if it exists. `git(root, *args)` runs Git in a folder with author and committer names given by **environment variables** (`env=` replaces the environment of the child process), so the tests work on a machine with no Git identity configured.

Lines 22 to 30:

```python
def commit_all(root: Path, message: str) -> str:
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)
    return git(root, "rev-parse", "HEAD")

def workflow(*uses: str) -> str:
    steps = "".join(f"      - uses: {value}\n" for value in uses)
    return f"jobs:\n  j:\n    runs-on: ubuntu-latest\n    steps:\n{steps}"
```

`commit_all` stages everything (`add -A`), commits quietly (`-q`) with a message and returns the new commit's full hash (`rev-parse HEAD`). `workflow(*uses)` builds the text of a minimal workflow with one step per `uses:` value: `"".join(f"      - uses: {value}\n" for value in uses)` joins the generated lines, then it is placed into a fixed skeleton (`\n` is a line break, and the spaces make the YAML indentation).

Lines 33 to 43:

```python
def test_a_full_sha_a_local_path_and_a_digest_are_pinned():
    assert pins.is_pinned(f"actions/checkout@{SHA}")
    assert pins.is_pinned("./.github/actions/setup")
    assert pins.is_pinned("docker://rhysd/actionlint@sha256:" + "b" * 64)

def test_a_tag_a_branch_and_a_short_sha_are_not_pinned():
    assert not pins.is_pinned("actions/checkout@v4")
    assert not pins.is_pinned("actions/checkout@main")
    assert not pins.is_pinned("actions/checkout@abc1234")
```

Tests of `is_pinned`: a full SHA, a local path `./.github/actions/setup` and a Docker image pinned by a 64-character digest are pinned; a tag `@v4`, a branch `@main` and a seven-character short hash are not.

Lines 45 to 58:

```python
def test_violations_name_the_file_and_the_reference(tmp_path):
    write(tmp_path, ".github/workflows/a.yml", workflow("actions/checkout@v4", f"actions/cache@{SHA}"))
    assert pins.violations(tmp_path) == [".github/workflows/a.yml: actions/checkout@v4"]

def test_job_level_uses_composite_steps_and_consumer_workflows_are_checked(tmp_path):
    write(tmp_path, ".github/workflows/b.yml", "jobs:\n  call:\n    uses: org/repo/.github/workflows/x.yml@v1\n")
    write(tmp_path, ".github/actions/t/action.yml", "runs:\n  using: composite\n  steps:\n    - uses: x/y@v5\n")
    write(
        tmp_path,
        "consumers/svc/.github/workflows/ci.yml",
        "jobs:\n  ci:\n    uses: org/repo/.github/workflows/x.yml@v1\n",
    )
    assert len(pins.violations(tmp_path)) == 3
```

Tests of `violations`. `tmp_path` is a built-in **fixture**: a fresh empty temporary folder for each test (pytest passes it because the test names it as a parameter). Test 1: a workflow with one unpinned and one pinned step reports only `.github/workflows/a.yml: actions/checkout@v4`. Test 2: three files, each with a violation in a different place: a job-level `uses` in a workflow, a step inside a composite action file, and a consumer's workflow: `len(...) == 3` shows all three places are scanned.

Lines 61 to 74:

```python
def test_the_internal_pin_must_be_the_last_commit_that_changed_the_action(tmp_path):
    git(tmp_path, "init", "-q", "-b", "main")
    write(tmp_path, ".github/actions/tool/action.yml", "name: tool\nruns:\n  using: composite\n  steps: []\n")
    action_commit = commit_all(tmp_path, "action")
    write(tmp_path, ".github/workflows/w.yml", workflow(f"{PLATFORM}/.github/actions/tool@{action_commit}"))
    commit_all(tmp_path, "workflow")
    assert pins.internal_problems(tmp_path, PLATFORM) == []

    write(tmp_path, ".github/actions/tool/action.yml", "name: tool v2\nruns:\n  using: composite\n  steps: []\n")
    newer = commit_all(tmp_path, "action changes")
    problems = pins.internal_problems(tmp_path, PLATFORM)
    assert len(problems) == 1
    assert action_commit[:12] in problems[0]
    assert newer[:12] in problems[0]
```

Test of `internal_problems`. `git init -q -b main` creates a repository whose first branch is `main`. An action file is committed (`action_commit`), then a workflow that pins that exact commit is committed: no problems. Then the action file changes and is committed (`newer`): now exactly one problem, and its message contains the first 12 characters of both the old pin and the new commit.

Lines 77 to 92:

```python
def test_a_readme_change_does_not_make_the_internal_pin_stale(tmp_path):
    git(tmp_path, "init", "-q", "-b", "main")
    write(tmp_path, ".github/actions/tool/action.yml", "name: tool\nruns:\n  using: composite\n  steps: []\n")
    action_commit = commit_all(tmp_path, "action")
    write(tmp_path, ".github/workflows/w.yml", workflow(f"{PLATFORM}/.github/actions/tool@{action_commit}"))
    write(tmp_path, ".github/actions/tool/README.md", "docs\n")
    commit_all(tmp_path, "readme and workflow")
    assert pins.internal_problems(tmp_path, PLATFORM) == []

def test_an_internal_reference_by_tag_is_reported(tmp_path):
    git(tmp_path, "init", "-q", "-b", "main")
    write(tmp_path, ".github/actions/tool/action.yml", "name: tool\n")
    write(tmp_path, ".github/workflows/w.yml", workflow(f"{PLATFORM}/.github/actions/tool@v1"))
    commit_all(tmp_path, "all")
    assert "not pinned to a commit" in pins.internal_problems(tmp_path, PLATFORM)[0]
```

Two more edge cases. A change to the action's `README.md` must **not** make the pin stale (the README is excluded from the "last change" query). A reference by tag (`@v1`) is reported as `not pinned to a commit`.

Lines 95 to 103:

```python
def test_an_action_outside_the_allowed_list_is_reported(tmp_path):
    write(tmp_path, ".github/workflows/w.yml", workflow(f"actions/checkout@{SHA}", f"evil/stealer@{SHA}", "./local"))
    assert pins.not_allowed(tmp_path, ["actions/*"]) == [f".github/workflows/w.yml: evil/stealer@{SHA}"]

def test_the_allowlist_ignores_comments_and_blank_lines(tmp_path):
    allowlist = tmp_path / "allowed.txt"
    allowlist.write_text("# comment\n\nactions/*   # official\nowner/repo\n", encoding="utf-8")
    assert pins.read_allowlist(allowlist) == ["actions/*", "owner/repo"]
```

`not_allowed`: with the allowed pattern `actions/*`, the unlisted `evil/stealer` is reported and the local `./local` is ignored. `read_allowlist` ignores comments and blank lines and strips trailing comments: `"actions/*   # official"` becomes `actions/*`.

Lines 106 to 120:

```python
def test_main_reports_every_kind_of_problem_and_exits_1(tmp_path, capsys):
    git(tmp_path, "init", "-q", "-b", "main")
    write(tmp_path, ".github/workflows/w.yml", workflow("actions/checkout@v4"))
    write(tmp_path, "allowed.txt", "nobody/*\n")
    commit_all(tmp_path, "all")
    assert pins.main([str(tmp_path), "--internal", PLATFORM, "--allowlist", str(tmp_path / "allowed.txt")]) == 1
    err = capsys.readouterr().err
    assert "not pinned to a full commit SHA" in err
    assert "not on the allowed list" in err

def test_main_exits_0_when_everything_is_in_order(tmp_path, capsys):
    write(tmp_path, ".github/workflows/w.yml", workflow(f"actions/checkout@{SHA}"))
    assert pins.main([str(tmp_path)]) == 0
    assert "pinned" in capsys.readouterr().out
```

Tests of `main`: with an unpinned reference and a list that allows only `nobody/*`, `main` returns 1 and standard error (read with the `capsys` fixture) contains both messages; with a clean workflow it returns 0 and prints a line containing `pinned`.

<!-- /walk:tests/test_pins.py -->

<!-- walk:tests/test_platform_refs.py -->
### `tests/test_platform_refs.py`, line by line

Lines 1 to 18:

```python
import subprocess
from pathlib import Path

import pytest
from pipeline import platform_refs

PLATFORM = "sumitsr/platform-ci"
WORKFLOW = f"""
jobs:
  ci:
    uses: {PLATFORM}/.github/workflows/build-test.yml@v1
  again:
    uses: {PLATFORM}/.github/workflows/build-test.yml@v1
  other:
    uses: someone/else/.github/workflows/x.yml@v3
  pinned:
    uses: {PLATFORM}/.github/workflows/build-test.yml@{"b" * 40}
"""
```

Imports, the platform name, and `WORKFLOW`, a multi-line f-string (triple quotes) with four jobs: two identical references to `build-test.yml@v1`, one to another repository, and one pinned by a SHA of forty `b` characters. `{"b" * 40}` inside the f-string repeats the letter.

Lines 21 to 32:

```python
def git(repo: Path, *args: str) -> str:
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True, env=env
    ).stdout.strip()

def commit(repo: Path, text: str) -> str:
    (repo / "f.txt").write_text(text, encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", text)
    return git(repo, "rev-parse", "HEAD")
```

Helpers: `git(repo, *args)` (as in the previous file, compact), and `commit(repo, text)` which writes the text to `f.txt`, commits it with the text as message and returns the new commit's hash.

Lines 35 to 38:

```python
@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q", "-b", "main")
    return tmp_path
```

`@pytest.fixture` marks a function as a **fixture**: a reusable piece of test setup. Tests that name `repo` as a parameter receive its return value, here a new, empty Git repository in a temporary folder.

Lines 41 to 49:

```python
def test_only_references_to_the_platform_are_found_once_each_in_file_order():
    refs = platform_refs.platform_references(WORKFLOW, PLATFORM)
    assert [r.ref for r in refs] == ["v1", "b" * 40]
    assert refs[0].path == f"{PLATFORM}/.github/workflows/build-test.yml"

def test_a_full_sha_is_a_commit_and_a_tag_is_a_label():
    refs = platform_refs.platform_references(WORKFLOW, PLATFORM)
    assert [r.is_commit for r in refs] == [False, True]
```

Tests of `platform_references`: only the platform's own references are found, once each, in file order (`v1` then the SHA); the first one's path is the workflow inside the repository; `is_commit` is `False` for the tag and `True` for the SHA.

Lines 52 to 76:

```python
def test_a_tag_resolves_to_the_commit_it_points_at(repo):
    first = commit(repo, "one")
    git(repo, "tag", "v1")
    assert platform_refs.resolve(repo, "v1") == first

def test_a_moved_tag_resolves_to_a_different_commit_but_a_sha_never_does(repo):
    original = commit(repo, "one")
    git(repo, "tag", "v1")
    moved = commit(repo, "two")
    git(repo, "tag", "-f", "v1")
    assert platform_refs.resolve(repo, "v1") == moved != original
    assert platform_refs.resolve(repo, original) == original

def test_an_annotated_tag_resolves_to_its_commit_not_the_tag_object(repo):
    first = commit(repo, "one")
    git(repo, "tag", "-a", "v1", "-m", "release")
    assert platform_refs.resolve(repo, "v1") == first

def test_a_ref_that_names_nothing_is_an_error(repo):
    commit(repo, "one")
    with pytest.raises(LookupError, match="v9"):
        platform_refs.resolve(repo, "v9")
```

Tests of `resolve`: a tag resolves to the commit it points at. A **moved tag**: after `git tag -f v1` (`-f` forces re-pointing) `v1` resolves to the new commit, while the original commit's SHA still resolves to itself (`resolve(repo, "v1") == moved != original` is a chained comparison). An **annotated tag** (`-a`, a tag with its own message and object) still resolves to the commit, not the tag object, thanks to `^{commit}`. A name that does not exist raises `LookupError` whose message contains `v9`.

Lines 79 to 93:

```python
def test_main_prints_ref_commit_kind_and_path(repo, tmp_path_factory, capsys):
    first = commit(repo, "one")
    git(repo, "tag", "v1")
    workflow = tmp_path_factory.mktemp("w") / "ci.yml"
    workflow.write_text(f"jobs:\n  ci:\n    uses: {PLATFORM}/.github/workflows/build-test.yml@v1\n", encoding="utf-8")
    assert platform_refs.main([str(workflow), "--platform", PLATFORM, "--repo", str(repo)]) == 0
    assert capsys.readouterr().out.strip() == f"v1\t{first}\tlabel\t{PLATFORM}/.github/workflows/build-test.yml"

def test_main_exits_1_when_a_ref_does_not_resolve(repo, tmp_path_factory, capsys):
    commit(repo, "one")
    workflow = tmp_path_factory.mktemp("w") / "ci.yml"
    workflow.write_text(f"jobs:\n  ci:\n    uses: {PLATFORM}/.github/workflows/build-test.yml@v9\n", encoding="utf-8")
    assert platform_refs.main([str(workflow), "--platform", PLATFORM, "--repo", str(repo)]) == 1
    assert "v9" in capsys.readouterr().err
```

Tests of `main`. `tmp_path_factory.mktemp("w")` makes another temporary folder (a second one is needed besides the repository). Test 1 writes a workflow, runs `main` with `--platform` and `--repo`, and expects exactly one tab-separated line: `v1`, the commit, `label` (a tag), and the path. Test 2: an unknown tag `v9` makes `main` return 1 and print `v9` to standard error.

Lines 96 to 117:

```python
def test_the_closure_follows_a_reusable_workflow_to_the_action_it_uses(repo):
    inner = f"jobs:\n  j:\n    steps:\n      - uses: {PLATFORM}/.github/actions/tool@{'c' * 40}\n"
    (repo / ".github/workflows").mkdir(parents=True)
    (repo / ".github/workflows/build.yml").write_text(inner, encoding="utf-8")
    commit(repo, "release")
    git(repo, "tag", "v1")
    caller = f"jobs:\n  ci:\n    uses: {PLATFORM}/.github/workflows/build.yml@v1\n"
    with pytest.raises(LookupError, match="cccc"):
        platform_refs.closure(repo, PLATFORM, caller)

def test_the_closure_lists_the_workflow_and_the_action_each_once(repo):
    action_commit = commit(repo, "action")
    inner = f"jobs:\n  j:\n    steps:\n      - uses: {PLATFORM}/.github/actions/tool@{action_commit}\n"
    (repo / ".github/workflows").mkdir(parents=True)
    (repo / ".github/workflows/build.yml").write_text(inner, encoding="utf-8")
    commit(repo, "release")
    git(repo, "tag", "v1")
    call = f"uses: {PLATFORM}/.github/workflows/build.yml@v1"
    caller = f"jobs:\n  a:\n    {call}\n  b:\n    {call}\n"
    resolved = platform_refs.closure(repo, PLATFORM, caller)
    assert [ref.ref for ref, _ in resolved] == ["v1", action_commit]
```

Tests of `closure`. Test 1: the reusable workflow at tag `v1` itself uses the platform's action pinned to a commit made of `c` characters that does not exist in the test repository, so following the reference inside raises `LookupError` matching `cccc`. Test 2: a caller with two jobs calling the same workflow, whose content uses an action at a real commit: the result lists two references, `v1` and the action's commit, each once.

<!-- /walk:tests/test_platform_refs.py -->

<!-- walk:tests/test_secrets_report.py -->
### `tests/test_secrets_report.py`, line by line

Lines 1 to 18:

```python
from pathlib import Path

from pipeline import secrets_report

CALLEE = """
on:
  workflow_call:
    secrets:
      PACKAGE_TOKEN:
        required: false
jobs:
  j:
    runs-on: ubuntu-latest
    steps:
      - run: echo
        env:
          T: ${{ secrets.PACKAGE_TOKEN }}
"""
```

Imports and `CALLEE`, a triple-quoted text that is a small reusable workflow: it declares one optional secret `PACKAGE_TOKEN` under `on: workflow_call: secrets:` and uses it in a step's `env`.

Lines 21 to 28:

```python
def write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def consumer(secrets: str = "") -> str:
    return f"jobs:\n  ci:\n    uses: o/p/.github/workflows/build-test.yml@v1\n{secrets}"
```

Helpers: `write(root, relative, text)` (as in the other tests) and `consumer(secrets="")`, which returns the text of a calling workflow; its parameter has a default of the empty text, so a test can add a `secrets:` line.

Lines 31 to 35:

```python
def test_declared_and_referenced_secret_names_are_read_from_the_callee():
    import yaml

    assert secrets_report.declared_secrets(yaml.safe_load(CALLEE)) == {"PACKAGE_TOKEN"}
    assert secrets_report.referenced_secrets(CALLEE) == {"PACKAGE_TOKEN"}
```

`declared_secrets` of the parsed workflow and `referenced_secrets` of its text are both `{"PACKAGE_TOKEN"}` (a set literal in braces). The `import yaml` is inside the test function, which is allowed in Python and only loads the package when this test runs.

Lines 38 to 59:

```python
def test_a_caller_that_passes_nothing_lets_the_callee_read_nothing():
    row = secrets_report.row_for("svc-orders", {"uses": "x"}, {"PACKAGE_TOKEN"})
    assert (row.passed, row.readable) == ("none", "nothing")

def test_a_named_secret_is_the_only_one_the_callee_can_read():
    row = secrets_report.row_for(
        "svc-billing", {"secrets": {"PACKAGE_TOKEN": "${{ secrets.PACKAGE_TOKEN }}"}}, {"PACKAGE_TOKEN"}
    )
    assert (row.passed, row.readable) == ("PACKAGE_TOKEN (named)", "PACKAGE_TOKEN only")

def test_a_named_secret_the_callee_did_not_declare_is_reported_as_ignored():
    row = secrets_report.row_for("svc-x", {"secrets": {"OTHER": "v"}}, {"PACKAGE_TOKEN"})
    assert "OTHER not declared by the callee" in row.readable

def test_inherit_hands_over_every_secret_of_the_caller():
    row = secrets_report.row_for("svc-search", {"secrets": "inherit"}, {"PACKAGE_TOKEN"})
    assert row.passed == "inherit"
    assert "every secret in svc-search" in row.readable
    assert "never asked for" in row.readable
```

Four small tests of `row_for`, which turns one calling job into a table row. No `secrets:` key: passed `none`, readable `nothing`. One named secret that the callee declares: `PACKAGE_TOKEN (named)` and `PACKAGE_TOKEN only`. A named secret that the callee does not declare (`OTHER`): the text says `OTHER not declared by the callee`. `inherit`: passed `inherit`, and the readable text says `every secret in svc-search` and `never asked for`.

Lines 62 to 77:

```python
def test_the_report_has_one_row_per_consumer_in_name_order(tmp_path):
    write(tmp_path, ".github/workflows/build-test.yml", CALLEE)
    write(tmp_path, "consumers/svc-b/.github/workflows/ci.yml", consumer("    secrets: inherit\n"))
    write(tmp_path, "consumers/svc-a/.github/workflows/ci.yml", consumer())
    rows = secrets_report.build_rows(tmp_path, tmp_path / ".github/workflows/build-test.yml")
    assert [row.consumer for row in rows] == ["svc-a", "svc-b"]
    text = secrets_report.render(rows)
    assert text.splitlines()[0].startswith("consumer")
    assert "inherit" in text

def test_main_prints_the_table(tmp_path, capsys):
    write(tmp_path, ".github/workflows/build-test.yml", CALLEE)
    write(tmp_path, "consumers/svc-a/.github/workflows/ci.yml", consumer())
    assert secrets_report.main([str(tmp_path)]) == 0
    assert "svc-a" in capsys.readouterr().out
```

`build_rows` makes one row per consumer in name order (the files are created in the order `svc-b`, `svc-a`, but the rows come out `svc-a`, `svc-b`), `render` starts with a header line beginning `consumer` and includes `inherit`; and `main` prints a table that contains `svc-a` and returns 0.

<!-- /walk:tests/test_secrets_report.py -->

<!-- walk:tests/test_setup_toolchain_action.py -->
### `tests/test_setup_toolchain_action.py`, line by line

Lines 1 to 11:

```python
"""The composite action's contract: its metadata and its input validation script."""

import subprocess
from pathlib import Path

import pytest
import yaml

ACTION_DIR = Path(__file__).resolve().parents[1] / ".github" / "actions" / "setup-toolchain"
ACTION = yaml.safe_load((ACTION_DIR / "action.yml").read_text(encoding="utf-8"))
SCRIPT = ACTION_DIR / "validate-inputs.sh"
```

The module docstring says the file tests the composite action's contract. `Path(__file__).resolve().parents[1]` finds the repository root: `__file__` is this file's path, `.resolve()` makes it absolute, `parents[1]` is the folder two steps up (`parents[0]` is `tests`). The action file is read and parsed with `yaml.safe_load` into a dictionary named `ACTION`; `SCRIPT` is the path of the validation script.

Lines 14 to 16:

```python
def validate(version: str, requirements: str = "requirements.txt") -> subprocess.CompletedProcess[str]:
    env = {"INPUT_PYTHON_VERSION": version, "INPUT_REQUIREMENTS_FILE": requirements, "PATH": "/usr/bin:/bin"}
    return subprocess.run(["bash", str(SCRIPT)], capture_output=True, text=True, env=env, check=False)
```

`validate(version, requirements="requirements.txt")` runs the script with Bash: the inputs are passed as **environment variables** `INPUT_PYTHON_VERSION` and `INPUT_REQUIREMENTS_FILE`, with a minimal `PATH`. `capture_output=True, text=True` returns the output as text; `check=False` means a non-zero exit code does not raise an error. The return type `subprocess.CompletedProcess[str]` holds `returncode`, `stdout` and `stderr`.

Lines 19 to 25:

```python
def test_it_is_a_composite_action():
    assert ACTION["runs"]["using"] == "composite"

def test_the_python_version_input_is_required_and_the_requirements_file_has_a_default():
    assert ACTION["inputs"]["python-version"]["required"] is True
    assert ACTION["inputs"]["requirements-file"]["default"] == "requirements.txt"
```

Metadata tests: the action is `composite`; the input `python-version` is required (`is True`) and `requirements-file` defaults to `requirements.txt`.

Lines 28 to 36:

```python
def test_every_input_and_output_has_a_description():
    for section in ("inputs", "outputs"):
        for name, spec in ACTION[section].items():
            assert spec.get("description"), f"{section}.{name} has no description"

def test_it_declares_the_cache_hit_and_python_version_outputs():
    assert set(ACTION["outputs"]) == {"cache-hit", "python-version"}
    assert ACTION["outputs"]["cache-hit"]["value"] == "${{ steps.cache.outputs.cache-hit }}"
```

Every input and output has a description (the loop checks `spec.get("description")` is non-empty and gives a readable failure message if not: `assert condition, message`). The outputs are exactly `cache-hit` and `python-version`, and `cache-hit` takes its value from `steps.cache.outputs.cache-hit`.

Lines 39 to 56:

```python
def test_every_run_step_names_its_shell():
    for step in ACTION["runs"]["steps"]:
        if "run" in step:
            assert step.get("shell") == "bash", f"step without shell: {step}"

def test_inputs_reach_the_validation_step_through_the_environment():
    step = ACTION["runs"]["steps"][0]
    assert "${{" not in step["run"]
    assert step["env"]["INPUT_PYTHON_VERSION"] == "${{ inputs.python-version }}"

def test_the_cache_key_contains_the_os_the_exact_python_and_the_file_hash():
    cache = next(s for s in ACTION["runs"]["steps"] if s.get("id") == "cache")
    key = cache["with"]["key"]
    assert "runner.os" in key
    assert "steps.python.outputs.python-version" in key
    assert "hashFiles(inputs.requirements-file)" in key
```

Safety tests of the YAML: every step with a `run:` names `shell: bash` (composite action steps must); the first step's script contains no `${{` (inputs reach it only through `env:`, so a hostile version string cannot become code) and its `INPUT_PYTHON_VERSION` is `${{ inputs.python-version }}`; the cache step (found with `next(generator)`, the first item matching `id == "cache"`) builds its key from the runner OS, the exact Python version and the hash of the requirements file.

Lines 59 to 76:

```python
@pytest.mark.parametrize("version", ["3.12", "3.12.7", "3.9", "3.13"])
def test_a_version_that_looks_like_a_python_version_is_accepted(version):
    result = validate(version)
    assert result.returncode == 0
    assert version in result.stdout

@pytest.mark.parametrize("version", ["", "3", "latest", "3.12; rm -rf /", "2.7", "3.12.7.1", "$(id)"])
def test_anything_else_is_rejected_with_an_error_that_names_the_input(version):
    result = validate(version)
    assert result.returncode == 1
    assert "python-version must look like" in result.stdout

def test_an_empty_requirements_file_name_is_rejected():
    result = validate("3.12", requirements="")
    assert result.returncode == 1
    assert "requirements-file" in result.stdout
```

Tests of the validation script. For the accepted versions `3.12`, `3.12.7`, `3.9`, `3.13` the exit code is 0 and the version is echoed. For `""`, `"3"`, `"latest"`, `"3.12; rm -rf /"`, `"2.7"`, `"3.12.7.1"` and `"$(id)"` the exit code is 1 and the output says `python-version must look like`. An empty requirements-file name is rejected and the message names `requirements-file`. The hostile examples are only data given to a script that checks them with a pattern; nothing is executed.

<!-- /walk:tests/test_setup_toolchain_action.py -->

<!-- walk:tests/test_pin_check_workflow.py -->
### `tests/test_pin_check_workflow.py`, line by line

Lines 1 to 11:

```python
"""The pin-check workflow's shell script, run on small repositories built in a temporary folder."""

import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = yaml.safe_load((ROOT / ".github" / "workflows" / "pin-check.yml").read_text(encoding="utf-8"))
SCRIPT = next(step["run"] for step in WORKFLOW["jobs"]["pin-check"]["steps"] if "run" in step)
SHA = "a" * 40
```

Docstring, imports and set-up. The workflow file `pin-check.yml` is parsed; `SCRIPT` is the text of the first step that has a `run:` key (`next(...)` of a generator expression). `WORKFLOW["jobs"]["pin-check"]["steps"]` walks into the parsed dictionary.

Lines 14 to 18:

```python
def run(tmp_path: Path, workflow: str) -> subprocess.CompletedProcess[str]:
    target = tmp_path / ".github" / "workflows"
    target.mkdir(parents=True)
    (target / "w.yml").write_text(workflow, encoding="utf-8")
    return subprocess.run(["bash", "-c", SCRIPT], cwd=tmp_path, capture_output=True, text=True, check=False)
```

`run(tmp_path, workflow)` builds the folder `.github/workflows` in a temporary directory, writes `w.yml` there, and runs the workflow's own shell script with `bash -c SCRIPT` in that directory (`cwd=tmp_path`). This tests the real script without GitHub.

Lines 21 to 22:

```python
def test_it_can_be_required_by_a_ruleset_and_called_by_other_repositories():
    assert set(WORKFLOW[True]) == {"pull_request", "workflow_call"}
```

`WORKFLOW[True]` is the `on:` section (PyYAML reads the key `on` as `True`); the workflow must listen to `pull_request` (so a ruleset can require it) and `workflow_call` (so other repositories can call it).

Lines 25 to 54:

```python
def test_a_pinned_repository_passes(tmp_path):
    result = run(
        tmp_path, f"jobs:\n  j:\n    steps:\n      - uses: actions/checkout@{SHA} # v7\n      - uses: ./local\n"
    )
    assert result.returncode == 0
    assert "every uses is pinned" in result.stdout

def test_a_tag_fails_and_the_line_is_named(tmp_path):
    result = run(tmp_path, "jobs:\n  j:\n    steps:\n      - uses: actions/checkout@v4\n")
    assert result.returncode == 1
    assert "actions/checkout@v4" in result.stdout

def test_a_branch_and_a_short_hash_fail(tmp_path):
    result = run(tmp_path, "jobs:\n  j:\n    steps:\n      - uses: a/b@main\n      - uses: a/c@abc1234\n")
    assert result.returncode == 1
    assert "a/b@main" in result.stdout
    assert "a/c@abc1234" in result.stdout

def test_a_digest_pinned_image_passes(tmp_path):
    digest = "b" * 64
    result = run(tmp_path, f"jobs:\n  j:\n    steps:\n      - uses: docker://alpine@sha256:{digest}\n")
    assert result.returncode == 0

def test_a_repository_without_workflows_passes(tmp_path):
    result = subprocess.run(["bash", "-c", SCRIPT], cwd=tmp_path, capture_output=True, text=True, check=False)
    assert result.returncode == 0
```

Tests of the script: a pinned repository passes (exit 0, output contains `every uses is pinned`; a trailing `# v7` comment and a local path are fine); a tag `@v4` fails with exit 1 and the offending text is printed; a branch (`a/b@main`) and a short hash (`a/c@abc1234`) both fail and are both named; a Docker image pinned by a 64-character digest passes; a repository with no workflows folder passes.

<!-- /walk:tests/test_pin_check_workflow.py -->

<!-- walk:tests/test_build_test_workflow.py -->
### `tests/test_build_test_workflow.py`, line by line

Lines 1 to 15:

```python
"""The shared workflow's contract: its inputs, secrets, permissions and what it does with untrusted text."""

import re
from pathlib import Path

import pytest
import yaml
from pipeline import pins, secrets_report

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / ".github" / "workflows" / "build-test.yml"
TEXT = PATH.read_text(encoding="utf-8")
WORKFLOW = yaml.safe_load(TEXT)
CALL = WORKFLOW[True]["workflow_call"]
JOB = WORKFLOW["jobs"]["build-test"]
```

Docstring and set-up: the shared workflow `build-test.yml` is read as text (`TEXT`) and as parsed YAML (`WORKFLOW`). `CALL` is its `workflow_call` section (reached through the key `True`, since `on` parses as the boolean) and `JOB` the single job `build-test`. `from pipeline import pins, secrets_report` reuses the repository's own tools in the tests.

Lines 18 to 37:

```python
def test_it_is_a_reusable_workflow_with_typed_inputs():
    assert CALL["inputs"]["python"] == {
        "description": "Python version to test with, such as 3.12.",
        "type": "string",
        "required": True,
    }
    assert CALL["inputs"]["test-command"]["default"] == "pytest -q"
    assert CALL["inputs"]["report-secret-names"]["type"] == "boolean"

def test_the_v1_input_name_is_gone_so_a_caller_still_using_it_fails_loudly():
    assert "python-version" not in CALL["inputs"]

def test_the_secret_is_declared_and_optional():
    assert CALL["secrets"]["PACKAGE_TOKEN"]["required"] is False

def test_every_secret_the_workflow_reads_is_declared():
    assert secrets_report.referenced_secrets(TEXT) <= secrets_report.declared_secrets(WORKFLOW)
```

Contract of the inputs and secrets. `python` is a required string input with the exact description; `test-command` defaults to `pytest -q`; `report-secret-names` is a boolean. The version-1 input name `python-version` is gone, so a caller still using it fails loudly. The secret `PACKAGE_TOKEN` is declared and optional. Every `secrets.NAME` the file mentions is declared: `<=` between sets means "is a subset of".

Lines 40 to 59:

```python
def test_permissions_start_empty_and_the_job_adds_only_contents_read():
    assert WORKFLOW["permissions"] == {}
    assert JOB["permissions"] == {"contents": "read"}
    assert JOB["timeout-minutes"] <= 15

def test_untrusted_text_never_reaches_a_shell_command_through_an_expression():
    for step in JOB["steps"]:
        if "run" in step:
            assert "${{" not in step["run"], step

def test_the_test_command_and_the_secret_list_go_through_the_environment():
    env_names = {name for step in JOB["steps"] for name in step.get("env", {})}
    assert {"TEST_COMMAND", "SECRETS_CONTEXT", "PACKAGE_TOKEN"} <= env_names

def test_checkout_does_not_leave_the_token_in_the_git_config():
    checkout = next(s for s in JOB["steps"] if "actions/checkout" in s.get("uses", ""))
    assert checkout["with"]["persist-credentials"] is False
```

Security tests. Permissions start empty (`{}`) and the job adds only `contents: read`, with a timeout of at most 15 minutes. No `run:` step contains `${{` (untrusted text never reaches a shell command through an expression). The environment names `TEST_COMMAND`, `SECRETS_CONTEXT` and `PACKAGE_TOKEN` appear in some step (a set comprehension collects them; `<=` checks the subset). The checkout step has `persist-credentials: false`.

Lines 62 to 77:

```python
def test_the_composite_action_is_called_by_repository_path_at_a_full_commit():
    toolchain = next(s for s in JOB["steps"] if s.get("id") == "toolchain")
    reference = toolchain["uses"]
    assert reference.startswith("sumitsr/platform-ci/.github/actions/setup-toolchain@")
    assert pins.is_pinned(reference)
    assert toolchain["with"]["python-version"] == "${{ inputs.python }}"

def test_the_secret_names_step_runs_only_when_asked():
    step = next(s for s in JOB["steps"] if "secret names" in s.get("name", ""))
    assert step["if"] == "inputs.report-secret-names"

def test_the_workflow_exposes_the_cache_hit_of_the_toolchain():
    assert CALL["outputs"]["cache-hit"]["value"] == "${{ jobs.build-test.outputs.cache-hit }}"
    assert JOB["outputs"]["cache-hit"] == "${{ steps.toolchain.outputs.cache-hit }}"
```

The composite action is called by repository path at a full commit (`pins.is_pinned(reference)`), with `python-version` taken from `inputs.python`; the step that reports secret names runs only `if: inputs.report-secret-names`; the workflow exposes the toolchain's `cache-hit` output through the job.

Lines 80 to 100:

```python
def consumers() -> list[Path]:
    return sorted(ROOT.glob("consumers/*/.github/workflows/ci.yml"))

@pytest.mark.parametrize("workflow", consumers(), ids=lambda p: p.parents[2].name)
def test_a_consumer_workflow_is_under_fifteen_lines_and_only_calls_the_platform(workflow):
    assert len(workflow.read_text(encoding="utf-8").splitlines()) < 15
    jobs = yaml.safe_load(workflow.read_text(encoding="utf-8"))["jobs"]
    assert len(jobs) == 1
    job = next(iter(jobs.values()))
    assert job["uses"].startswith("sumitsr/platform-ci/.github/workflows/build-test.yml@")
    assert "steps" not in job

def test_the_changelog_tells_consumers_what_to_change_for_every_release():
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    releases = re.findall(r"^## \[(\d+\.\d+\.\d+)\]", text, flags=re.M)
    sections = re.split(r"^## \[", text, flags=re.M)[1:]
    assert releases == ["2.0.0", "1.0.0"]
    for section in sections:
        assert "### Required changes for consumers" in section
```

`consumers()` lists the three consumer workflows. `@pytest.mark.parametrize("workflow", consumers(), ids=lambda p: p.parents[2].name)` runs the next test once per consumer and names each run after the consumer's folder. Each consumer file must be under 15 lines, have exactly one job, that job must call the shared workflow with `uses` and have no `steps`. The last test reads `CHANGELOG.md`: `re.findall(r"^## \[(\d+\.\d+\.\d+)\]", text, flags=re.M)` finds release headings such as `## [2.0.0]` (`re.M` makes `^` match at each line start; `\d+` is one or more digits), `re.split` cuts the text into one piece per release, and every piece must contain `### Required changes for consumers`.

<!-- /walk:tests/test_build_test_workflow.py -->

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
