# GitHub Actions: reusable workflows and composite actions

## What it is

GitHub Actions is the automation service built into GitHub. You describe jobs in YAML files (see `yaml.md`); GitHub starts a fresh machine (a **runner**) for each job and runs the steps. A **workflow** is one file in `.github/workflows/`. An **event** (a push, a pull request) starts it. A **job** is a list of **steps** that run on one runner. A step is either a shell command (`run:`) or a ready-made **action** (`uses:`).

This repository is about *sharing* automation, which needs three more ideas:

- A **reusable workflow** is a whole workflow that other workflows call as if it were a job. It declares what it accepts with `on: workflow_call`.
- A **composite action** is an action made of steps (`runs: using: composite`). A workflow calls it from inside a job, as one step.
- A **ref** names a version of someone else's code: a **tag** like `v2` (a label its owner can move), a branch, or a **commit SHA** (a 40-character fingerprint of one exact state, which can never move).

## Why this repository uses it

The lesson builds a small "platform": one reusable workflow (`build-test.yml`) that builds and tests a service, one composite action (`setup-toolchain`) that installs Python and restores a cache, and three consumer services that call them in under fifteen lines. It then shows what happens when a tag moves, and why consumers pin by commit.

## Where it appears

| Path | What it does |
| --- | --- |
| `.github/workflows/build-test.yml` | The reusable workflow (version 2 API). |
| `.github/actions/setup-toolchain/action.yml` | The composite action. |
| `.github/workflows/test-setup-toolchain.yml` | Uses the action from this repository and prints its outputs. |
| `.github/workflows/ci.yml` | The platform's own CI: lint, test, and a matrix job that calls `build-test.yml` on each consumer folder. |
| `.github/workflows/pin-check.yml` | A dependency-free workflow that fails when any `uses:` is not a full SHA; usable as a required workflow. |
| `consumers/*/.github/workflows/ci.yml` | The three callers, 8 to 10 lines each. |
| `demo/consumer-on-tag.yml`, `demo/consumer-on-commit.yml` | The two callers used by the moved-tag demo. |

## How it works underneath

1. A caller job has `uses: OWNER/REPO/.github/workflows/FILE@REF` instead of `runs-on` and `steps`. GitHub resolves `REF` **when the run starts**. A SHA resolves to itself. A tag resolves to whatever commit the tag points at *today*.
2. GitHub loads that file from that commit and runs its jobs. The caller passes **inputs** (`with:`) and **secrets** (`secrets:`). A secret not passed is not visible to the called workflow. `secrets: inherit` passes every secret the caller can see.
3. Permissions are capped from above: a called workflow can have at most the token permissions its caller grants.
4. Inside the called workflow, a step `uses: OWNER/REPO/PATH@REF` fetches a composite action the same way. A path starting with `./` is looked up in the **caller's** checked-out repository, not in the repository the workflow came from; that is why the reusable workflow cannot use `./.github/actions/...` for its own action.
5. A composite action's steps run in the same job and the same runner as the step that called it. Each `run:` step inside needs its own `shell:`.

## Walkthrough of this repository's use

### The caller, 8 lines

```yaml
name: ci
on: [push, pull_request]
permissions:
  contents: read
jobs:
  ci:
    uses: sumitsr/platform-ci/.github/workflows/build-test.yml@fcd73fa6d3117df6168d8f822e79577ac99cedfe # v2.0.0
    with: { python: "3.12" }
```

`on: [push, pull_request]` is a list of events. `permissions: contents: read` is the most the called workflow may use. The job calls the workflow at a full SHA with the version in a comment (for people and for Dependabot). `with: { python: "3.12" }` is a YAML flow mapping, a one-line mapping. `svc-billing` adds `secrets: { PACKAGE_TOKEN: ${{ secrets.PACKAGE_TOKEN }} }`; `svc-search` adds `secrets: inherit`.

### The reusable workflow's interface

```yaml
on:
  workflow_call:
    inputs:
      python:
        description: Python version to test with, such as 3.12.
        type: string
        required: true
      test-command:
        type: string
        default: pytest -q
      working-directory:
        type: string
        default: .
      report-secret-names:
        type: boolean
        default: false
    secrets:
      PACKAGE_TOKEN:
        required: false
    outputs:
      cache-hit:
        value: ${{ jobs.build-test.outputs.cache-hit }}
```

`workflow_call` is the event "another workflow called me". Each input has a type (`string`, `boolean`, `number`), an optional `default`, and may be `required`. Only secrets declared under `secrets:` can be passed by name. `outputs` hands a value back to the caller; here it comes from the job's own `outputs`, which come from the toolchain step. The version 2 change was renaming the input `python-version` to `python`: a breaking change, so it shipped as a new major tag and `v1` kept working.

### Least privilege

```yaml
permissions: {}

jobs:
  build-test:
    permissions:
      contents: read
```

`{}` at the top gives the token no rights; the one job adds `contents: read`, enough to check out code.

### Steps, defaults, and untrusted text

```yaml
    defaults:
      run:
        shell: bash
        working-directory: ${{ inputs.working-directory }}
    steps:
      - uses: actions/checkout@... # v7.0.1
        with:
          persist-credentials: false
      - name: List the secret names this workflow can read
        if: inputs.report-secret-names
        env:
          SECRETS_CONTEXT: ${{ toJSON(secrets) }}
        run: |
          printf '%s' "$SECRETS_CONTEXT" | jq -r 'keys[] | "can read secret=" + .'
```

