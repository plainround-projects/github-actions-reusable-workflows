# GitHub Actions: reusable workflows and composite actions

## What it is

GitHub Actions is the automation service built into GitHub. You describe jobs in YAML files (see `yaml.md`); GitHub starts a fresh machine (a **runner**) for each job and runs the steps. A **workflow** is one file in `.github/workflows/`. An **event** (a push, a pull request) starts it. A **job** is a list of **steps** that run on one runner. A step is either a shell command (`run:`) or a ready-made **action** (`uses:`).

This repository is about *sharing* automation, which needs three more ideas:

- A **reusable workflow** is a whole workflow that other workflows call as if it were a job. It declares what it accepts with `on: workflow_call`.
- A **composite action** is an action made of steps (`runs: using: composite`). A workflow calls it from inside a job, as one step.
- A **ref** names a version of someone else's code: a **tag** like `v2` (a label its owner can move), a branch, or a **commit SHA** (a 40-character fingerprint of one exact state, which can never move).

<!-- words -->

<details>
<summary><b>Words this note uses, in case they are new to you</b> (click to open)</summary>

- **shell**: The program inside a terminal that reads what you type and starts other programs. Bash is a shell.
- **PATH**: An environment variable listing the folders where the shell looks for programs. Typing `node` works because the folder holding `node` is in `PATH`.
- **regex**: Short for regular expression: a compact pattern that describes text, such as `^[0-9]{12}$` (exactly twelve digits).
- **hash**: A fixed-length fingerprint computed from some data. The same data always gives the same hash; any change gives a different one. SHA-256 and SHA-1 are two ways of computing one.
- **SHA**: A family of hash functions. A Git **commit SHA** is a 40-character hexadecimal fingerprint that names one exact commit.
- **branch**: A movable name for a line of commits in Git. `main` is the usual name of the primary line.
- **pull request**: A proposal on GitHub to merge the commits of one branch into another. People review it and automation checks it before it is merged.
- **fork**: Your own copy of someone else's repository on GitHub. Strangers propose changes by changing their fork and opening a pull request from it.
- **secret**: A value such as a password stored in a repository's settings. Workflows can read it, but GitHub hides it in logs.
- **API**: Application programming interface: a set of requests a program can send to another program or service, with documented answers. A web API is called over the internet with HTTP.
- **YAML**: A plain-text format for structured data that uses indentation instead of braces. GitHub workflows are YAML files.
- **token**: A secret text that proves who is asking when a program talks to a service, instead of a password. Tokens can be limited in what they may do and in how long they last.
- **Docker**: A tool that builds images and runs containers.
- **package**: In Python, a folder with an `__init__.py` file that can be imported as a unit; also a bundle of code installed with pip.
- **dependency**: A package that your project needs in order to work.
- **function**: A named piece of code that takes inputs (parameters), does something, and may return a result.
- **interface**: A description of the shape something must have: which fields and methods. Code that depends only on the interface can accept any object of that shape.
- **list**: An ordered collection of values written one after another.
- **boolean**: A value that is either true or false.
- **folder**: A container for files and other folders on disk (also called a directory).
- **version**: A number such as `1.2.3` that names one release of software (major.minor.patch).
- **test**: A small program that uses your code and checks that the answer is the one you expected.

</details>

<!-- /words -->

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

<!-- walk:.github/workflows/build-test.yml -->
### `.github/workflows/build-test.yml`, line by line

Lines 1 to 5:

```yaml
name: build-test

# The shared workflow every service calls. Version 2 API: the Python input is `python` (it was `python-version` in v1).

on:
  workflow_call:
```

`name` is the label in GitHub's list. The comment says this is the **shared workflow** every service calls, and that version 2's API renamed the input `python-version` to `python`. `on: workflow_call:` makes it a **reusable workflow**: it does not start on events; it is started by other workflows that call it with `uses:`. (See the explanation of reusable workflows above.)

Lines 6 to 26:

