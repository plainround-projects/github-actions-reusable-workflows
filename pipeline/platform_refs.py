"""Find the references a workflow makes to this platform and resolve each to the commit it names right now.

GitHub resolves ``@v1`` when a run starts, so a tag that was moved gives a different commit than yesterday, while a
full SHA always gives the same one. ``scripts/run_consumer.sh`` uses this to run a consumer locally with ``act``
against exactly the commits GitHub would pick.
"""

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


@dataclass(frozen=True, slots=True)
class PlatformRef:
    """One ``uses:`` of the platform: the path inside the repository and the ref as written (tag, branch or SHA)."""

    path: str
    ref: str

    @property
    def is_commit(self) -> bool:
        """Whether the ref is a full commit SHA, which can never point somewhere else."""
        return bool(_SHA.fullmatch(self.ref))


def platform_references(workflow_text: str, platform: str) -> list[PlatformRef]:
    """Return every reference to ``platform`` (``owner/repo``) in a workflow, in file order, without duplicates."""
    found: list[PlatformRef] = []
    for value in uses_values(yaml.safe_load(workflow_text)):
        path, _, ref = value.partition("@")
        if path.startswith(f"{platform}/") and ref and PlatformRef(path, ref) not in found:
            found.append(PlatformRef(path, ref))
    return found


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


def _file_at(repo: Path, commit: str, path: str) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(repo), "show", f"{commit}:{path}"], capture_output=True, text=True, check=False
    )
    return result.stdout if result.returncode == 0 else None


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


if __name__ == "__main__":
    sys.exit(main())