`defaults.run` sets the shell and folder for every `run:` step. `if: inputs.report-secret-names` runs the step only when the caller asked. `${{ toJSON(secrets) }}` turns the secrets context into JSON; it is put in an environment variable so it is never pasted into the script text. `jq` (see `jq.md`) prints only the *names* (`keys[]`), never values.

```yaml
      - name: Test
        env:
          TEST_COMMAND: ${{ inputs.test-command }}
        run: bash -c "$TEST_COMMAND"
```

The caller's test command is run, but it reaches the shell as data in `$TEST_COMMAND`, not as text GitHub pasted into the script. Writing `run: ${{ inputs.test-command }}` would let the expression engine splice the text into the script (script injection).

### The composite action and its pin

```yaml
      - id: toolchain
        uses: sumitsr/platform-ci/.github/actions/setup-toolchain@d70ac3daf2d7ada75bcbd1bc34d83a6f29ce9abd
        with:
          python-version: ${{ inputs.python }}
          requirements-file: ${{ inputs.working-directory }}/requirements.txt
```

The action is called by repository path, pinned to the commit that last changed the action's folder. The workflow and the action live in the same repository, and a commit cannot contain its own hash, so the action is committed first and the workflow second. `python -m pipeline.pins --internal` fails if the pin is stale.

`action.yml` itself:

```yaml
inputs:
  python-version:
    description: Python version to install, such as 3.12 or 3.12.7.
    required: true
outputs:
  cache-hit:
    value: ${{ steps.cache.outputs.cache-hit }}
runs:
  using: composite
  steps:
    - name: Validate the inputs
      shell: bash
      env:
        INPUT_PYTHON_VERSION: ${{ inputs.python-version }}
      run: bash "$GITHUB_ACTION_PATH/validate-inputs.sh"
    - id: python
      uses: actions/setup-python@... # v7.1.0
    - id: cache
      uses: actions/cache@... # v6.1.0
      with:
        path: ${{ steps.pip-dir.outputs.path }}
        key: pip-${{ runner.os }}-${{ steps.python.outputs.python-version }}-${{ hashFiles(inputs.requirements-file) }}
        restore-keys: |
          pip-${{ runner.os }}-${{ steps.python.outputs.python-version }}-
```

`runs.using: composite` marks it. `$GITHUB_ACTION_PATH` is the folder holding the action's files, so the action can run its own script. `steps.NAME.outputs.X` reads an earlier step's output (the step needs an `id`). The cache key is the operating system, the exact Python version and the hash of the requirements file, so a changed dependency list never restores an old cache. `restore-keys` is a fallback prefix: if the exact key is missing, restore the newest cache that starts with it. `hashFiles(...)` is a GitHub function that returns a hash of the named files.

### The platform tests itself

```yaml
  consumers:
    name: ${{ matrix.service }} through build-test
    strategy:
      fail-fast: false
      matrix:
        service: [svc-orders, svc-billing, svc-search]
    uses: ./.github/workflows/build-test.yml
    with:
      python: "3.12"
      working-directory: consumers/${{ matrix.service }}
      report-secret-names: true
```

A matrix can drive a reusable-workflow call too. In the *same* repository `uses: ./.github/workflows/...` is allowed at the job level.

### The pin checker as a required workflow

`pin-check.yml` runs on `pull_request` and on `workflow_call`, and its one script greps every `uses:` for a 40-hex SHA. It depends on nothing, so an organization ruleset can require it in every repository.

## Try it yourself

1. `grep -n "uses:" consumers/*/.github/workflows/ci.yml` shows the three callers' pinned SHAs.
2. `make secrets-report` prints the secrets table: `none`, `PACKAGE_TOKEN (named)`, `inherit`.
3. `.venv/bin/python -m pipeline.pins --internal sumitsr/platform-ci --allowlist allowed-actions.txt` prints `pins: every uses: is pinned, fresh, allowed`.
4. `wc -l consumers/*/.github/workflows/ci.yml` shows 8, 10 and 9 lines.
5. With Docker: `make run` runs the action's test workflow and `svc-orders` through the shared workflow, and `make demo-moved-tag` shows a tag move.

## Mistakes people make

- Missing `shell:` on a `run:` step in a composite action. The workflow fails to load.
- `uses: ./actions/...` inside a reusable workflow. The path is resolved in the caller's repository.
- `secrets: inherit` "to keep it simple". Every shared workflow can then read every secret.
- Changing an input name and keeping the tag. Consumers on that tag break on their next run.
- Pinning a SHA copied from a fork. The SHA exists but is not the code you reviewed.
- Pasting inputs straight into `run:`.

## Check yourself

1. When does GitHub resolve `@v2`? *(When the run starts, to the commit the tag points at that moment.)*
2. Why can't the reusable workflow use `./.github/actions/setup-toolchain`? *(`./` is resolved in the caller's repository.)*
3. What does `permissions: {}` followed by a job-level `contents: read` achieve? *(The token has no rights except reading contents, for that one job.)*
4. Why is the test command passed through `env`? *(So the expression engine never splices caller text into the script.)*
5. Why is the platform's own action pinned to a commit that precedes the workflow's? *(A commit cannot contain its own hash.)*

## Further reading

- Reusing workflows: https://docs.github.com/en/actions/sharing-automations/reusing-workflows
- Creating a composite action: https://docs.github.com/en/actions/sharing-automations/creating-actions/creating-a-composite-action
- Workflow syntax: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
- Security hardening, including script injection and pinning: https://docs.github.com/en/actions/reference/security/secure-use