```yaml
    inputs:
      python:
        description: Python version to test with, such as 3.12.
        type: string
        required: true
      test-command:
        description: Command that runs the tests, run with bash from the working directory.
        type: string
        default: pytest -q
      working-directory:
        description: Folder of the service inside the caller's repository.
        type: string
        default: .
      report-secret-names:
        description: Print the names (never the values) of the secrets this workflow can read.
        type: boolean
        default: false
    secrets:
      PACKAGE_TOKEN:
        description: Token for a private package index, if the service uses one.
        required: false
```

`inputs:` lists the settings a caller may pass with `with:`. Each input has a `description`, a `type` (`string` or `boolean`) and either `required: true` or a `default`. `python` (required text) is the Python version to test with. `test-command` defaults to `pytest -q`; `working-directory` (default `.`) is the service's folder inside the caller's repository; `report-secret-names` (boolean, default `false`) asks the workflow to print the **names** of the secrets it can read. `secrets:` declares the secrets a caller may pass by name: `PACKAGE_TOKEN`, optional (`required: false`).

Lines 27 to 32:

```yaml
    outputs:
      cache-hit:
        description: "'true' when the pip cache was restored from the exact key."
        value: ${{ jobs.build-test.outputs.cache-hit }}

permissions: {}
```

`outputs:` publishes a value back to the caller: `cache-hit`, whose value `${{ jobs.build-test.outputs.cache-hit }}` is copied from the job's output of the same name. The description is quoted because it contains an apostrophe and colon-free text; YAML needs quotes around texts starting with `'`. `permissions: {}` at the top gives every job no scopes unless it asks.

Lines 34 to 45:

```yaml
jobs:
  build-test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    permissions:
      contents: read
    outputs:
      cache-hit: ${{ steps.toolchain.outputs.cache-hit }}
    defaults:
      run:
        shell: bash
        working-directory: ${{ inputs.working-directory }}
```

The single job `build-test`: a Linux runner, a 15-minute limit, only `contents: read`, and the job output `cache-hit` taken from the step with `id: toolchain`. `defaults.run` sets, for every `run:` step, the shell (`bash`) and the working directory (`${{ inputs.working-directory }}`), so each command runs inside the service's folder.

Lines 46 to 55:

```yaml
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - name: List the secret names this workflow can read
        if: inputs.report-secret-names
        env:
          SECRETS_CONTEXT: ${{ toJSON(secrets) }}
        run: |
          printf '%s' "$SECRETS_CONTEXT" | jq -r 'keys[] | "can read secret=" + .'
```

Steps. (1) `actions/checkout` pinned to a full commit SHA (with its version in the comment) and `persist-credentials: false`. (2) A step that runs only `if: inputs.report-secret-names`: `SECRETS_CONTEXT: ${{ toJSON(secrets) }}` puts all secrets the workflow can read into an environment variable as JSON text; the script pipes it into `jq` (`printf '%s' "$SECRETS_CONTEXT" | jq -r 'keys[] | "can read secret=" + .'`) which prints only the **keys** (the names), never the values. `printf '%s'` prints the text exactly, with no interpretation. `-r` prints raw text without JSON quotes; `keys[]` yields each name; `"can read secret=" + .` joins the words and the name.

Lines 56 to 60:

```yaml
      - id: toolchain
        uses: sumitsr/platform-ci/.github/actions/setup-toolchain@d70ac3daf2d7ada75bcbd1bc34d83a6f29ce9abd
        with:
          python-version: ${{ inputs.python }}
          requirements-file: ${{ inputs.working-directory }}/requirements.txt
```

The platform's own composite action is used by repository path at a full commit (`d70ac3da...`): `sumitsr/platform-ci/.github/actions/setup-toolchain@<SHA>`. `id: toolchain` lets later steps and the job output refer to this step. Its inputs: the Python version from the workflow's `python` input, and the requirements file inside the working directory.

Lines 61 to 69:

```yaml
      # PACKAGE_TOKEN is for a private index the service configures in its own pip.conf; it is empty when not passed.
      - name: Install dependencies
        env:
          PACKAGE_TOKEN: ${{ secrets.PACKAGE_TOKEN }}
        run: python -m pip install --require-hashes -r requirements.txt
      - name: Test
        env:
          TEST_COMMAND: ${{ inputs.test-command }}
        run: bash -c "$TEST_COMMAND"
