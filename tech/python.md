# Python

## What it is

Python is a programming language. You write instructions in text files ending in `.py`; a program called the **interpreter** reads them and carries them out. A **module** is one `.py` file, a **package** is a folder of modules with a name. This repository supports Python 3.10 and newer (`requires-python = ">=3.10"`) and was developed with 3.13.

<!-- words -->

<details>
<summary><b>Words this note uses, in case they are new to you</b> (click to open)</summary>

- **command line**: The text you type after the prompt in a terminal to run a program, such as `npm test`. The words after the program name are its **arguments**; words that start with `-` or `--` are **options** (also called flags).
- **environment variable**: A named piece of text that is handed to a program by whoever starts it, for example `HOME` or `CI`. Programs read them to learn about the setting they run in.
- **process**: A program while it is running, with its own memory. Starting a program creates a process; when it ends the process is gone.
- **regular expression**: A compact pattern that describes text, such as `^[0-9]{12}$` (exactly twelve digits). Tools use them to find or check text. Often shortened to **regex**.
- **hash**: A fixed-length fingerprint computed from some data. The same data always gives the same hash; any change gives a different one. SHA-256 and SHA-1 are two ways of computing one.
- **branch**: A movable name for a line of commits in Git. `main` is the usual name of the primary line.
- **tag**: A name attached to a commit in Git, usually a version such as `v1.0.0`. Unlike a commit's SHA, a tag can be moved to another commit.
- **repository**: A project's folder of files together with its complete history of changes. On GitHub, a repository is a page with those files, issues and pull requests.
- **workflow**: A GitHub Actions automation described in a YAML file under `.github/workflows/`. It names the events that start it and the jobs it runs.
- **secret**: A value such as a password stored in a repository's settings. Workflows can read it, but GitHub hides it in logs.
- **CI**: Continuous integration: running checks (build, tests, linters) automatically every time code changes.
- **JSON**: A plain-text format for structured data: objects `{ "name": "value" }`, lists `[1, 2]`, texts in double quotes, numbers, `true`, `false`, `null`. It has no comments.
- **YAML**: A plain-text format for structured data that uses indentation instead of braces. GitHub workflows are YAML files.
- **TOML**: A plain-text settings format made of `[sections]` and `key = value` lines.
- **image**: A read-only package that holds everything needed to start a container: a file system plus settings. A running **container** is made from an image.
- **Docker**: A tool that builds images and runs containers.
- **library**: A package of ready-made code that your program calls.
- **function**: A named piece of code that takes inputs (parameters), does something, and may return a result.
- **variable**: A name for a place that holds a value which can be used later in the code.
- **string**: A piece of text in a program.
- **boolean**: A value that is either true or false.
- **file path**: The written address of a file, such as `src/main.ts`; folders are separated by `/`.
- **folder**: A container for files and other folders on disk (also called a directory).
- **version**: A number such as `1.2.3` that names one release of software (major.minor.patch).
- **test**: A small program that uses your code and checks that the answer is the one you expected.
- **dataclass**: A Python class that mostly holds data; the `@dataclass` decorator writes its constructor, equality and printed form from the list of fields.
- **comprehension**: A short way to build a list, set or dictionary from a loop in one expression, such as `[x * 2 for x in items if x > 0]`.
- **exception**: An error raised while a program runs (`raise ValueError("message")`). Code can catch it with `try`/`except`; if nobody catches it the program stops.
- **tuple**: An unchangeable ordered list of values in Python, written `(a, b)`.
- **pytest**: A Python test framework: it finds functions named `test_...`, runs them, and reports failures.
- **subprocess**: A Python standard-library module that starts other programs and collects their output.

</details>

<!-- /words -->

## Why this repository uses it

The platform's tools are Python: the checker that every `uses:` is pinned (`pipeline/pins.py`), the resolver that turns `@v1` into a commit (`pipeline/platform_refs.py`), and the secrets report (`pipeline/secrets_report.py`). The three consumer services are small Python services too, so the shared workflow has real code to build and test.

## Where it appears

| Path | What it does with Python |
| --- | --- |
| `pipeline/` | The platform's tools: pins, platform references, secrets report. |
| `tests/` | Tests of those tools, of the action's script, and of the two workflows. |
| `consumers/svc-orders/src/orders/`, `svc-billing/src/billing/`, `svc-search/src/search/` | Three small layered services (domain, application, infrastructure, interfaces). |
| `consumers/*/tests/` | Each service's own tests. |
| `pyproject.toml` | Project metadata and tool settings (see `toml.md`). |

## How it works underneath

`python -m orders o-1 pen:2:150` means "run the package `orders` as a program": the interpreter finds `orders/__main__.py`, compiles it to **bytecode** and runs it from the top. An `import` runs another module once and gives you names from it. The **standard library** (`re`, `subprocess`, `decimal`, `json`, `argparse`, `collections`) ships with Python; other libraries, such as PyYAML, are installed with pip (see `pip.md`).

Python does not check **type hints** (`order_id: str`) when it runs; mypy (see `mypy.md`) does that without running the code.

## Walkthrough of this repository's use

### Frozen dataclasses and properties (the services' domain)

```python
@dataclass(frozen=True, slots=True)
class OrderLine:
    sku: str
    quantity: int
    unit_price_cents: int

    def __post_init__(self) -> None:
        if not self.sku:
            raise OrderError("a line needs a sku")
        if self.quantity < 1:
            raise OrderError(f"quantity of {self.sku} must be at least 1")

    @property
    def total_cents(self) -> int:
        return self.quantity * self.unit_price_cents
```

`@dataclass` writes `__init__`, `__eq__` and `__repr__` from the fields. `frozen=True` makes instances read-only; `slots=True` stores the fields compactly. `__post_init__` runs right after construction and refuses bad values. `@property` lets you write `line.total_cents` (no parentheses) for a value computed on demand. Prices are whole cents: no float ever touches money.

### Exact decimal arithmetic

```python
CENT = Decimal("0.01")

@property
def tax(self) -> Decimal:
    return (self.subtotal * self.tax_rate).quantize(CENT, ROUND_HALF_EVEN)
```

`Decimal` (standard library) stores numbers in base ten, so `Decimal("0.10")` is exactly one tenth. `quantize(CENT, ROUND_HALF_EVEN)` rounds to the cent; "half even" rounds exact halves to the nearest even digit, which avoids a systematic upward bias. The text constructor `Decimal("0.01")` is used because `Decimal(0.01)` would capture the binary float's error.

### Counting and sorting

```python
self._postings: dict[str, Counter[str]] = {}
...
self._postings.setdefault(term, Counter())[document.doc_id] += 1
...
return sorted(scores.items(), key=lambda item: (-item[1], item[0]))
```

`Counter` is a dictionary that counts. `setdefault(key, default)` returns the existing value or stores and returns the default. `sorted(..., key=lambda ...)` sorts by a computed key: a `lambda` is a one-line anonymous function; the pair `(-score, id)` sorts by score descending, then id.

### Regular expressions

```python
_WORD = re.compile(r"[a-z0-9]+")
def tokenize(text: str) -> list[str]:
    return [word for word in _WORD.findall(text.lower()) if word not in STOP_WORDS]
```

`re.compile` builds a pattern once. `findall` returns every non-overlapping match. The expression in square brackets after `return` is a **list comprehension**: a compact loop with a filter.

### Protocols for ports

```python
class OrderRepository(Protocol):
    def add(self, order: Order) -> None: ...
```

A `Protocol` says "any object with this method will do". The use case depends on the protocol, the in-memory repository satisfies it, and tests can pass their own.

### Dataclass values returned by tools

```python
@dataclass(frozen=True, slots=True)
class PlatformRef:
    path: str
    ref: str

    @property
    def is_commit(self) -> bool:
        return bool(_SHA.fullmatch(self.ref))
```

`fullmatch` succeeds only if the *whole* text matches the pattern `[0-9a-f]{40}` (exactly forty hexadecimal characters).

### Running other programs

```python
def resolve(repo: Path, ref: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise LookupError(f"{ref!r} does not name a commit in {repo}")
    return result.stdout.strip()
```

`subprocess.run` starts another program. A **list** of arguments avoids a shell, so odd characters in `ref` cannot become commands. `capture_output=True, text=True` returns the output as text. `check=False` means "do not raise on a non-zero exit; I will look at `returncode`". In the f-string, `{{` and `}}` produce literal braces, so the argument is `v2^{commit}` (Git syntax for "the commit this tag points to"). `{ref!r}` inserts the text with quotes.

### A loop with a queue

```python
pending = platform_references(workflow_text, platform)
while pending:
    reference = pending.pop(0)
    ...
    pending += platform_references(text, platform)
```

`closure` follows references inside references: a workflow that uses an action that uses another action. `pop(0)` takes the front of the list; `+=` on a list appends the items of another list.

### Command lines and exit codes

```python
parser = argparse.ArgumentParser(prog="pipeline.pins")
parser.add_argument("--internal", metavar="OWNER/REPO", help="...")
args = parser.parse_args(argv)
...
return 1 if problems else 0
```

`argparse` turns the arguments into named values and prints help for you. A conditional expression `A if cond else B` picks one of two values. The module ends with `sys.exit(main())`, so the number returned becomes the process exit code that CI reads.

<!-- walk:pipeline/pins.py -->
### `pipeline/pins.py`, line by line

Lines 1 to 7:

```python
"""Checks on the ``uses:`` references of the workflows and local actions.

* every reference names a full commit SHA, a local path or a digest-pinned image (a tag can be moved by its owner);
* every reference to this repository's own composite actions pins the last commit that changed the action, so the
  workflow runs the action as it is now, not a stale version of it (``--internal``);
* every external action is on an allowed list (``--allowlist FILE``, one ``owner/repo`` pattern per line).
"""
```

