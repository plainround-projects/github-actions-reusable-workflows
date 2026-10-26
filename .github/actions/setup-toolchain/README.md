# setup-toolchain

A composite action that installs a pinned Python and restores the pip download cache, keyed on the dependency file.
The reusable workflow `build-test.yml` calls it; consumers can also call it directly.

## Inputs

| Name | Required | Default | What it does |
| --- | --- | --- | --- |
| `python-version` | yes | | The version to install, `3.12` or `3.12.7`. The first step rejects anything else with an error that names the input. |
| `requirements-file` | no | `requirements.txt` | The file whose hash is part of the cache key. Changing it changes the key, so the cache misses. |

## Outputs

| Name | Value |
| --- | --- |
| `cache-hit` | `true` when the cache was restored from the exact key. Empty on a miss (the first run, or after the dependency file changed). |
| `python-version` | The exact version installed, for example `3.12.7`. |

## Use

```yaml
- id: toolchain
  uses: <owner>/platform-ci/.github/actions/setup-toolchain@<full commit SHA> # vX.Y.Z
  with:
    python-version: "3.12"
- run: echo "cache hit: ${{ steps.toolchain.outputs.cache-hit }}"
```

Every `run` step in a composite action needs its own `shell:`. This action uses `bash`, so it is for Linux and macOS
runners (and Git Bash on Windows). The cache path comes from `python -m pip cache dir`, so it is correct on each system.

## How it is tested

- `tests/test_setup_toolchain_action.py` parses `action.yml` (typed inputs and outputs, a `shell` on every `run` step,
  every `uses` pinned to a full SHA) and runs `validate-inputs.sh` with good and bad values.
- `.github/workflows/test-setup-toolchain.yml` uses the action from this repository (`uses: ./.github/actions/setup-toolchain`)
  and prints its outputs. Run it locally with `make run`.

## Versioning

The action is pinned **by commit SHA** inside the reusable workflow, never by a tag, because the workflow and the action
live in the same repository: a tag the workflow used would move with the workflow. `pipeline/pins.py --internal` fails
the build when that SHA is not the last commit that changed this folder (see ADR 0002 in `docs/adr`).