```

A comment explains `PACKAGE_TOKEN`: it is for a private package index the service configures in its own `pip.conf`; it is empty when not passed. The install step passes it through `env:` (so only this step can see it) and runs `python -m pip install --require-hashes -r requirements.txt` (hash-checked install of the locked packages). The test step passes the caller's command through `env: TEST_COMMAND` and runs `bash -c "$TEST_COMMAND"`: the command is data in a variable, never pasted into the script text by an expression.

<!-- /walk:.github/workflows/build-test.yml -->

<!-- walk:.github/actions/setup-toolchain/action.yml -->
### `.github/actions/setup-toolchain/action.yml`, line by line

Lines 1 to 2:

```yaml
name: Set up toolchain
description: Install a pinned Python and restore the pip cache, keyed on the dependency file.
```

`name` and `description` label the action. A **composite action** is a reusable group of steps stored in a folder as `action.yml`; callers use it with `uses:`.

Lines 4 to 19:

```yaml
inputs:
  python-version:
    description: Python version to install, such as 3.12 or 3.12.7.
    required: true
  requirements-file:
    description: Dependency file whose hash keys the pip cache.
    required: false
    default: requirements.txt

outputs:
  cache-hit:
    description: "'true' when the pip cache was restored from the exact key, otherwise empty."
    value: ${{ steps.cache.outputs.cache-hit }}
  python-version:
    description: The exact Python version that was installed.
    value: ${{ steps.python.outputs.python-version }}
```

`inputs`: `python-version` (required) and `requirements-file` (optional, default `requirements.txt`; its hash keys the cache). `outputs`: `cache-hit` (copied from the step with id `cache`) and `python-version` (the exact version installed, from the step with id `python`). Descriptions are required by a test.

Lines 21 to 29:

```yaml
runs:
  using: composite
  steps:
    - name: Validate the inputs
      shell: bash
      env:
        INPUT_PYTHON_VERSION: ${{ inputs.python-version }}
        INPUT_REQUIREMENTS_FILE: ${{ inputs.requirements-file }}
      run: bash "$GITHUB_ACTION_PATH/validate-inputs.sh"
```

`runs.using: composite` marks the type. Step 1 validates the inputs. A composite action's `run:` steps must name their `shell`. The two inputs reach the script only through `env:` as `INPUT_PYTHON_VERSION` and `INPUT_REQUIREMENTS_FILE`. `$GITHUB_ACTION_PATH` is a variable GitHub sets to the folder where the action's files are, so `bash "$GITHUB_ACTION_PATH/validate-inputs.sh"` runs the script stored next to the action.

Lines 31 to 34:

```yaml
    - id: python
      uses: actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0 # v7.1.0
      with:
        python-version: ${{ inputs.python-version }}
```

Step 2, `id: python`: the pinned `actions/setup-python` installs the requested Python and exposes `python-version`, the exact version.

Lines 36 to 38:

```yaml
    - id: pip-dir
      shell: bash
      run: echo "path=$(python -m pip cache dir)" >> "$GITHUB_OUTPUT"
```

Step 3, `id: pip-dir`: `python -m pip cache dir` prints the folder where pip keeps downloads. `echo "path=..." >> "$GITHUB_OUTPUT"` appends a line `path=<folder>` to the file named by `$GITHUB_OUTPUT`; GitHub reads that file after the step and makes `path` available as `steps.pip-dir.outputs.path`. This is how a step publishes an output.

Lines 40 to 46:

```yaml
    - id: cache
      uses: actions/cache@55cc8345863c7cc4c66a329aec7e433d2d1c52a9 # v6.1.0
      with:
        path: ${{ steps.pip-dir.outputs.path }}
        key: pip-${{ runner.os }}-${{ steps.python.outputs.python-version }}-${{ hashFiles(inputs.requirements-file) }}
        restore-keys: |
          pip-${{ runner.os }}-${{ steps.python.outputs.python-version }}-