The first thing in a Python file, a text in triple quotes, is the **docstring** of the module: documentation that tools and people can read (`pins.__doc__`). This one says what the module checks: every `uses:` names a full commit SHA, a local path or a digest-pinned image; references to this repository's own composite actions pin the commit where the action last changed (`--internal`); every external action is on an allowed list (`--allowlist`). A *composite action* is an action made of steps (see `github-actions.md`).

Lines 9 to 20:

```python
from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

import yaml
```

The imports. `from __future__ import annotations` makes type hints in this file be stored as text and evaluated lazily, which lets newer hint syntax (like `list[str]` and `X | None`) work on every Python version this repository supports. `import argparse` loads a standard-library module (a module is a Python file you can reuse); `argparse` reads the command line. `fnmatch` matches file-name patterns, `re` does regular expressions, `subprocess` starts other programs, `sys` gives access to the interpreter (its arguments and output streams). `from collections.abc import Iterator, Sequence` and `from typing import Any` bring in names used only in type hints. `from pathlib import Path` gives an object that represents a file path. `import yaml` loads the third-party package PyYAML (see `pyyaml.md`), which reads YAML files.

Lines 22 to 24:

```python
_PINNED = re.compile(r"[\w.-]+/[\w./-]+@[0-9a-f]{40}")
_DIGEST = re.compile(r"docker://\S+@sha256:[0-9a-f]{64}")
_SHA = re.compile(r"[0-9a-f]{40}")
```

Three **compiled regular expressions**. `re.compile(r"...")` builds a pattern object once. The `r` before the quotes makes it a **raw string**: backslashes are kept as they are, which regular expressions need. `_PINNED` matches `owner/name@` followed by exactly 40 hexadecimal characters (`[0-9a-f]{40}`; `[\w.-]` means a letter, digit, underscore, dot or hyphen). `_DIGEST` matches a Docker image reference `docker://...@sha256:` plus 64 hexadecimal characters, which names an image by the fingerprint of its content. `_SHA` is just forty hexadecimal characters. The leading underscore is a convention for "private to this file".

Lines 27 to 39:

```python
def uses_values(document: Any) -> Iterator[str]:
    """Yield every ``uses`` value of a parsed workflow or action: job-level and step-level."""
    if not isinstance(document, dict):
        return
    for job in (document.get("jobs") or {}).values():
        if "uses" in job:
            yield str(job["uses"])
        for step in job.get("steps") or []:
            if "uses" in step:
                yield str(step["uses"])
    for step in (document.get("runs") or {}).get("steps") or []:
        if "uses" in step:
            yield str(step["uses"])
```

`uses_values` is a **generator**: a function that produces values one at a time with `yield` instead of building a list. The hints `document: Any` and `-> Iterator[str]` say it takes anything and produces texts. If the parsed document is not a dictionary (`isinstance(document, dict)`), a bare `return` ends it with nothing. For every job (`(document.get("jobs") or {}).values()`: `.get` returns `None` for a missing key and `or {}` replaces `None` by an empty dictionary), it yields the job's own `uses` (a job that calls a reusable workflow) and then each step's `uses`. Finally the same for `runs.steps`, where a **composite action file** keeps its steps. `str(...)` makes sure a text comes out.

Lines 42 to 45:

```python
def definition_files(root: Path) -> list[Path]:
    """Return the workflow files and composite action files under ``root/.github``, plus the consumers' own."""
    patterns = [".github/workflows/*.y*ml", ".github/actions/**/action.y*ml", "consumers/*/.github/workflows/*.y*ml"]
    return sorted(path for pattern in patterns for path in root.glob(pattern))
```

`definition_files` finds the YAML files that define workflows and actions. `root.glob(pattern)` lists files matching a **glob** pattern (`*` any characters, `**` any folders, `.y*ml` matches `.yml` and `.yaml`): the workflows, every composite `action.yml` below `.github/actions`, and the consumers' own workflows. A double loop in one expression (`for pattern in patterns for path in root.glob(pattern)`) is a **generator expression**; `sorted(...)` makes a list in a stable order.

Lines 48 to 54:

```python
def references(root: Path) -> list[tuple[Path, str]]:
    """Return ``(file, uses-value)`` for every reference in every definition file."""
    found = []
    for file in definition_files(root):
        document = yaml.safe_load(file.read_text(encoding="utf-8"))
        found += [(file, ref) for ref in uses_values(document)]
    return found
```

`references` returns pairs `(file, uses-value)` for every definition file. `yaml.safe_load(text)` parses YAML into Python dictionaries and lists, refusing YAML that could build arbitrary objects. `file.read_text(encoding="utf-8")` reads the file as text. `found += [...]` appends a list built with a **list comprehension** `[(file, ref) for ref in uses_values(document)]`. The return hint `list[tuple[Path, str]]` means a list of pairs of (path, text).

Lines 57 to 64:

```python
def is_pinned(reference: str) -> bool:
    """Return whether a ``uses`` value is local, a digest-pinned image, or a full-SHA reference."""
    return reference.startswith("./") or bool(_DIGEST.fullmatch(reference)) or bool(_PINNED.fullmatch(reference))

def violations(root: Path) -> list[str]:
    """Return ``path: uses-value`` for each reference that is not pinned."""
    return [f"{file.relative_to(root)}: {ref}" for file, ref in references(root) if not is_pinned(ref)]
```

`is_pinned` is true when the reference starts with `./` (a local path), or matches the digest pattern entirely, or matches the pinned pattern entirely (`fullmatch` requires the whole text to match, not just a part). `bool(...)` turns a match object or `None` into `True` or `False`. `violations` returns a readable `path: reference` text for every reference that is not pinned. The `f"...{expression}..."` is an **f-string**: the parts in braces are replaced by their values; `file.relative_to(root)` shortens the path.

Lines 67 to 74:

```python
def _git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=True)
    return result.stdout.strip()

def last_change(root: Path, directory: str) -> str:
    """Return the last commit that changed ``directory``, not counting its README."""
    return _git(root, "log", "-1", "--format=%H", "--", directory, f":(exclude){directory}/README.md")
```

`_git` runs `git -C <root> <args>`: `subprocess.run([...], capture_output=True, text=True, check=True)` starts the program, collects its output as text, and raises an error if its exit code is not 0. `*args` collects extra positional arguments into a tuple, and `*args` inside the list spreads them out again. `.strip()` removes the final line break. `last_change` asks Git for the last commit that changed a directory: `log -1 --format=%H` prints only the full hash of the newest commit, and after `--` come the paths: the directory itself and `:(exclude)<directory>/README.md`, a **pathspec** that removes the README from consideration (editing the README does not change the action, so it must not make the pin stale).

Lines 77 to 95:

```python
def internal_problems(root: Path, platform: str) -> list[str]:
    """Return a message for each reference to this repository's own actions that is not at the action's last change."""
    problems = []
    prefix = f"{platform}/.github/actions/"
    for file, ref in references(root):
        if not ref.startswith(prefix) or "@" not in ref:
            continue
        path, _, pinned = ref.partition("@")
        directory = path.removeprefix(f"{platform}/")
        if not _SHA.fullmatch(pinned):
            problems.append(f"{file.relative_to(root)}: {ref} is not pinned to a commit")
            continue
        expected = last_change(root, directory)
        if pinned != expected:
            problems.append(
                f"{file.relative_to(root)}: {path} is pinned to {pinned[:12]}, "
                f"but the action last changed in {expected[:12]}"
            )
    return problems
```

`internal_problems` checks the repository's own actions. `prefix` is, for example, `sumitsr/platform-ci/.github/actions/`. For each reference that starts with that prefix and has an `@`: `ref.partition("@")` splits the text into the part before `@`, the `@` itself and the part after; `_` is the conventional name for a value we do not use. `path.removeprefix(...)` cuts the repository name off, leaving the folder inside the repository. If what follows `@` is not a full SHA, that is a problem and `continue` skips to the next reference. Otherwise `last_change` gives the commit where the action last changed; if the pin differs, the message shows the first twelve characters of both (`pinned[:12]` is a **slice**: characters 0 to 11).

Lines 98 to 107:

```python
def not_allowed(root: Path, allowlist: Sequence[str]) -> list[str]:
    """Return ``path: uses-value`` for each external reference whose ``owner/repo`` matches no allowed pattern."""
    found = []
    for file, ref in references(root):
        if ref.startswith(("./", "docker://")):
            continue
        slug = "/".join(ref.partition("@")[0].split("/")[:2])
        if not any(fnmatch.fnmatchcase(slug, pattern) for pattern in allowlist):
            found.append(f"{file.relative_to(root)}: {ref}")
    return found
```

`not_allowed` checks external actions against a list of patterns. References starting with `./` or `docker://` are skipped (`startswith` accepts a tuple of prefixes). The `slug` is `owner/repo`: take the text before `@`, split it at `/` and keep the first two pieces. `any(fnmatch.fnmatchcase(slug, pattern) for pattern in allowlist)` is true if at least one pattern matches (`fnmatchcase` does case-sensitive shell-style matching; `*` is a wildcard).

Lines 110 to 113:

```python
def read_allowlist(path: Path) -> list[str]:
    """Read one pattern per line, ignoring blank lines and ``#`` comments."""
    lines = (line.split("#", 1)[0].strip() for line in path.read_text(encoding="utf-8").splitlines())
    return [line for line in lines if line]
```

