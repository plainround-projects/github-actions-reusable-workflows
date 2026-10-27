"""The pin-check workflow's shell script, run on small repositories built in a temporary folder."""

import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = yaml.safe_load((ROOT / ".github" / "workflows" / "pin-check.yml").read_text(encoding="utf-8"))
SCRIPT = next(step["run"] for step in WORKFLOW["jobs"]["pin-check"]["steps"] if "run" in step)
SHA = "a" * 40


def run(tmp_path: Path, workflow: str) -> subprocess.CompletedProcess[str]:
    target = tmp_path / ".github" / "workflows"
    target.mkdir(parents=True)
    (target / "w.yml").write_text(workflow, encoding="utf-8")
    return subprocess.run(["bash", "-c", SCRIPT], cwd=tmp_path, capture_output=True, text=True, check=False)


def test_it_can_be_required_by_a_ruleset_and_called_by_other_repositories():
    assert set(WORKFLOW[True]) == {"pull_request", "workflow_call"}


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