```

Step 4, `id: cache`: `actions/cache` saves and restores that folder. `key` is `pip-<operating system>-<exact Python version>-<hash of the requirements file>` (`runner.os` is the runner's OS name; `hashFiles(inputs.requirements-file)` is a built-in that hashes the file). If an exact key is found, `cache-hit` is `true`. `restore-keys` lists a shorter prefix: when no exact key exists, the newest cache with that prefix is restored, so a changed requirements file still starts from a nearly full cache.

Lines 48 to 50:

```yaml
    - name: Show the toolchain
      shell: bash
      run: python --version
```

Step 5 prints `python --version` so the log shows which interpreter is in use.

<!-- /walk:.github/actions/setup-toolchain/action.yml -->

<!-- walk:.github/workflows/ci.yml -->
### `.github/workflows/ci.yml`, line by line

Lines 1 to 15:

```yaml
name: ci

# The platform tests itself: its tools, the composite action, the consumers' code, and the shared workflow

# (called on each consumer exactly as a consumer repository would call it).

on:
  push:
    branches: [main]
  pull_request:

permissions:
  contents: read

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}
```

The platform tests itself. It runs on pushes to `main` and on all pull requests. Top-level `permissions: contents: read` and `concurrency`: runs of the same branch share a group; a newer run cancels an older one except on `main` (`cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}`).

Lines 17 to 37:

```yaml
jobs:
  lint:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          fetch-depth: 0 # the internal pin check reads the history of the action folder
          persist-credentials: false
      - uses: actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0 # v7.1.0
        with:
          python-version: "3.12"
          cache: pip
          cache-dependency-path: requirements.txt
      - run: pip install --require-hashes -r requirements.txt
      - run: scripts/install-actionlint.sh
      - run: echo "$PWD/.tools/bin" >> "$GITHUB_PATH"
      - run: make lint BIN=
      - run: make audit BIN=
```

Job `lint` (10-minute limit). Checkout uses `fetch-depth: 0`, which downloads the **whole history** instead of only the latest commit, because the internal pin check reads Git history of the action folder. `actions/setup-python` installs Python 3.12 and caches pip (`cache: pip`, keyed on `requirements.txt` by `cache-dependency-path`). Then: `pip install --require-hashes -r requirements.txt` (the tools), `scripts/install-actionlint.sh`, add `.tools/bin` to the path for later steps (`echo ... >> "$GITHUB_PATH"`), `make lint BIN=` and `make audit BIN=`. `BIN=` sets the Makefile variable to empty so it calls tools straight from the PATH, because in CI they are installed globally.

Lines 39 to 55:

```yaml
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          fetch-depth: 0 # tests resolve tags and pinned commits in the history
          persist-credentials: false
      - uses: actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0 # v7.1.0
        with:
          python-version: "3.12"
          cache: pip
          cache-dependency-path: requirements.txt
      - run: pip install --require-hashes -r requirements.txt
      - run: make test BIN=
```

Job `test`: the same checkout with full history (tests resolve tags and pinned commits), Python 3.12, install the tools, `make test BIN=`.

Lines 57 to 70:

```yaml
  # The shared workflow, called from this repository on each consumer's folder.
  consumers:
    name: ${{ matrix.service }} through build-test
    strategy:
      fail-fast: false
      matrix:
        service: [svc-orders, svc-billing, svc-search]
    permissions:
      contents: read
    uses: ./.github/workflows/build-test.yml
    with:
      python: "3.12"
      working-directory: consumers/${{ matrix.service }}
      report-secret-names: true
```

Job `consumers`: it calls the shared workflow from this same repository (`uses: ./.github/workflows/build-test.yml`) once per consumer. `strategy.matrix.service: [svc-orders, svc-billing, svc-search]` runs the job three times, with `${{ matrix.service }}` set each time; `fail-fast: false` lets the other two finish if one fails. `name:` labels each run. `with:` passes `python: "3.12"`, the service's folder, and `report-secret-names: true`. A job that calls a reusable workflow has no `runs-on` or `steps`; its `permissions` cap what the called workflow may get.

<!-- /walk:.github/workflows/ci.yml -->

<!-- walk:.github/workflows/pin-check.yml -->
### `.github/workflows/pin-check.yml`, line by line

Lines 1 to 10:

```yaml
name: pin-check

