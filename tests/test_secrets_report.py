from pathlib import Path

from pipeline import secrets_report

CALLEE = """
on:
  workflow_call:
    secrets:
      PACKAGE_TOKEN:
        required: false
jobs:
  j:
    runs-on: ubuntu-latest
    steps:
      - run: echo
        env:
          T: ${{ secrets.PACKAGE_TOKEN }}
"""


def write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def consumer(secrets: str = "") -> str:
    return f"jobs:\n  ci:\n    uses: o/p/.github/workflows/build-test.yml@v1\n{secrets}"


def test_declared_and_referenced_secret_names_are_read_from_the_callee():
    import yaml

    assert secrets_report.declared_secrets(yaml.safe_load(CALLEE)) == {"PACKAGE_TOKEN"}
    assert secrets_report.referenced_secrets(CALLEE) == {"PACKAGE_TOKEN"}


def test_a_caller_that_passes_nothing_lets_the_callee_read_nothing():
    row = secrets_report.row_for("svc-orders", {"uses": "x"}, {"PACKAGE_TOKEN"})
    assert (row.passed, row.readable) == ("none", "nothing")


def test_a_named_secret_is_the_only_one_the_callee_can_read():
    row = secrets_report.row_for(
        "svc-billing", {"secrets": {"PACKAGE_TOKEN": "${{ secrets.PACKAGE_TOKEN }}"}}, {"PACKAGE_TOKEN"}
    )
    assert (row.passed, row.readable) == ("PACKAGE_TOKEN (named)", "PACKAGE_TOKEN only")


def test_a_named_secret_the_callee_did_not_declare_is_reported_as_ignored():
    row = secrets_report.row_for("svc-x", {"secrets": {"OTHER": "v"}}, {"PACKAGE_TOKEN"})
    assert "OTHER not declared by the callee" in row.readable


def test_inherit_hands_over_every_secret_of_the_caller():
    row = secrets_report.row_for("svc-search", {"secrets": "inherit"}, {"PACKAGE_TOKEN"})
    assert row.passed == "inherit"
    assert "every secret in svc-search" in row.readable
    assert "never asked for" in row.readable


def test_the_report_has_one_row_per_consumer_in_name_order(tmp_path):
    write(tmp_path, ".github/workflows/build-test.yml", CALLEE)
    write(tmp_path, "consumers/svc-b/.github/workflows/ci.yml", consumer("    secrets: inherit\n"))
    write(tmp_path, "consumers/svc-a/.github/workflows/ci.yml", consumer())
    rows = secrets_report.build_rows(tmp_path, tmp_path / ".github/workflows/build-test.yml")
    assert [row.consumer for row in rows] == ["svc-a", "svc-b"]
    text = secrets_report.render(rows)
    assert text.splitlines()[0].startswith("consumer")
    assert "inherit" in text


def test_main_prints_the_table(tmp_path, capsys):
    write(tmp_path, ".github/workflows/build-test.yml", CALLEE)
    write(tmp_path, "consumers/svc-a/.github/workflows/ci.yml", consumer())
    assert secrets_report.main([str(tmp_path)]) == 0
    assert "svc-a" in capsys.readouterr().out
