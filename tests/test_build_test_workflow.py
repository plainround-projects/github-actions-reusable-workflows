"""The shared workflow's contract: its inputs, secrets, permissions and what it does with untrusted text."""

import re
from pathlib import Path

import pytest
import yaml
from pipeline import pins, secrets_report

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / ".github" / "workflows" / "build-test.yml"
TEXT = PATH.read_text(encoding="utf-8")
WORKFLOW = yaml.safe_load(TEXT)
CALL = WORKFLOW[True]["workflow_call"]
JOB = WORKFLOW["jobs"]["build-test"]


def test_it_is_a_reusable_workflow_with_typed_inputs():
    assert CALL["inputs"]["python"] == {
        "description": "Python version to test with, such as 3.12.",
        "type": "string",
        "required": True,
    }
    assert CALL["inputs"]["test-command"]["default"] == "pytest -q"
    assert CALL["inputs"]["report-secret-names"]["type"] == "boolean"


def test_the_v1_input_name_is_gone_so_a_caller_still_using_it_fails_loudly():
    assert "python-version" not in CALL["inputs"]


def test_the_secret_is_declared_and_optional():
    assert CALL["secrets"]["PACKAGE_TOKEN"]["required"] is False


def test_every_secret_the_workflow_reads_is_declared():
    assert secrets_report.referenced_secrets(TEXT) <= secrets_report.declared_secrets(WORKFLOW)


def test_permissions_start_empty_and_the_job_adds_only_contents_read():
    assert WORKFLOW["permissions"] == {}
    assert JOB["permissions"] == {"contents": "read"}
    assert JOB["timeout-minutes"] <= 15


def test_untrusted_text_never_reaches_a_shell_command_through_an_expression():
    for step in JOB["steps"]:
        if "run" in step:
            assert "${{" not in step["run"], step


def test_the_test_command_and_the_secret_list_go_through_the_environment():
    env_names = {name for step in JOB["steps"] for name in step.get("env", {})}
    assert {"TEST_COMMAND", "SECRETS_CONTEXT", "PACKAGE_TOKEN"} <= env_names


def test_checkout_does_not_leave_the_token_in_the_git_config():
    checkout = next(s for s in JOB["steps"] if "actions/checkout" in s.get("uses", ""))
    assert checkout["with"]["persist-credentials"] is False


def test_the_composite_action_is_called_by_repository_path_at_a_full_commit():
    toolchain = next(s for s in JOB["steps"] if s.get("id") == "toolchain")
    reference = toolchain["uses"]
    assert reference.startswith("sumitsr/platform-ci/.github/actions/setup-toolchain@")
    assert pins.is_pinned(reference)
    assert toolchain["with"]["python-version"] == "${{ inputs.python }}"


def test_the_secret_names_step_runs_only_when_asked():
    step = next(s for s in JOB["steps"] if "secret names" in s.get("name", ""))
    assert step["if"] == "inputs.report-secret-names"


def test_the_workflow_exposes_the_cache_hit_of_the_toolchain():
    assert CALL["outputs"]["cache-hit"]["value"] == "${{ jobs.build-test.outputs.cache-hit }}"
    assert JOB["outputs"]["cache-hit"] == "${{ steps.toolchain.outputs.cache-hit }}"


def consumers() -> list[Path]:
    return sorted(ROOT.glob("consumers/*/.github/workflows/ci.yml"))


@pytest.mark.parametrize("workflow", consumers(), ids=lambda p: p.parents[2].name)
def test_a_consumer_workflow_is_under_fifteen_lines_and_only_calls_the_platform(workflow):
    assert len(workflow.read_text(encoding="utf-8").splitlines()) < 15
    jobs = yaml.safe_load(workflow.read_text(encoding="utf-8"))["jobs"]
    assert len(jobs) == 1
    job = next(iter(jobs.values()))
    assert job["uses"].startswith("sumitsr/platform-ci/.github/workflows/build-test.yml@")
    assert "steps" not in job


def test_the_changelog_tells_consumers_what_to_change_for_every_release():
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    releases = re.findall(r"^## \[(\d+\.\d+\.\d+)\]", text, flags=re.M)
    sections = re.split(r"^## \[", text, flags=re.M)[1:]
    assert releases == ["2.0.0", "1.0.0"]
    for section in sections:
        assert "### Required changes for consumers" in section