# Fails when any `uses:` in a repository's workflows or actions names a tag or branch instead of a full commit SHA.

# It has no dependencies, so an organization ruleset (docs/org-ruleset.json) can require it in every repository, and any

# repository can call it with `uses: sumitsr/platform-ci/.github/workflows/pin-check.yml@<full SHA>`.

on:
  pull_request:
  workflow_call:

permissions: {}
```

A small workflow that fails if any `uses:` names a tag or branch instead of a full commit SHA. It triggers on pull requests and on `workflow_call`, so an organization ruleset can require it everywhere and any repository can call it. It has no dependencies. No permissions at the top.

Lines 12 to 21:

```yaml
jobs:
  pin-check:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
```

One job, five-minute limit, `contents: read`, and a checkout without saved credentials.

Lines 22 to 37:

```yaml
      - name: Every uses names a full commit SHA, a local path or a digest
        shell: bash
        run: |
          set -uo pipefail
          files=$(find .github -type f \( -name '*.yml' -o -name '*.yaml' \) 2>/dev/null | sort)
          [ -n "$files" ] || { echo "no workflow files"; exit 0; }
          # shellcheck disable=SC2086
          bad=$(grep -nE '^[[:space:]-]*uses:' $files \
            | grep -vE 'uses:[[:space:]]*"?(\./|docker://[^[:space:]]+@sha256:[0-9a-f]{64})' \
            | grep -vE 'uses:[[:space:]]*"?[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+@[0-9a-f]{40}("|[[:space:]]|$)' || true)
          if [ -n "$bad" ]; then
            echo "These references are not pinned to a full commit SHA:"
            echo "$bad"
            exit 1
          fi
          echo "pin-check: every uses is pinned"
```

The script, line by line. `set -uo pipefail` (no `-e`, because the script handles failures itself): unset variables are errors and a pipeline fails if any part fails. `files=$(find .github -type f \( -name '*.yml' -o -name '*.yaml' \) 2>/dev/null | sort)` lists every YAML file under `.github` (`\( ... -o ... \)` groups two name tests with *or*; `2>/dev/null` throws away error messages, for a repository with no `.github`; `sort` makes the order stable). `[ -n "$files" ] || { echo "no workflow files"; exit 0; }` prints a note and succeeds if there are none. The comment `# shellcheck disable=SC2086` silences ShellCheck for the next line, where `$files` is deliberately unquoted so each file name is a separate argument. `bad=$( ... )` collects offending lines: the first `grep -nE '^[[:space:]-]*uses:' $files` prints every line that is a `uses:` entry, with its file and line number (`-n`, `-E` extended regex; `[[:space:]-]*` allows leading spaces and a list dash). The next `grep -vE` (`-v` = remove matching lines) drops references that are local (`./`) or Docker images pinned by a 64-hex digest; the third drops references of the form `owner/name@` plus 40 hex characters followed by a quote, a space or the end of line. `|| true` keeps the script going when `grep` finds nothing to print (it exits 1 then). If `bad` is not empty, the lines are printed and the script exits 1; otherwise it prints `pin-check: every uses is pinned`.

<!-- /walk:.github/workflows/pin-check.yml -->

<!-- walk:.github/workflows/test-setup-toolchain.yml -->
### `.github/workflows/test-setup-toolchain.yml`, line by line

Lines 1 to 11:

```yaml
name: test-setup-toolchain

# Uses the composite action from this repository the way a consumer would and prints its outputs.

# The first run prints an empty cache-hit (a miss); the second prints true.

on:
  push:
    branches: [main]
    paths: [".github/actions/setup-toolchain/**", ".github/workflows/test-setup-toolchain.yml", "requirements.txt"]
  pull_request:
    paths: [".github/actions/setup-toolchain/**", ".github/workflows/test-setup-toolchain.yml", "requirements.txt"]
  workflow_dispatch:
```

