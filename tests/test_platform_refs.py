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


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q", "-b", "main")
    return tmp_path


def test_only_references_to_the_platform_are_found_once_each_in_file_order():
    refs = platform_refs.platform_references(WORKFLOW, PLATFORM)
    assert [r.ref for r in refs] == ["v1", "b" * 40]
    assert refs[0].path == f"{PLATFORM}/.github/workflows/build-test.yml"


def test_a_full_sha_is_a_commit_and_a_tag_is_a_label():
    refs = platform_refs.platform_references(WORKFLOW, PLATFORM)
    assert [r.is_commit for r in refs] == [False, True]


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