`read_allowlist` reads a file of patterns, one per line. The first line is a generator expression: for each line of the file take the part before any `#` (`split("#", 1)[0]`) and trim it. The second line keeps only the non-empty ones, so blank lines and comments are ignored.

Lines 116 to 139:

```python
def main(argv: Sequence[str] | None = None) -> int:
    """Run the requested checks; exit 1 and list every problem when there is one."""
    parser = argparse.ArgumentParser(prog="pipeline.pins", description=__doc__.splitlines()[0] if __doc__ else "")
    parser.add_argument("root", nargs="?", type=Path, default=Path("."))
    parser.add_argument("--internal", metavar="OWNER/REPO", help="also check pins of this repository's own actions")
    parser.add_argument("--allowlist", type=Path, help="also check every external action against this list")
    args = parser.parse_args(argv)

    problems = [f"not pinned to a full commit SHA: {line}" for line in violations(args.root)]
    if args.internal:
        problems += [f"stale internal pin: {line}" for line in internal_problems(args.root, args.internal)]
    if args.allowlist:
        problems += [
            f"action not on the allowed list: {line}" for line in not_allowed(args.root, read_allowlist(args.allowlist))
        ]
    for line in problems:
        print(line, file=sys.stderr)
    if not problems:
        print(
            "pins: every uses: is pinned"
            + (", fresh" if args.internal else "")
            + (", allowed" if args.allowlist else "")
        )
    return 1 if problems else 0
```

`main` is the command-line entry point; `argv: Sequence[str] | None = None` means it takes a list of texts or nothing. `argparse.ArgumentParser(...)` describes the command line: `root` is an optional positional argument (`nargs="?"`) of type `Path` defaulting to `.`; `--internal OWNER/REPO` and `--allowlist FILE` are options. `parser.parse_args(argv)` reads `sys.argv` when `argv` is `None`. The problems list starts with the unpinned references, then adds stale internal pins if `--internal` was given and unlisted actions if `--allowlist` was given. Each problem is printed to standard error (`file=sys.stderr`). With no problems, a success line is printed whose ending depends on which checks ran (`+ (", fresh" if ... else "")`). The function returns 1 when there were problems, else 0: that is the **exit code**.

Lines 142 to 143:

```python
if __name__ == "__main__":
    sys.exit(main())
```

`if __name__ == "__main__":` is true only when the file is run directly (`python -m pipeline.pins`), not when it is imported by another file. `sys.exit(main())` ends the program with `main`'s return value as the exit code.

<!-- /walk:pipeline/pins.py -->

<!-- walk:pipeline/platform_refs.py -->
### `pipeline/platform_refs.py`, line by line

Lines 1 to 6:

```python
"""Find the references a workflow makes to this platform and resolve each to the commit it names right now.

GitHub resolves ``@v1`` when a run starts, so a tag that was moved gives a different commit than yesterday, while a
full SHA always gives the same one. ``scripts/run_consumer.sh`` uses this to run a consumer locally with ``act``
against exactly the commits GitHub would pick.
"""
```

The docstring explains the purpose: GitHub resolves a tag like `@v1` when a run starts, so a moved tag gives a different commit than yesterday, while a full SHA always gives the same one. `scripts/run_consumer.sh` uses this module to run a consumer locally with `act` against exactly the commits GitHub would pick.

Lines 8 to 22:

```python
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import yaml

from pipeline.pins import uses_values

_SHA = re.compile(r"[0-9a-f]{40}")
```

Imports as in `pins.py`, plus `dataclass` (below) and `from pipeline.pins import uses_values`, which reuses the generator of the previous file. `pipeline.pins` is a **package path**: the folder `pipeline` with its `__init__.py` file makes it a package, and `pins` is a module in it. The regular expression `_SHA` matches forty hexadecimal characters.

Lines 25 to 35:

```python
@dataclass(frozen=True, slots=True)
class PlatformRef:
    """One ``uses:`` of the platform: the path inside the repository and the ref as written (tag, branch or SHA)."""

    path: str
    ref: str

    @property
    def is_commit(self) -> bool:
        """Whether the ref is a full commit SHA, which can never point somewhere else."""
        return bool(_SHA.fullmatch(self.ref))
```

`@dataclass(frozen=True, slots=True)` is a **decorator**: a line starting with `@` placed above a class or function that changes it. `dataclass` writes the boring methods of a class that only holds data (the constructor, equality, a readable text form) from the field list. `frozen=True` makes instances unchangeable; `slots=True` stores the fields compactly. Here a `PlatformRef` has two texts: `path` (the place inside the repository) and `ref` (the tag, branch or SHA as written). `@property` makes `is_commit` readable like a field (`reference.is_commit`, no parentheses) while it is computed from the others; it is true when `ref` is a full commit SHA, which can never point somewhere else.

Lines 38 to 45:

```python
def platform_references(workflow_text: str, platform: str) -> list[PlatformRef]:
    """Return every reference to ``platform`` (``owner/repo``) in a workflow, in file order, without duplicates."""
    found: list[PlatformRef] = []
    for value in uses_values(yaml.safe_load(workflow_text)):
        path, _, ref = value.partition("@")
        if path.startswith(f"{platform}/") and ref and PlatformRef(path, ref) not in found:
            found.append(PlatformRef(path, ref))
    return found
```

`platform_references` collects every `uses:` that points to this platform, in file order and without duplicates. `uses_values(yaml.safe_load(workflow_text))` gives the references; `value.partition("@")` splits into path and ref. A reference counts if the path starts with `<platform>/`, there is a ref, and it is not already in `found` (dataclasses compare by their fields). The hint `found: list[PlatformRef] = []` tells readers (and the type checker) what the empty list will hold.

Lines 48 to 58:

```python
def resolve(repo: Path, ref: str) -> str:
    """Return the commit ``ref`` names in ``repo`` right now; raise ``LookupError`` when it names nothing."""
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise LookupError(f"{ref!r} does not name a commit in {repo}")
    return result.stdout.strip()
```

`resolve(repo, ref)` asks Git which commit a name denotes: `git -C <repo> rev-parse --verify --quiet <ref>^{commit}`. `rev-parse` turns names into hashes; `--verify` requires exactly one valid answer; `--quiet` prints nothing on failure; `^{commit}` means "follow a tag to the commit it points to" (inside an f-string the braces must be doubled, `{{commit}}`, to appear literally). `check=False` means a failing exit code does not raise; the code checks `result.returncode` itself, and raises `LookupError` (a built-in exception for a missing thing) with `{ref!r}` (the text with quotes, as Python would write it). Otherwise it returns the printed hash.

Lines 61 to 65:

```python
def _file_at(repo: Path, commit: str, path: str) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(repo), "show", f"{commit}:{path}"], capture_output=True, text=True, check=False
    )
    return result.stdout if result.returncode == 0 else None
```

`_file_at(repo, commit, path)` returns the contents of a file as it was in a given commit (`git show <commit>:<path>`), or `None` when it does not exist. `str | None` is the hint for "a text or nothing". `a if condition else b` is Python's one-line choice.

Lines 68 to 88:

```python
def closure(repo: Path, platform: str, workflow_text: str) -> list[tuple[PlatformRef, str]]:
    """Return every ``(reference, commit)`` a workflow needs, following the references inside what it references.

    A reusable workflow at a commit can itself use the platform's composite action; running the consumer needs both.
    Each distinct reference appears once.
    """
    found: list[tuple[PlatformRef, str]] = []
    pending = platform_references(workflow_text, platform)
    while pending:
        reference = pending.pop(0)
        if any(reference == seen for seen, _ in found):
            continue
        commit = resolve(repo, reference.ref)
        found.append((reference, commit))
        inside = reference.path.removeprefix(f"{platform}/")
        for candidate in (inside, f"{inside}/action.yml"):
            text = _file_at(repo, commit, candidate)
            if text is not None and candidate.endswith(".yml"):
                pending += platform_references(text, platform)
                break
    return found
```

`closure` follows references inside references. Reusable workflow A, at some commit, may itself call the platform's composite action B; to run the consumer locally, both must be fetched at the right commits. `pending` is a work list; `pending.pop(0)` takes the first item. If a reference was already handled (`any(reference == seen for seen, _ in found)`), skip it. Otherwise `resolve` gives its commit and the pair is recorded. `inside` is the path inside the platform repository; the loop tries two candidate files, the path itself (a workflow file) and `<path>/action.yml` (a composite action), reads each at that commit and, if it exists and is a `.yml` file, appends its references to `pending` and stops looking (`break`). The result lists each distinct reference once with its commit.

Lines 91 to 105:

```python
def main(argv: Sequence[str] | None = None) -> int:
    """Print ``ref<TAB>commit<TAB>kind<TAB>path`` for each platform reference a workflow file needs."""
    parser = argparse.ArgumentParser(prog="pipeline.platform_refs")
    parser.add_argument("workflow", type=Path)
    parser.add_argument("--platform", required=True, metavar="OWNER/REPO")
    parser.add_argument("--repo", type=Path, default=Path("."), help="the platform repository to resolve refs in")
    args = parser.parse_args(argv)
    try:
        for reference, commit in closure(args.repo, args.platform, args.workflow.read_text(encoding="utf-8")):
            kind = "commit" if reference.is_commit else "label"
            print(f"{reference.ref}\t{commit}\t{kind}\t{reference.path}")
    except LookupError as error:
        print(f"platform_refs: {error}", file=sys.stderr)
        return 1
    return 0
```

