import subprocess
from pathlib import Path

from pipeline import pins

SHA = "a" * 40
PLATFORM = "sumitsr/platform-ci"


def write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def git(root: Path, *args: str) -> str:
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    done = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=True, env=env)
    return done.stdout.strip()


def commit_all(root: Path, message: str) -> str:
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)
    return git(root, "rev-parse", "HEAD")


def workflow(*uses: str) -> str:
    steps = "".join(f"      - uses: {value}\n" for value in uses)
    return f"jobs:\n  j:\n    runs-on: ubuntu-latest\n    steps:\n{steps}"


def test_a_full_sha_a_local_path_and_a_digest_are_pinned():
    assert pins.is_pinned(f"actions/checkout@{SHA}")
    assert pins.is_pinned("./.github/actions/setup")
    assert pins.is_pinned("docker://rhysd/actionlint@sha256:" + "b" * 64)


def test_a_tag_a_branch_and_a_short_sha_are_not_pinned():
    assert not pins.is_pinned("actions/checkout@v4")
    assert not pins.is_pinned("actions/checkout@main")
    assert not pins.is_pinned("actions/checkout@abc1234")


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


def test_an_action_outside_the_allowed_list_is_reported(tmp_path):
    write(tmp_path, ".github/workflows/w.yml", workflow(f"actions/checkout@{SHA}", f"evil/stealer@{SHA}", "./local"))
    assert pins.not_allowed(tmp_path, ["actions/*"]) == [f".github/workflows/w.yml: evil/stealer@{SHA}"]


def test_the_allowlist_ignores_comments_and_blank_lines(tmp_path):
    allowlist = tmp_path / "allowed.txt"
    allowlist.write_text("# comment\n\nactions/*   # official\nowner/repo\n", encoding="utf-8")
    assert pins.read_allowlist(allowlist) == ["actions/*", "owner/repo"]


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
