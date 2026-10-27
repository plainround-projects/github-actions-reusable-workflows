# uv

## What it is

uv is a fast Python package tool written in Rust. It can do much of what pip and venv do, and it can **resolve** dependencies: given the packages you name, work out which exact versions of everything fit together. In this repository it is used only to **make the lock files**, never in CI and never by the `Makefile`.

## Why this repository uses it

The platform's tools and each of the three consumers install from a hash-pinned lock file (`pip install --require-hashes`). A lock that works on every platform and from Python 3.10 up needs a resolver that can write environment markers. `uv pip compile --universal` does.

## Where it appears

| Path | What it does with uv |
| --- | --- |
| `requirements.txt` | Header comment names the `uv pip compile` command that made it. |
| `consumers/svc-orders/requirements.txt`, `svc-billing`, `svc-search` | The same, each from its own `requirements.in` (pytest only). |

## How it works underneath

`uv pip compile requirements.in -o requirements.txt` reads the top-level requirements, asks the package index which versions exist and what each needs, finds a consistent set, and writes it with hashes. `--universal` makes the answer valid for all platforms and Python versions at once instead of only the current machine. `--python-version 3.10` sets the oldest Python it must support. `uv run --python 3.11 ...` finds or downloads that Python, builds a throwaway environment, and runs the command in it.

## Walkthrough of this repository's use

```bash
uv pip compile requirements.in --universal --generate-hashes --python-version 3.10 -o requirements.txt
```

Run from the repository root for the tools, and from inside each consumer folder for its own lock. `--universal` resolves for all platforms at once and writes markers such as `; sys_platform == 'win32'`. `--generate-hashes` adds the SHA-256 lines. `--python-version 3.10` makes the oldest supported Python decide the choices. `-o` names the output. After running it, commit the `.txt` file. This is how `pytest` moved from 8.3.3 to 9.0.3 (the older version has a known advisory), and how `import-linter`, which nothing here used, was dropped.

## Try it yourself

1. `uv --version` prints the version.
2. `uv pip compile requirements.in --universal --python-version 3.10 -o /tmp/r.txt` writes a lock without hashes; `grep -c "^[a-z]" /tmp/r.txt` counts packages.
3. `cd consumers/svc-orders && uv pip compile requirements.in --universal --generate-hashes --python-version 3.10 -o /tmp/o.txt` reproduces that consumer's lock (compare with `diff /tmp/o.txt requirements.txt`; only the header path may differ).
4. `head -3 requirements.txt` shows the recorded command.

## Mistakes people make

- Editing `requirements.txt` by hand instead of the `.in` file.
- Forgetting `--universal` and getting a lock that is wrong on Windows.
- Running `uv` commands that change the project (like `uv add`) when the repository manages dependencies by hand.

## Check yourself

1. What does "resolve" mean? *(Choose exact versions of all packages that satisfy every requirement.)*
2. What does `--universal` add? *(A lock valid for every platform, with markers.)*
3. Why `--python-version 3.10`? *(The oldest supported Python limits which versions can be chosen.)*
4. Is uv used in CI? *(No; CI installs with pip.)*
5. Where is the command recorded? *(In the header comment of each lock file.)*

## Further reading

- uv documentation (pinned locally: 0.11.x): https://docs.astral.sh/uv/
- `uv pip compile`: https://docs.astral.sh/uv/pip/compile/
