# Python

## What it is

Python is a programming language. You write instructions in text files ending in `.py`; a program called the **interpreter** reads them and carries them out. A **module** is one `.py` file, a **package** is a folder of modules with a name. This repository supports Python 3.10 and newer (`requires-python = ">=3.10"`) and was developed with 3.13.

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
