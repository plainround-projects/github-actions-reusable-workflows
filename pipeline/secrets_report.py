"""Report what each called workflow can read, from the callers' ``secrets:`` and the callee's declarations.

Three ways a caller can pass secrets: none (the default), named ones, or ``inherit``. ``inherit`` hands over every
secret the caller can see, whether the callee asks for it or not.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_REFERENCE = re.compile(r"secrets\.([A-Za-z_][A-Za-z0-9_]*)")


@dataclass(frozen=True, slots=True)
class Row:
    """One consumer: what its workflow passes and what the shared workflow can therefore read."""

    consumer: str
    passed: str
    readable: str


def declared_secrets(callee: Mapping[Any, Any]) -> set[str]:
    """Return the secret names a reusable workflow declares under ``workflow_call.secrets``."""
    triggers = callee.get("on", callee.get(True)) or {}
    return set(((triggers.get("workflow_call") or {}).get("secrets") or {}).keys())


def referenced_secrets(callee_text: str) -> set[str]:
    """Return every ``secrets.NAME`` the callee's text mentions."""
    return set(_REFERENCE.findall(callee_text))


def passes(job: Mapping[str, Any]) -> str | dict[str, Any] | None:
    """Return ``"inherit"``, the named mapping, or ``None`` for the secrets a calling job passes."""
    value = job.get("secrets")
    if value is None or value == "inherit":
        return value
    return dict(value)


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


def build_rows(root: Path, callee_path: Path) -> list[Row]:
    """Build one row per consumer under ``root/consumers`` from its ``ci.yml``."""
    declared = declared_secrets(yaml.safe_load(callee_path.read_text(encoding="utf-8")))
    rows = []
    for workflow in sorted(root.glob("consumers/*/.github/workflows/ci.yml")):
        consumer = workflow.parents[2].name
        jobs = yaml.safe_load(workflow.read_text(encoding="utf-8"))["jobs"]
        rows += [row_for(consumer, job, declared) for job in jobs.values() if "uses" in job]
    return rows


def render(rows: Sequence[Row]) -> str:
    """Render the rows as the plain-text table of the README."""
    width = max(len("consumer"), *(len(row.consumer) for row in rows))
    passed = max(len("secrets passed"), *(len(row.passed) for row in rows))
    lines = [f"{'consumer':<{width}}  {'secrets passed':<{passed}}  what the shared workflow can read"]
    lines += [f"{row.consumer:<{width}}  {row.passed:<{passed}}  {row.readable}" for row in rows]
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """Print the table for the repository at the first argument (default: the current directory)."""
    args = list(sys.argv[1:] if argv is None else argv)
    root = Path(args[0]) if args else Path(".")
    rows = build_rows(root, root / ".github" / "workflows" / "build-test.yml")
    print(render(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
