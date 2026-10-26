"""Checks on the ``uses:`` references of the workflows and local actions.

* every reference names a full commit SHA, a local path or a digest-pinned image (a tag can be moved by its owner);
* every reference to this repository's own composite actions pins the last commit that changed the action, so the
  workflow runs the action as it is now, not a stale version of it (``--internal``);
* every external action is on an allowed list (``--allowlist FILE``, one ``owner/repo`` pattern per line).
"""

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

_PINNED = re.compile(r"[\w.-]+/[\w./-]+@[0-9a-f]{40}")
_DIGEST = re.compile(r"docker://\S+@sha256:[0-9a-f]{64}")
_SHA = re.compile(r"[0-9a-f]{40}")


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


def definition_files(root: Path) -> list[Path]:
    """Return the workflow files and composite action files under ``root/.github``, plus the consumers' own."""
    patterns = [".github/workflows/*.y*ml", ".github/actions/**/action.y*ml", "consumers/*/.github/workflows/*.y*ml"]
    return sorted(path for pattern in patterns for path in root.glob(pattern))


def references(root: Path) -> list[tuple[Path, str]]:
    """Return ``(file, uses-value)`` for every reference in every definition file."""
    found = []
    for file in definition_files(root):
        document = yaml.safe_load(file.read_text(encoding="utf-8"))
        found += [(file, ref) for ref in uses_values(document)]
    return found


def is_pinned(reference: str) -> bool:
    """Return whether a ``uses`` value is local, a digest-pinned image, or a full-SHA reference."""
    return reference.startswith("./") or bool(_DIGEST.fullmatch(reference)) or bool(_PINNED.fullmatch(reference))


def violations(root: Path) -> list[str]:
    """Return ``path: uses-value`` for each reference that is not pinned."""
    return [f"{file.relative_to(root)}: {ref}" for file, ref in references(root) if not is_pinned(ref)]


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def last_change(root: Path, directory: str) -> str:
    """Return the last commit that changed ``directory``, not counting its README."""
    return _git(root, "log", "-1", "--format=%H", "--", directory, f":(exclude){directory}/README.md")


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


def read_allowlist(path: Path) -> list[str]:
    """Read one pattern per line, ignoring blank lines and ``#`` comments."""
    lines = (line.split("#", 1)[0].strip() for line in path.read_text(encoding="utf-8").splitlines())
    return [line for line in lines if line]


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


if __name__ == "__main__":
    sys.exit(main())
