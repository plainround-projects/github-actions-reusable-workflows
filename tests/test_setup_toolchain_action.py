"""The composite action's contract: its metadata and its input validation script."""

import subprocess
from pathlib import Path

import pytest
import yaml

ACTION_DIR = Path(__file__).resolve().parents[1] / ".github" / "actions" / "setup-toolchain"
ACTION = yaml.safe_load((ACTION_DIR / "action.yml").read_text(encoding="utf-8"))
SCRIPT = ACTION_DIR / "validate-inputs.sh"


def validate(version: str, requirements: str = "requirements.txt") -> subprocess.CompletedProcess[str]:
    env = {"INPUT_PYTHON_VERSION": version, "INPUT_REQUIREMENTS_FILE": requirements, "PATH": "/usr/bin:/bin"}
    return subprocess.run(["bash", str(SCRIPT)], capture_output=True, text=True, env=env, check=False)


def test_it_is_a_composite_action():
    assert ACTION["runs"]["using"] == "composite"


def test_the_python_version_input_is_required_and_the_requirements_file_has_a_default():
    assert ACTION["inputs"]["python-version"]["required"] is True
    assert ACTION["inputs"]["requirements-file"]["default"] == "requirements.txt"


def test_every_input_and_output_has_a_description():
    for section in ("inputs", "outputs"):
        for name, spec in ACTION[section].items():
            assert spec.get("description"), f"{section}.{name} has no description"


def test_it_declares_the_cache_hit_and_python_version_outputs():
    assert set(ACTION["outputs"]) == {"cache-hit", "python-version"}
    assert ACTION["outputs"]["cache-hit"]["value"] == "${{ steps.cache.outputs.cache-hit }}"


def test_every_run_step_names_its_shell():
    for step in ACTION["runs"]["steps"]:
        if "run" in step:
            assert step.get("shell") == "bash", f"step without shell: {step}"


def test_inputs_reach_the_validation_step_through_the_environment():
    step = ACTION["runs"]["steps"][0]
    assert "${{" not in step["run"]
    assert step["env"]["INPUT_PYTHON_VERSION"] == "${{ inputs.python-version }}"


def test_the_cache_key_contains_the_os_the_exact_python_and_the_file_hash():
    cache = next(s for s in ACTION["runs"]["steps"] if s.get("id") == "cache")
    key = cache["with"]["key"]
    assert "runner.os" in key
    assert "steps.python.outputs.python-version" in key
    assert "hashFiles(inputs.requirements-file)" in key


@pytest.mark.parametrize("version", ["3.12", "3.12.7", "3.9", "3.13"])
def test_a_version_that_looks_like_a_python_version_is_accepted(version):
    result = validate(version)
    assert result.returncode == 0
    assert version in result.stdout


@pytest.mark.parametrize("version", ["", "3", "latest", "3.12; rm -rf /", "2.7", "3.12.7.1", "$(id)"])
def test_anything_else_is_rejected_with_an_error_that_names_the_input(version):
    result = validate(version)
    assert result.returncode == 1
    assert "python-version must look like" in result.stdout


def test_an_empty_requirements_file_name_is_rejected():
    result = validate("3.12", requirements="")
    assert result.returncode == 1
    assert "requirements-file" in result.stdout