`main` builds the command line: a required positional `workflow` file, a required `--platform OWNER/REPO`, and `--repo` (default `.`) for the platform clone in which to resolve refs. In a `try`/`except LookupError` block, it prints one tab-separated line per reference: the ref, the commit, the kind (`commit` if the ref is a SHA, else `label`) and the path (`\t` is a tab). If a ref names nothing, it prints the error to standard error and returns 1. Otherwise 0.

Lines 108 to 109:

```python
if __name__ == "__main__":
    sys.exit(main())
```

The usual start-up guard (see `pins.py`).

<!-- /walk:pipeline/platform_refs.py -->

<!-- walk:pipeline/secrets_report.py -->
### `pipeline/secrets_report.py`, line by line

Lines 1 to 5:

```python
"""Report what each called workflow can read, from the callers' ``secrets:`` and the callee's declarations.

Three ways a caller can pass secrets: none (the default), named ones, or ``inherit``. ``inherit`` hands over every
secret the caller can see, whether the callee asks for it or not.
"""
```

The docstring: the module reports what each called workflow can read. A caller can pass secrets in three ways: none (the default), named ones, or `inherit`, which hands over **every** secret the caller can see whether the callee asks for it or not.

Lines 7 to 18:

```python
from __future__ import annotations

import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_REFERENCE = re.compile(r"secrets\.([A-Za-z_][A-Za-z0-9_]*)")
```

Imports (the `Mapping` type is a read-only dictionary-like hint) and the regular expression `_REFERENCE`: the text `secrets.` followed by a name that starts with a letter or underscore and continues with letters, digits or underscores; the parentheses **capture** just the name.

Lines 21 to 27:

```python
@dataclass(frozen=True, slots=True)
class Row:
    """One consumer: what its workflow passes and what the shared workflow can therefore read."""

    consumer: str
    passed: str
    readable: str
```

A frozen dataclass `Row` with three texts: the consumer's name, what its workflow passes, and what the shared workflow can therefore read.

Lines 30 to 38:

```python
def declared_secrets(callee: Mapping[Any, Any]) -> set[str]:
    """Return the secret names a reusable workflow declares under ``workflow_call.secrets``."""
    triggers = callee.get("on", callee.get(True)) or {}
    return set(((triggers.get("workflow_call") or {}).get("secrets") or {}).keys())

def referenced_secrets(callee_text: str) -> set[str]:
    """Return every ``secrets.NAME`` the callee's text mentions."""
    return set(_REFERENCE.findall(callee_text))
```

`declared_secrets` returns the set of secret names that a reusable workflow declares under `on: workflow_call: secrets:`. A **set** is an unordered collection without duplicates. The key `on` has a quirk: the YAML 1.1 rules used by PyYAML read the bare word `on` as the boolean `True`, so the dictionary key may be `True`. `callee.get("on", callee.get(True))` tries the text `on` first and falls back to `True`; `or {}` guards a missing value. Then each level is looked up with `.get(...) or {}`, and `.keys()` gives the names. `referenced_secrets` finds every `secrets.NAME` in the callee's text with `_REFERENCE.findall` (it returns the captured names) and makes a set.

Lines 41 to 46:

```python
def passes(job: Mapping[str, Any]) -> str | dict[str, Any] | None:
    """Return ``"inherit"``, the named mapping, or ``None`` for the secrets a calling job passes."""
    value = job.get("secrets")
    if value is None or value == "inherit":
        return value
    return dict(value)
```

`passes(job)` returns what a calling job gives: `None` when it has no `secrets:` key, the text `"inherit"`, or a plain dictionary of the named secrets (`dict(value)` copies it).

Lines 49 to 63:

```python
def row_for(consumer: str, job: Mapping[str, Any], declared: set[str]) -> Row:
    """Describe one calling job."""
    given = passes(job)
    if given is None:
        return Row(consumer, "none", "nothing")
    if given == "inherit":
        return Row(consumer, "inherit", f"every secret in {consumer} (including ones it never asked for)")
    names = sorted(given)
    undeclared = [name for name in names if name not in declared]
    note = f" ({', '.join(undeclared)} not declared by the callee, so ignored)" if undeclared else ""
    return Row(
        consumer,
        f"{', '.join(names)} (named)",
        f"{' and '.join(n for n in names if n in declared) or 'nothing'} only{note}",
    )
```

