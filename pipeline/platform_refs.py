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


def main(argv: Sequence[str] | None = None) -> int:
    """Print ``ref<TAB>commit<TAB>kind<TAB>path`` for each platform reference of a workflow file."""
    parser = argparse.ArgumentParser(prog="pipeline.platform_refs")
    parser.add_argument("workflow", type=Path)
    parser.add_argument("--platform", required=True, metavar="OWNER/REPO")
    parser.add_argument("--repo", type=Path, default=Path("."), help="the platform repository to resolve refs in")
    args = parser.parse_args(argv)
    try:
        for reference in platform_references(args.workflow.read_text(encoding="utf-8"), args.platform):
            kind = "commit" if reference.is_commit else "label"
            print(f"{reference.ref}\t{resolve(args.repo, reference.ref)}\t{kind}\t{reference.path}")
    except LookupError as error:
        print(f"platform_refs: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