The comment explains that this workflow uses the composite action from the repository as a consumer would, and that the first run prints an empty `cache-hit` (a miss) while the second prints `true`. Triggers: pushes to `main` and pull requests, but only when files matching the `paths` filter change (the action folder, this workflow file or the requirements file), plus `workflow_dispatch` (a manual button).

Lines 13 to 25:

```yaml
permissions:
  contents: read

jobs:
  toolchain:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
```

`contents: read`, one job, 10 minutes, checkout without saved credentials.

Lines 27 to 39:

```yaml
      - id: toolchain
        uses: ./.github/actions/setup-toolchain
        with:
          python-version: "3.12"

      - name: Print the outputs
        env:
          CACHE_HIT: ${{ steps.toolchain.outputs.cache-hit }}
          PYTHON_VERSION: ${{ steps.toolchain.outputs.python-version }}
        run: |
          echo "cache-hit='${CACHE_HIT}'"
          echo "python-version='${PYTHON_VERSION}'"
          python --version
```

`uses: ./.github/actions/setup-toolchain` calls the local action by relative path (`./` means this repository). The next step prints the action's two outputs through `env:` (`CACHE_HIT`, `PYTHON_VERSION`) with `echo`, and then `python --version`.

Lines 41 to 51:

```yaml
      - name: A version the action cannot install is refused
        id: refused
        continue-on-error: true
        uses: ./.github/actions/setup-toolchain
        with:
          python-version: latest

      - name: The refusal really failed the step
        env:
          OUTCOME: ${{ steps.refused.outcome }}
        run: test "$OUTCOME" = "failure"
```

A negative test inside the workflow. The action is given `latest`, which its validation must refuse. `continue-on-error: true` lets the workflow carry on after that step fails; `id: refused` names it. The last step reads the step's `outcome` (`steps.refused.outcome` is the real result before `continue-on-error` is applied) and runs `test "$OUTCOME" = "failure"`, which exits non-zero (and so fails the job) unless the step really failed.

<!-- /walk:.github/workflows/test-setup-toolchain.yml -->

<!-- walk:demo/consumer-on-tag.yml -->
### `demo/consumer-on-tag.yml`, line by line

Lines 1 to 8:

```yaml
name: ci
on: [push, pull_request]
permissions:
  contents: read
jobs:
  ci:
    uses: sumitsr/platform-ci/.github/workflows/build-test.yml@v1
    with: { python-version: "3.12" }
```

A consumer workflow as it looked in version 1: `on: [push, pull_request]` is a list of events; the job calls the shared workflow by the **moving tag** `@v1` and passes the old input name `python-version` (`with: { python-version: "3.12" }` is a mapping in one line). It is a demonstration file, used by `make run-v1` and the moved-tag demo.

<!-- /walk:demo/consumer-on-tag.yml -->

<!-- walk:demo/consumer-on-commit.yml -->
### `demo/consumer-on-commit.yml`, line by line

Lines 1 to 8:

```yaml
name: ci
on: [push, pull_request]
permissions:
  contents: read
jobs:
  ci:
    uses: sumitsr/platform-ci/.github/workflows/build-test.yml@ORIGINAL_COMMIT # v1.0.0
    with: { python-version: "3.12" }
```

The same consumer pinned to a **commit**: the text `ORIGINAL_COMMIT` is a placeholder that `scripts/demo_moved_tag.sh` replaces (with `sed`) by the real hash of the `v1.0.0` commit. The comment `# v1.0.0` names the version.

<!-- /walk:demo/consumer-on-commit.yml -->

<!-- walk:consumers/svc-orders/.github/workflows/ci.yml -->
### `consumers/svc-orders/.github/workflows/ci.yml`, line by line

Lines 1 to 8:

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

The consumer's whole workflow: eight lines. `on: [push, pull_request]`; `permissions: contents: read`; one job `ci` that calls the shared workflow at the full commit of release v2.0.0 (the comment names the version) and passes `python: "3.12"`. The other two consumers are the same except for their own `with:` values.

<!-- /walk:consumers/svc-orders/.github/workflows/ci.yml -->

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