`row_for` describes one calling job. No secrets: `none` / `nothing`. `inherit`: everything in the consumer, "including ones it never asked for". Named secrets: `names = sorted(given)` (the dictionary's keys in order), `undeclared` lists names the callee does not declare (a list comprehension with an `if`); the note says they are ignored. `', '.join(names)` glues a list into one text with commas. `' and '.join(n for n in names if n in declared) or 'nothing'` lists the secrets that are both passed and declared, or the word `nothing`.

Lines 66 to 74:

```python
def build_rows(root: Path, callee_path: Path) -> list[Row]:
    """Build one row per consumer under ``root/consumers`` from its ``ci.yml``."""
    declared = declared_secrets(yaml.safe_load(callee_path.read_text(encoding="utf-8")))
    rows = []
    for workflow in sorted(root.glob("consumers/*/.github/workflows/ci.yml")):
        consumer = workflow.parents[2].name
        jobs = yaml.safe_load(workflow.read_text(encoding="utf-8"))["jobs"]
        rows += [row_for(consumer, job, declared) for job in jobs.values() if "uses" in job]
    return rows
```

`build_rows` loads the callee's declarations once, then for each consumer workflow `consumers/*/.github/workflows/ci.yml` (sorted): `workflow.parents[2].name` is the folder name two levels above the file's folder (the consumer's name; `parents[0]` is `workflows`, `[1]` is `.github`, `[2]` is the consumer folder). It loads the `jobs` mapping and adds a row for each job that has a `uses` key (a job that calls a reusable workflow).

Lines 77 to 83:

```python
def render(rows: Sequence[Row]) -> str:
    """Render the rows as the plain-text table of the README."""
    width = max(len("consumer"), *(len(row.consumer) for row in rows))
    passed = max(len("secrets passed"), *(len(row.passed) for row in rows))
    lines = [f"{'consumer':<{width}}  {'secrets passed':<{passed}}  what the shared workflow can read"]
    lines += [f"{row.consumer:<{width}}  {row.passed:<{passed}}  {row.readable}" for row in rows]
    return "\n".join(lines)
```

`render` builds the plain-text table printed in the README. `max(len("consumer"), *(len(row.consumer) for row in rows))` finds the longest text, so the columns line up (`*` spreads the generator into the arguments of `max`). In `f"{'consumer':<{width}}"`, `:<{width}` pads the text to that width, left-aligned. `"\n".join(lines)` makes one text with line breaks.

Lines 86 to 96:

```python
def main(argv: Sequence[str] | None = None) -> int:
    """Print the table for the repository at the first argument (default: the current directory)."""
    args = list(sys.argv[1:] if argv is None else argv)
    root = Path(args[0]) if args else Path(".")
    rows = build_rows(root, root / ".github" / "workflows" / "build-test.yml")
    print(render(rows))
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

`main` reads the optional first argument as the repository root, builds the rows for the shared workflow `.github/workflows/build-test.yml`, prints the table and returns 0. `sys.argv[1:] if argv is None else argv` uses the real command line unless a list was passed (which tests do).

<!-- /walk:pipeline/secrets_report.py -->

<!-- walk:pipeline/__init__.py -->
### `pipeline/__init__.py`, line by line

Lines 1 to 1:

```python
"""Tools the platform repository's workflows and tests use: pin checks, platform references, secret reports."""
```

A package marker file. A folder of Python files becomes a **package** (importable as a unit, e.g. `import orders.domain`) when it contains a file named `__init__.py`. The text in triple quotes is the package's docstring; there is no other code. It runs once when the package is first imported. This one names the tools the platform's workflows and tests use: pin checks, platform references, secret reports. Because it exists, `python -m pipeline.pins` and `from pipeline.pins import uses_values` work.

<!-- /walk:pipeline/__init__.py -->

<!-- walk:consumers/svc-orders/src/orders/__init__.py -->
### `consumers/svc-orders/src/orders/__init__.py`, line by line

Lines 1 to 1:

```python
"""svc-orders: place orders and price them."""
```

A package marker file. A folder of Python files becomes a **package** (importable as a unit, e.g. `import orders.domain`) when it contains a file named `__init__.py`. The text in triple quotes is the package's docstring; there is no other code. It runs once when the package is first imported. The top package of the orders service. The layout `consumers/svc-orders/src/orders/{domain,application,infrastructure,interfaces}` is the same layered design as in the other services: the **domain** holds the rules and does no input or output; the **application** holds use cases and describes what it needs from the outside as a Protocol; the **infrastructure** provides real implementations (here: memory); the **interfaces** are the doors to the world (the command line). Each layer may use the ones before it, never the ones after.

<!-- /walk:consumers/svc-orders/src/orders/__init__.py -->

<!-- walk:consumers/svc-orders/src/orders/domain/__init__.py -->
### `consumers/svc-orders/src/orders/domain/__init__.py`, line by line

Lines 1 to 1:

```python
"""Order rules: lines, totals and validation. No I/O."""
```

A package marker file. A folder of Python files becomes a **package** (importable as a unit, e.g. `import orders.domain`) when it contains a file named `__init__.py`. The text in triple quotes is the package's docstring; there is no other code. It runs once when the package is first imported.

<!-- /walk:consumers/svc-orders/src/orders/domain/__init__.py -->

<!-- walk:consumers/svc-orders/src/orders/application/__init__.py -->
### `consumers/svc-orders/src/orders/application/__init__.py`, line by line

Lines 1 to 1:

```python
"""Use cases and ports. Depends on the domain only."""
```

A package marker file. A folder of Python files becomes a **package** (importable as a unit, e.g. `import orders.domain`) when it contains a file named `__init__.py`. The text in triple quotes is the package's docstring; there is no other code. It runs once when the package is first imported.

<!-- /walk:consumers/svc-orders/src/orders/application/__init__.py -->

<!-- walk:consumers/svc-orders/src/orders/infrastructure/__init__.py -->
### `consumers/svc-orders/src/orders/infrastructure/__init__.py`, line by line

Lines 1 to 1:

```python
"""Adapters for the application's ports."""
```

A package marker file. A folder of Python files becomes a **package** (importable as a unit, e.g. `import orders.domain`) when it contains a file named `__init__.py`. The text in triple quotes is the package's docstring; there is no other code. It runs once when the package is first imported.

<!-- /walk:consumers/svc-orders/src/orders/infrastructure/__init__.py -->

<!-- walk:consumers/svc-orders/src/orders/interfaces/__init__.py -->
### `consumers/svc-orders/src/orders/interfaces/__init__.py`, line by line

Lines 1 to 1:

```python
"""Command-line entry point."""
```

A package marker file. A folder of Python files becomes a **package** (importable as a unit, e.g. `import orders.domain`) when it contains a file named `__init__.py`. The text in triple quotes is the package's docstring; there is no other code. It runs once when the package is first imported.

<!-- /walk:consumers/svc-orders/src/orders/interfaces/__init__.py -->

<!-- walk:consumers/svc-orders/src/orders/__main__.py -->
### `consumers/svc-orders/src/orders/__main__.py`, line by line

Lines 1 to 7:

```python
"""``python -m orders`` entry point."""

import sys

from orders.interfaces.cli import main

sys.exit(main())
```

A file named `__main__.py` inside a package is what runs for `python -m orders`. (`-m` means "run this module as a program".) It imports the `main` function from the command-line layer and passes its return value to `sys.exit`, which ends the program with that number as the **exit code** (0 success, non-zero failure). It is the only file in the service that exits the process.

<!-- /walk:consumers/svc-orders/src/orders/__main__.py -->

<!-- walk:consumers/svc-orders/src/orders/domain/order.py -->
### `consumers/svc-orders/src/orders/domain/order.py`, line by line

Lines 1 to 6:

```python
"""An order is an id and one or more lines; prices are whole cents so no float ever touches money."""

from __future__ import annotations

from dataclasses import dataclass
```

The module docstring states the central rule: prices are whole cents so that no floating-point number ever touches money (floats cannot represent most decimal fractions exactly: `0.1 + 0.2` is `0.30000000000000004`). `from dataclasses import dataclass` loads the decorator described below.

Lines 8 to 10:

```python
class OrderError(ValueError):
    """The order breaks a rule: no lines, a non-positive quantity or a negative price."""
```

`class OrderError(ValueError):` defines a new kind of error. A **class** is a blueprint; the name in parentheses is the class it **inherits** from, so `OrderError` is a kind of `ValueError` and can be caught either way. The body is only a docstring: no extra behavior is needed, the new name is what matters, so callers can catch exactly this problem.

Lines 12 to 31:

```python
@dataclass(frozen=True, slots=True)
class OrderLine:
    """A quantity of one SKU at a price per unit, in cents."""

    sku: str
    quantity: int
    unit_price_cents: int

    def __post_init__(self) -> None:
        if not self.sku:
            raise OrderError("a line needs a sku")
        if self.quantity < 1:
            raise OrderError(f"quantity of {self.sku} must be at least 1")
        if self.unit_price_cents < 0:
            raise OrderError(f"price of {self.sku} must not be negative")

    @property
    def total_cents(self) -> int:
        """Quantity times unit price."""
        return self.quantity * self.unit_price_cents
```

`@dataclass(frozen=True, slots=True)` is a **decorator**: a line starting with `@` placed above a class that changes it. `dataclass` generates the constructor, equality and a readable text form from the field list; `frozen=True` forbids changing a field after creation; `slots=True` stores fields compactly. The three fields are written as `name: type`: `sku` (the item code, text), `quantity` (a whole number, `int`) and `unit_price_cents` (whole number). `__post_init__` is a method the dataclass calls right after building the object; here it **validates**: no `sku`, a quantity below 1, or a negative price each raise `OrderError` with a message. `self` is the object itself. An `f"...{self.sku}..."` is a formatted text. `@property` makes `total_cents` readable as `line.total_cents`, computed as quantity times price.

Lines 34 to 48:

```python
@dataclass(frozen=True, slots=True)
class Order:
    """An order with at least one line."""

    order_id: str
    lines: tuple[OrderLine, ...]

    def __post_init__(self) -> None:
        if not self.lines:
            raise OrderError("an order needs at least one line")

    @property
    def total_cents(self) -> int:
        """Sum of the line totals."""
        return sum(line.total_cents for line in self.lines)
```

`Order` has an `order_id` and `lines: tuple[OrderLine, ...]`, a tuple (an unchangeable list) of any length of order lines. Its `__post_init__` rejects an empty tuple (`not self.lines` is true for an empty one). The property `total_cents` adds up all line totals: `sum(line.total_cents for line in self.lines)` is a **generator expression** inside `sum`.

<!-- /walk:consumers/svc-orders/src/orders/domain/order.py -->

<!-- walk:consumers/svc-orders/src/orders/application/place_order.py -->
### `consumers/svc-orders/src/orders/application/place_order.py`, line by line

Lines 1 to 7:

```python
"""Use case: place an order and keep it."""

from __future__ import annotations

from typing import Protocol

from orders.domain.order import Order, OrderLine
```

Docstring, the `__future__` import (see `pins.py`), `from typing import Protocol`, and an import of the two domain classes. Note the direction: the application layer imports from the domain, never the reverse.

Lines 10 to 15:

```python
class OrderRepository(Protocol):
    """Where placed orders are kept."""

    def add(self, order: Order) -> None:
        """Store ``order``; raise ``KeyError`` when the id is already taken."""
        ...
```

`OrderRepository(Protocol)` describes, without implementing it, what the use case needs: something with a method `add(order)`. A **Protocol** is a type that any class satisfies if it has the right methods; no inheritance needed. The `...` (an *Ellipsis*) is the body, meaning "nothing here, it is only a description". This is how the application depends on an abstraction instead of on a concrete storage.

Lines 18 to 28:

```python
class PlaceOrder:
    """Build an order from raw line data and store it."""

    def __init__(self, repository: OrderRepository) -> None:
        self._repository = repository

    def __call__(self, order_id: str, lines: list[tuple[str, int, int]]) -> Order:
        """Place the order; invalid data raises :class:`~orders.domain.order.OrderError`."""
        order = Order(order_id, tuple(OrderLine(sku, quantity, price) for sku, quantity, price in lines))
        self._repository.add(order)
        return order
```

`PlaceOrder` is a class whose instances can be called like functions. `__init__` is the constructor; `self._repository = repository` stores the collaborator (the leading underscore means "internal"). `__call__` makes `place_order(order_id, lines)` work. The hint `list[tuple[str, int, int]]` says: a list of triples (sku, quantity, price in cents). It builds the `OrderLine` objects with a generator expression, builds the `Order`, asks the repository to store it, and returns the order. If the data is invalid, `OrderError` is raised by the domain classes.

<!-- /walk:consumers/svc-orders/src/orders/application/place_order.py -->

<!-- walk:consumers/svc-orders/src/orders/infrastructure/memory_repository.py -->
### `consumers/svc-orders/src/orders/infrastructure/memory_repository.py`, line by line

Lines 1 to 18:

```python
"""In-memory order storage."""

from __future__ import annotations

from orders.domain.order import Order

class InMemoryOrders:
    """Keeps orders in a dictionary for the lifetime of the process."""

    def __init__(self) -> None:
        self._orders: dict[str, Order] = {}

    def add(self, order: Order) -> None:
        """Store ``order``; raise ``KeyError`` when the id is already taken."""
        if order.order_id in self._orders:
            raise KeyError(f"order {order.order_id} already exists")
        self._orders[order.order_id] = order
```

`InMemoryOrders` satisfies the `OrderRepository` protocol (it has `add`). It keeps orders in a **dictionary** (`dict[str, Order]`, a mapping from text keys to orders) that lives only as long as the process. `self._orders: dict[str, Order] = {}` declares the type and starts empty (`{}`). `add` raises `KeyError` (the built-in error for a missing or clashing key) with a message if the id exists, otherwise stores the order under its id: `self._orders[order.order_id] = order`.

<!-- /walk:consumers/svc-orders/src/orders/infrastructure/memory_repository.py -->

<!-- walk:consumers/svc-orders/src/orders/interfaces/cli.py -->
### `consumers/svc-orders/src/orders/interfaces/cli.py`, line by line

Lines 1 to 11:

```python
"""``python -m orders ORDER_ID SKU:QUANTITY:UNIT_CENTS ...`` prints the order total."""

from __future__ import annotations

import sys
from collections.abc import Sequence

from orders.application.place_order import PlaceOrder
from orders.domain.order import OrderError
from orders.infrastructure.memory_repository import InMemoryOrders
```

The docstring shows the usage: `python -m orders ORDER_ID SKU:QUANTITY:UNIT_CENTS ...`. Imports bring in `sys` (for arguments and error output) and the other layers. This is the only layer that imports all of them, because it wires the pieces together.

Lines 13 to 26:

```python
def main(argv: Sequence[str] | None = None) -> int:
    """Run the program; return 0 on success and 1 when the order is invalid."""
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) < 2:
        print("usage: python -m orders ORDER_ID SKU:QUANTITY:UNIT_CENTS ...", file=sys.stderr)
        return 2
    try:
        lines = [(sku, int(quantity), int(price)) for sku, quantity, price in (part.split(":") for part in args[1:])]
        order = PlaceOrder(InMemoryOrders())(args[0], lines)
    except (OrderError, ValueError) as error:
        print(f"orders: {error}", file=sys.stderr)
        return 1
    print(f"{order.order_id}: {order.total_cents / 100:.2f}")
    return 0
```

`main(argv=None)` returns an integer exit code. `args = list(sys.argv[1:] if argv is None else argv)` takes the command-line words after the program name (or a list passed in by a test). With fewer than 2 arguments it prints the usage to **standard error** (`file=sys.stderr`) and returns 2. In the `try` block: for each remaining word, `part.split(":")` cuts `SKU:QUANTITY:UNIT_CENTS` into three texts; the list comprehension converts quantity and price with `int(...)` (which raises `ValueError` for non-numbers) and builds a list of triples. `PlaceOrder(InMemoryOrders())(args[0], lines)` creates the use case with an in-memory store and calls it. The `except (OrderError, ValueError) as error:` clause catches both the domain's rule errors and bad numbers, prints `orders: <message>` to standard error and returns 1. On success it prints `ORDER_ID: total` with the cents turned into currency: `order.total_cents / 100:.2f` divides by 100 and `:.2f` shows two decimals. The conversion to a float happens only for display. Returns 0.

<!-- /walk:consumers/svc-orders/src/orders/interfaces/cli.py -->

<!-- walk:consumers/svc-orders/pyproject.toml -->
### `consumers/svc-orders/pyproject.toml`, line by line

Lines 1 to 9:

```toml
[project]
name = "svc-orders"
version = "1.0.0"
description = "Place orders and price them. A consumer of the shared build-test workflow."
requires-python = ">=3.10"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

A TOML file (see `toml.md`). `[project]` names the service (`svc-orders`), its version, a description, and the oldest Python it supports (`requires-python = ">=3.10"`). `[tool.pytest.ini_options]` configures pytest: `testpaths = ["tests"]` says where the tests are, and `pythonpath = ["src"]` adds the `src` folder to Python's import search path so that `import orders` works without installing the project.

<!-- /walk:consumers/svc-orders/pyproject.toml -->

<!-- walk:consumers/svc-billing/pyproject.toml -->
### `consumers/svc-billing/pyproject.toml`, line by line

Lines 1 to 9:

```toml
[project]
name = "svc-billing"
version = "1.0.0"
description = "Issue invoices with tax. A consumer of the shared build-test workflow."
requires-python = ">=3.10"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

The same file for the billing service: name `svc-billing`, the same Python requirement, and pytest told to look in `tests` with `src` on the path.

<!-- /walk:consumers/svc-billing/pyproject.toml -->

<!-- walk:consumers/svc-search/pyproject.toml -->
### `consumers/svc-search/pyproject.toml`, line by line

Lines 1 to 9:

```toml
[project]
name = "svc-search"
version = "1.0.0"
description = "A tiny full-text index. A consumer of the shared build-test workflow."
requires-python = ">=3.10"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

The same file for the search service: name `svc-search`, the same Python requirement, and pytest told to look in `tests` with `src` on the path.

<!-- /walk:consumers/svc-search/pyproject.toml -->

<!-- walk:consumers/svc-billing/src/billing/__init__.py -->
### `consumers/svc-billing/src/billing/__init__.py`, line by line

Lines 1 to 1:

```python
"""svc-billing: issue invoices with tax."""
```

A package marker file. A folder of Python files becomes a **package** (importable as a unit, e.g. `import orders.domain`) when it contains a file named `__init__.py`. The text in triple quotes is the package's docstring; there is no other code. It runs once when the package is first imported. The billing package: issue invoices with tax.

<!-- /walk:consumers/svc-billing/src/billing/__init__.py -->

<!-- walk:consumers/svc-billing/src/billing/domain/__init__.py -->
### `consumers/svc-billing/src/billing/domain/__init__.py`, line by line

Lines 1 to 1:

```python
"""Invoice rules: lines, tax and rounding. No I/O."""
```

A package marker file. A folder of Python files becomes a **package** (importable as a unit, e.g. `import orders.domain`) when it contains a file named `__init__.py`. The text in triple quotes is the package's docstring; there is no other code. It runs once when the package is first imported.

<!-- /walk:consumers/svc-billing/src/billing/domain/__init__.py -->

<!-- walk:consumers/svc-billing/src/billing/application/__init__.py -->
### `consumers/svc-billing/src/billing/application/__init__.py`, line by line

Lines 1 to 1:

```python
"""Use cases and ports. Depends on the domain only."""
```

A package marker file. A folder of Python files becomes a **package** (importable as a unit, e.g. `import orders.domain`) when it contains a file named `__init__.py`. The text in triple quotes is the package's docstring; there is no other code. It runs once when the package is first imported.

<!-- /walk:consumers/svc-billing/src/billing/application/__init__.py -->

<!-- walk:consumers/svc-billing/src/billing/infrastructure/__init__.py -->
### `consumers/svc-billing/src/billing/infrastructure/__init__.py`, line by line

Lines 1 to 1:

```python
"""Adapters for the application ports."""
```

A package marker file. A folder of Python files becomes a **package** (importable as a unit, e.g. `import orders.domain`) when it contains a file named `__init__.py`. The text in triple quotes is the package's docstring; there is no other code. It runs once when the package is first imported.

<!-- /walk:consumers/svc-billing/src/billing/infrastructure/__init__.py -->

<!-- walk:consumers/svc-billing/src/billing/interfaces/__init__.py -->
### `consumers/svc-billing/src/billing/interfaces/__init__.py`, line by line

Lines 1 to 1:

```python
"""Command-line entry point."""
```

A package marker file. A folder of Python files becomes a **package** (importable as a unit, e.g. `import orders.domain`) when it contains a file named `__init__.py`. The text in triple quotes is the package's docstring; there is no other code. It runs once when the package is first imported.

<!-- /walk:consumers/svc-billing/src/billing/interfaces/__init__.py -->

<!-- walk:consumers/svc-billing/src/billing/__main__.py -->
### `consumers/svc-billing/src/billing/__main__.py`, line by line

Lines 1 to 7:

```python
"""``python -m billing`` entry point."""

import sys

from billing.interfaces.cli import main

sys.exit(main())
```

The `python -m billing` entry point, built exactly like the orders one: import `main`, call it, exit with its return value.

<!-- /walk:consumers/svc-billing/src/billing/__main__.py -->

<!-- walk:consumers/svc-billing/src/billing/domain/invoice.py -->
### `consumers/svc-billing/src/billing/domain/invoice.py`, line by line

Lines 1 to 8:

```python
"""An invoice prices lines with :class:`~decimal.Decimal`; tax is rounded half-even to the cent, once."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal

CENT = Decimal("0.01")
```

The docstring: an invoice prices lines with `Decimal`, and tax is rounded half-even to the cent, once. `decimal.Decimal` is Python's exact decimal number type (unlike `float`, `Decimal("0.10")` is exactly one tenth). `ROUND_HALF_EVEN` is a rounding rule ("banker's rounding"): a value exactly halfway rounds to the nearest even digit (2.665 to 2.66, 2.675 to 2.68), which avoids a systematic upward bias. `CENT = Decimal("0.01")` is the unit to round to.

Lines 11 to 12:

```python
class InvoiceError(ValueError):
    """The invoice breaks a rule: no lines, a bad quantity, a negative price or an impossible tax rate."""
```

`InvoiceError(ValueError)`: the domain's own error type, like `OrderError`.

Lines 15 to 32:

```python
@dataclass(frozen=True, slots=True)
class InvoiceLine:
    """A quantity of one item at a unit price."""

    description: str
    quantity: int
    unit_price: Decimal

    def __post_init__(self) -> None:
        if self.quantity < 1:
            raise InvoiceError(f"quantity of {self.description} must be at least 1")
        if self.unit_price < 0:
            raise InvoiceError(f"price of {self.description} must not be negative")

    @property
    def amount(self) -> Decimal:
        """Quantity times unit price, exact."""
        return self.unit_price * self.quantity
```

`InvoiceLine` is a frozen dataclass: `description` (text), `quantity` (`int`), `unit_price` (`Decimal`). `__post_init__` rejects a quantity below 1 and a negative price. The property `amount` is the price times the quantity, exact.

Lines 35 to 62:

```python
@dataclass(frozen=True, slots=True)
class Invoice:
    """Lines plus a tax rate between 0 and 1."""

    invoice_id: str
    lines: tuple[InvoiceLine, ...]
    tax_rate: Decimal

    def __post_init__(self) -> None:
        if not self.lines:
            raise InvoiceError("an invoice needs at least one line")
        if not Decimal(0) <= self.tax_rate <= Decimal(1):
            raise InvoiceError("tax rate must be between 0 and 1")

    @property
    def subtotal(self) -> Decimal:
        """Sum of the line amounts, rounded to the cent."""
        return sum((line.amount for line in self.lines), Decimal(0)).quantize(CENT, ROUND_HALF_EVEN)

    @property
    def tax(self) -> Decimal:
        """Tax on the subtotal, rounded half-even to the cent."""
        return (self.subtotal * self.tax_rate).quantize(CENT, ROUND_HALF_EVEN)

    @property
    def total(self) -> Decimal:
        """Subtotal plus tax."""
        return self.subtotal + self.tax
```

`Invoice` has an id, a tuple of lines and a `tax_rate`. Its validation rejects an empty invoice and a tax rate outside 0 to 1 (`not Decimal(0) <= self.tax_rate <= Decimal(1)` is a **chained comparison**: both must hold). `subtotal` sums the line amounts starting from `Decimal(0)` (`sum(iterable, start)`), and `.quantize(CENT, ROUND_HALF_EVEN)` rounds to two decimals using the rule above. `tax` multiplies the subtotal by the rate and rounds once. `total` adds the two. Because money is rounded at the subtotal and at the tax, and nowhere else, the three figures always add up.

<!-- /walk:consumers/svc-billing/src/billing/domain/invoice.py -->

<!-- walk:consumers/svc-billing/src/billing/application/issue_invoice.py -->
### `consumers/svc-billing/src/billing/application/issue_invoice.py`, line by line

Lines 1 to 16:

```python
"""Use case: issue an invoice and keep it."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Protocol

from billing.domain.invoice import Invoice, InvoiceError, InvoiceLine

class InvoiceRepository(Protocol):
    """Where issued invoices are kept."""

    def add(self, invoice: Invoice) -> None:
        """Store ``invoice``; raise ``KeyError`` when the id is already taken."""
        ...
```

As in orders: docstring, imports (plus `Decimal` and `InvalidOperation`, the error raised when a text is not a number), and the `InvoiceRepository` protocol with the single method `add`.

Lines 19 to 36:

```python
class IssueInvoice:
    """Build an invoice from raw text values and store it."""

    def __init__(self, repository: InvoiceRepository) -> None:
        self._repository = repository

    def __call__(self, invoice_id: str, tax_rate: str, lines: list[tuple[str, int, str]]) -> Invoice:
        """Issue the invoice; invalid data raises :class:`~billing.domain.invoice.InvoiceError`."""
        try:
            invoice = Invoice(
                invoice_id,
                tuple(InvoiceLine(description, quantity, Decimal(price)) for description, quantity, price in lines),
                Decimal(tax_rate),
            )
        except InvalidOperation as error:
            raise InvoiceError(f"not a decimal number: {error}") from error
        self._repository.add(invoice)
        return invoice
```

`IssueInvoice` is callable like `PlaceOrder`. It takes the id, the tax rate **as text** (`str`) and lines as triples `(description, quantity, price text)`, and converts with `Decimal(price)` and `Decimal(tax_rate)` (texts, so no float is involved). If conversion fails, `except InvalidOperation as error:` raises `InvoiceError(...) from error`: it turns the low-level error into the domain's error while keeping the original attached (`from error`). Then the invoice is stored and returned.

<!-- /walk:consumers/svc-billing/src/billing/application/issue_invoice.py -->

<!-- walk:consumers/svc-billing/src/billing/infrastructure/memory_repository.py -->
### `consumers/svc-billing/src/billing/infrastructure/memory_repository.py`, line by line

Lines 1 to 18:

```python
"""In-memory invoice storage."""

from __future__ import annotations

from billing.domain.invoice import Invoice

class InMemoryInvoices:
    """Keeps invoices in a dictionary for the lifetime of the process."""

    def __init__(self) -> None:
        self._invoices: dict[str, Invoice] = {}

    def add(self, invoice: Invoice) -> None:
        """Store ``invoice``; raise ``KeyError`` when the id is already taken."""
        if invoice.invoice_id in self._invoices:
            raise KeyError(f"invoice {invoice.invoice_id} already exists")
        self._invoices[invoice.invoice_id] = invoice
```

`InMemoryInvoices` is the same dictionary-backed store as in orders, keyed by `invoice_id`, raising `KeyError` for a duplicate id.

<!-- /walk:consumers/svc-billing/src/billing/infrastructure/memory_repository.py -->

<!-- walk:consumers/svc-billing/src/billing/interfaces/cli.py -->
### `consumers/svc-billing/src/billing/interfaces/cli.py`, line by line

Lines 1 to 26:

```python
"""``python -m billing INVOICE_ID TAX_RATE DESCRIPTION:QUANTITY:UNIT_PRICE ...`` prints the invoice totals."""

from __future__ import annotations

import sys
from collections.abc import Sequence

from billing.application.issue_invoice import IssueInvoice
from billing.domain.invoice import InvoiceError
from billing.infrastructure.memory_repository import InMemoryInvoices

def main(argv: Sequence[str] | None = None) -> int:
    """Run the program; return 0 on success and 1 when the invoice is invalid."""
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) < 3:
        print("usage: python -m billing INVOICE_ID TAX_RATE DESCRIPTION:QUANTITY:UNIT_PRICE ...", file=sys.stderr)
        return 2
    try:
        lines = [(item, int(quantity), price) for item, quantity, price in (part.split(":") for part in args[2:])]
        invoice = IssueInvoice(InMemoryInvoices())(args[0], args[1], lines)
    except (InvoiceError, ValueError) as error:
        print(f"billing: {error}", file=sys.stderr)
        return 1
    print(f"{invoice.invoice_id}: subtotal {invoice.subtotal} tax {invoice.tax} total {invoice.total}")
    return 0
```

The command line `python -m billing INVOICE_ID TAX_RATE DESCRIPTION:QUANTITY:UNIT_PRICE ...`. With fewer than three arguments it prints the usage and returns 2. Otherwise `args[2:]` are the lines; each `part.split(":")` becomes `(description, quantity, price)` with the quantity converted by `int` and the price left as text for `Decimal`. `IssueInvoice(InMemoryInvoices())(args[0], args[1], lines)` issues the invoice. Errors from the domain or from `int(...)` print `billing: <message>` to standard error and return 1. Success prints `ID: subtotal X tax Y total Z` and returns 0.

<!-- /walk:consumers/svc-billing/src/billing/interfaces/cli.py -->

<!-- walk:consumers/svc-search/src/search/__init__.py -->
### `consumers/svc-search/src/search/__init__.py`, line by line

Lines 1 to 1:

```python
"""svc-search: a tiny full-text index."""
```

A package marker file. A folder of Python files becomes a **package** (importable as a unit, e.g. `import orders.domain`) when it contains a file named `__init__.py`. The text in triple quotes is the package's docstring; there is no other code. It runs once when the package is first imported. The search package: a tiny full-text index.

<!-- /walk:consumers/svc-search/src/search/__init__.py -->

<!-- walk:consumers/svc-search/src/search/domain/__init__.py -->
### `consumers/svc-search/src/search/domain/__init__.py`, line by line

Lines 1 to 1:

```python
"""Tokenizing and the inverted index. No I/O."""
```

A package marker file. A folder of Python files becomes a **package** (importable as a unit, e.g. `import orders.domain`) when it contains a file named `__init__.py`. The text in triple quotes is the package's docstring; there is no other code. It runs once when the package is first imported.

<!-- /walk:consumers/svc-search/src/search/domain/__init__.py -->

<!-- walk:consumers/svc-search/src/search/application/__init__.py -->
### `consumers/svc-search/src/search/application/__init__.py`, line by line

Lines 1 to 1:

```python
"""Use cases and ports. Depends on the domain only."""
```

A package marker file. A folder of Python files becomes a **package** (importable as a unit, e.g. `import orders.domain`) when it contains a file named `__init__.py`. The text in triple quotes is the package's docstring; there is no other code. It runs once when the package is first imported.

<!-- /walk:consumers/svc-search/src/search/application/__init__.py -->

<!-- walk:consumers/svc-search/src/search/infrastructure/__init__.py -->
### `consumers/svc-search/src/search/infrastructure/__init__.py`, line by line

Lines 1 to 1:

```python
"""Adapters for the application ports."""
```

A package marker file. A folder of Python files becomes a **package** (importable as a unit, e.g. `import orders.domain`) when it contains a file named `__init__.py`. The text in triple quotes is the package's docstring; there is no other code. It runs once when the package is first imported.

<!-- /walk:consumers/svc-search/src/search/infrastructure/__init__.py -->

<!-- walk:consumers/svc-search/src/search/interfaces/__init__.py -->
### `consumers/svc-search/src/search/interfaces/__init__.py`, line by line

Lines 1 to 1:

```python
"""Command-line entry point."""
```

A package marker file. A folder of Python files becomes a **package** (importable as a unit, e.g. `import orders.domain`) when it contains a file named `__init__.py`. The text in triple quotes is the package's docstring; there is no other code. It runs once when the package is first imported.

<!-- /walk:consumers/svc-search/src/search/interfaces/__init__.py -->

<!-- walk:consumers/svc-search/src/search/__main__.py -->
### `consumers/svc-search/src/search/__main__.py`, line by line

Lines 1 to 7:

```python
"""``python -m search`` entry point."""

import sys

from search.interfaces.cli import main

sys.exit(main())
```

The `python -m search` entry point, built like the other two.

<!-- /walk:consumers/svc-search/src/search/__main__.py -->

<!-- walk:consumers/svc-search/src/search/domain/index.py -->
### `consumers/svc-search/src/search/domain/index.py`, line by line

Lines 1 to 10:

```python
"""Words become terms; an inverted index maps each term to the documents that contain it."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

STOP_WORDS = frozenset({"a", "an", "and", "the", "of", "to", "in", "is"})
_WORD = re.compile(r"[a-z0-9]+")
```

The docstring: words become terms and an **inverted index** maps each term to the documents that contain it (like the index at the back of a book). `Counter` is a dictionary that counts. `STOP_WORDS` is a `frozenset`, an unchangeable set of very common words that carry no meaning for searching. `_WORD = re.compile(r"[a-z0-9]+")` matches runs of lower-case letters and digits.

Lines 13 to 15:

```python
def tokenize(text: str) -> list[str]:
    """Lowercase ``text`` and return its words, without stop words, in order."""
    return [word for word in _WORD.findall(text.lower()) if word not in STOP_WORDS]
```

`tokenize(text)` lower-cases the text, finds all words with `_WORD.findall`, and keeps those not in `STOP_WORDS`: a list comprehension with an `if`. It returns a list in order.

Lines 18 to 23:

```python
@dataclass(frozen=True, slots=True)
class Document:
    """A document id and its text."""

    doc_id: str
    text: str
```

`Document` is a frozen dataclass with an id and the text.

Lines 26 to 35:

```python
class InvertedIndex:
    """Maps terms to ``{doc_id: occurrences}``; a query matches documents that contain every query term."""

    def __init__(self) -> None:
        self._postings: dict[str, Counter[str]] = {}

    def add(self, document: Document) -> None:
        """Index ``document``; adding the same id again counts its words twice, so callers add each id once."""
        for term in tokenize(document.text):
            self._postings.setdefault(term, Counter())[document.doc_id] += 1
```

`InvertedIndex.__init__` creates `_postings`, a dictionary from each term to a `Counter` of `{doc_id: how many times}`. `add` tokenizes the document text; for each term `self._postings.setdefault(term, Counter())` returns the existing counter or inserts a new one, and `[document.doc_id] += 1` counts one more occurrence. The docstring warns that adding the same id twice double counts.

Lines 37 to 47:

```python
    def search(self, query: str) -> list[tuple[str, int]]:
        """Return ``(doc_id, score)`` for documents containing every term, best score first, ties by id."""
        terms = tokenize(query)
        if not terms:
            return []
        matching: set[str] | None = None
        for term in terms:
            ids = set(self._postings.get(term, {}))
            matching = ids if matching is None else matching & ids
        scores = {doc: sum(self._postings[term][doc] for term in terms) for doc in matching or set()}
        return sorted(scores.items(), key=lambda item: (-item[1], item[0]))
```

`search(query)` returns `(doc_id, score)` pairs. An empty query (all stop words) returns `[]`. For each term, `ids` is the set of documents that contain it (`self._postings.get(term, {})` gives an empty mapping for an unknown term); `matching` starts as `None` and becomes the first set, then is **intersected** with each later one (`matching & ids` keeps only documents in both), so a document must contain every term. `scores` maps each matching document to the sum of its counts for all the query terms (`matching or set()` guards the `None`). The final line sorts the pairs: `key=lambda item: (-item[1], item[0])` is a small anonymous function that sorts by score descending (negated) and then by id ascending.

<!-- /walk:consumers/svc-search/src/search/domain/index.py -->

<!-- walk:consumers/svc-search/src/search/application/search_documents.py -->
### `consumers/svc-search/src/search/application/search_documents.py`, line by line

Lines 1 to 16:

```python
"""Use cases: build an index from a document source and answer queries."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from search.domain.index import Document, InvertedIndex

class DocumentSource(Protocol):
    """Where documents come from."""

    def documents(self) -> Iterable[Document]:
        """Yield every document once."""
        ...
```

Imports and the `DocumentSource` protocol: anything with a method `documents()` that yields documents (`Iterable[Document]`).

Lines 19 to 29:

```python
class SearchDocuments:
    """Index a source once, then answer any number of queries."""

    def __init__(self, source: DocumentSource) -> None:
        self._index = InvertedIndex()
        for document in source.documents():
            self._index.add(document)

    def __call__(self, query: str) -> list[tuple[str, int]]:
        """Return ``(doc_id, score)`` for the documents matching ``query``."""
        return self._index.search(query)
```

`SearchDocuments.__init__` builds an `InvertedIndex` and adds every document of the source once. `__call__(query)` answers a query through the index. Indexing once and querying many times is why the work happens in the constructor.

<!-- /walk:consumers/svc-search/src/search/application/search_documents.py -->

<!-- walk:consumers/svc-search/src/search/infrastructure/jsonl_source.py -->
### `consumers/svc-search/src/search/infrastructure/jsonl_source.py`, line by line

Lines 1 to 27:

```python
"""Documents from a JSON Lines file: one ``{"id": ..., "text": ...}`` object per line."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

from search.domain.index import Document

class JsonLinesDocuments:
    """:class:`~search.application.search_documents.DocumentSource` backed by a file."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def documents(self) -> Iterator[Document]:
        """Yield the documents of the file; a blank line is skipped, a malformed line raises ``ValueError``."""
        for number, line in enumerate(self._path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                yield Document(str(record["id"]), str(record["text"]))
            except (json.JSONDecodeError, KeyError, TypeError) as error:
                raise ValueError(f"{self._path}:{number}: not a document: {error}") from error
```

`JsonLinesDocuments` reads **JSON Lines**: a text file with one JSON object per line. `documents` is a generator (`yield`): `enumerate(..., start=1)` pairs each line with its number counting from 1. Blank lines are skipped (`continue`). `json.loads(line)` parses one line; `Document(str(record["id"]), str(record["text"]))` builds a document, converting both to text. If the line is not JSON (`json.JSONDecodeError`), has no `id` or `text` (`KeyError`), or is not an object (`TypeError`), a `ValueError` is raised whose message names the file and line number, and `from error` keeps the cause attached.

<!-- /walk:consumers/svc-search/src/search/infrastructure/jsonl_source.py -->

<!-- walk:consumers/svc-search/src/search/interfaces/cli.py -->
### `consumers/svc-search/src/search/interfaces/cli.py`, line by line

Lines 1 to 26:

```python
"""``python -m search DOCUMENTS.jsonl QUERY...`` prints the matching document ids with their scores."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

from search.application.search_documents import SearchDocuments
from search.infrastructure.jsonl_source import JsonLinesDocuments

def main(argv: Sequence[str] | None = None) -> int:
    """Run the program; return 0 on success, 1 for an unreadable file and 2 for a usage error."""
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) < 2:
        print("usage: python -m search DOCUMENTS.jsonl QUERY...", file=sys.stderr)
        return 2
    try:
        results = SearchDocuments(JsonLinesDocuments(Path(args[0])))(" ".join(args[1:]))
    except (OSError, ValueError) as error:
        print(f"search: {error}", file=sys.stderr)
        return 1
    for doc_id, score in results:
        print(f"{doc_id}\t{score}")
    return 0
```

`python -m search DOCUMENTS.jsonl QUERY...`. Fewer than two arguments: usage, exit 2. Otherwise `Path(args[0])` is the file, `" ".join(args[1:])` joins the remaining words into the query, and the use case is built and called. `OSError` (unreadable file) and `ValueError` (a bad line) are reported as `search: <message>` with exit code 1. Each result is printed as the id, a tab and the score; the program returns 0.

<!-- /walk:consumers/svc-search/src/search/interfaces/cli.py -->

<!-- walk:.env.example -->
### `.env.example`, line by line

Lines 1 to 5:

```hcl
# Every variable the project reads. None is a secret.

# The GitHub repository this platform is published as. The workflows pin the platform's own composite action by

# commit SHA under this name, so publish the repository as sumitsr/platform-ci (the account the author is signed in as).

PLATFORM_REPO=sumitsr/platform-ci
```

Configuration for the platform repository. The lines starting with `#` are comments. `PLATFORM_REPO=sumitsr/platform-ci` sets the environment variable that tells the Makefile which GitHub repository name the platform is published under; the workflows pin the platform's own composite action by commit SHA under this name. The comment says none of the values is a secret. A real `.env` file (ignored by Git) is read by the Makefile's `-include .env`.

<!-- /walk:.env.example -->

## Try it yourself

1. `.venv/bin/python -m pipeline.secrets_report` prints the three-row secrets table.
2. `.venv/bin/python -m pipeline.platform_refs consumers/svc-orders/.github/workflows/ci.yml --platform sumitsr/platform-ci` prints two lines: the workflow and the action, each with `commit`.
3. `cd consumers/svc-orders && PYTHONPATH=src ../../.venv/bin/python -m orders o-1 pen:2:150 pad:1:50` prints `o-1: 3.50`.
4. `cd consumers/svc-billing && PYTHONPATH=src ../../.venv/bin/python -m billing i-1 0.0825 widget:3:19.99` prints `i-1: subtotal 59.97 tax 4.95 total 64.92`.
5. `.venv/bin/python -c "from decimal import Decimal as D; print(0.1+0.2, D('0.1')+D('0.2'))"` prints `0.30000000000000004 0.3`.

## Mistakes people make

- Using floats for money.
- `subprocess.run(f"git {ref}", shell=True)`: a hostile `ref` becomes a command. A list without `shell=True` avoids it.
- `except:` or `except Exception:` that hides bugs.
- A mutable default argument.
- Forgetting that `Decimal(0.1)` is not `Decimal("0.1")`.

## Check yourself

1. Why are prices whole cents or `Decimal`? *(Binary floats cannot represent most decimal fractions exactly.)*
2. What does `fullmatch` require? *(The whole text matches the pattern.)*
3. Why does `subprocess.run` get a list? *(No shell is involved, so arguments cannot be re-parsed as commands.)*
4. What does `frozen=True` prevent? *(Changing a field after the object is built.)*
5. What does `v2^{commit}` mean to Git? *(The commit that the tag `v2` ultimately points to.)*

## Further reading

- Python 3.13 documentation: https://docs.python.org/3.13/
- `decimal`: https://docs.python.org/3.13/library/decimal.html
- `subprocess`: https://docs.python.org/3.13/library/subprocess.html
- `dataclasses`: https://docs.python.org/3.13/library/dataclasses.html
