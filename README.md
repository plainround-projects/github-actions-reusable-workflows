# github-actions-reusable-workflows

A small CI platform for GitHub Actions: a reusable workflow that builds and tests a service, a composite action that sets up the toolchain, three consumer services that call them in under fifteen lines each, versioned releases with a careful breaking change, and a demonstration of why a consumer should pin the platform by commit rather than by a tag that can move.

| | |
| --- | --- |
| **Lesson** | `/prep/github-actions/project-reusable-workflows`, "A shared CI platform with a reusable workflow and a composite action" (`data-structure-explainer/src/content/tracks/github-actions/14-project-reusable-workflows.md` in the Plainround app) |
| **Planned hours** | 8 |
| **Level** | Intermediate |
| **Architecture** | [ARCHITECTURE.md](ARCHITECTURE.md), decisions in [docs/adr](docs/adr), release notes in [CHANGELOG.md](CHANGELOG.md) |

**Publish it as `sumitsr/platform-ci`.** The lesson's repository is called `platform-ci`; this folder is its root, and the workflows pin the platform's own commits under that name (`sumitsr/platform-ci/...@<full SHA>`). Push this repository with its history and its tags (`git push origin main --tags`) so the pinned commits exist on GitHub. The three consumers in [`consumers/`](consumers) are complete repositories on their own; to publish them as `svc-orders`, `svc-billing` and `svc-search`, copy each folder into a repository of that name. The history here is the lesson's story as real commits: the action, the workflow at `v1.0.0`, the consumers on `@v1`, the breaking change at `v2.0.0`, the consumers moved one at a time, then pinned.

## Prerequisites

| Tool | Version | Used for |
| --- | --- | --- |
| Python | 3.10 to 3.13 (tested with 3.13) | the pipeline tools, the tests, the consumers' code |
| GNU Make | 3.81 or newer | every command below |
| git | 2.30 or newer | resolving tags and commits, the moved-tag demo |
| [act](https://github.com/nektos/act) and Docker | act 0.2.89, Docker 24 or newer | `make run` and friends: workflows on your machine, in the image built from [ci/act-runner/Dockerfile](ci/act-runner/Dockerfile) |
| [actionlint](https://github.com/rhysd/actionlint) and shellcheck | 1.7.12 and 0.11 (`brew install actionlint shellcheck`) | linting workflows and scripts |
| [uv](https://docs.astral.sh/uv/) | any recent | only to recompile the lock files |
| `gh` CLI | any recent | only `scripts/org-policy.sh` (it has a `DRY_RUN=1` mode) |

No cloud account and no secrets. Tools are pinned with hashes in `requirements.txt`; each consumer has its own hashed `requirements.txt`.

## Setup, run, test, stop

```bash
make up                 # create .venv from the hash-pinned lock file and build the act runner image
make test               # the tools, the action, both workflows, the pin check, and the three consumers' own tests
make lint               # ruff, format check, mypy, actionlint, shellcheck, pin check (full SHA, fresh, allowed)
make audit              # known-vulnerability check of the locked dependencies
make run                # the action's test workflow, then svc-orders through build-test, both with act
make run-v1             # svc-orders as it was before v2: build-test@v1 with python-version (still works)
make run-all            # all three consumers through build-test at the pinned v2.0.0 commit
make demo-moved-tag     # lesson step 5: move v1 in a throwaway clone; @v1 runs the new code, the SHA does not
make secrets-report     # what the shared workflow can read, per consumer
make down               # remove leftover act containers
```

`make help` lists every target. `make test` and `make lint` need only Python; the `run` targets need Docker and act.

`scripts/run_consumer.sh` is how a consumer runs locally: its workflow says `uses: sumitsr/platform-ci/...@<ref>`, so the script resolves each ref in this repository's git history (the way GitHub does when a run starts), unpacks each commit with `git archive`, and hands act `--local-repository` mappings. It prints what it resolved:

```text
$ scripts/run_consumer.sh svc-orders
resolved .github/workflows/build-test.yml@fcd73fa6d311 -> fcd73fa6d311 (commit)
resolved .github/actions/setup-toolchain@d70ac3daf2d7 -> d70ac3daf2d7 (commit)
```

## Done when: the lesson's checklist and the proof for each line

| # | Done when (from the lesson) | Command | What proves it |
| --- | --- | --- | --- |
| 1 | A test workflow in the platform repository uses the action and prints its outputs. | `make run` (first command) | [`test-setup-toolchain.yml`](.github/workflows/test-setup-toolchain.yml) uses `./.github/actions/setup-toolchain`, prints `cache-hit` and `python-version`, and checks that a version the action cannot install (`latest`) is refused. Output below. The action has typed inputs, outputs and `shell: bash` on every `run` step (asserted in `tests/test_setup_toolchain_action.py`); its [README](.github/actions/setup-toolchain/README.md) documents them. |
| 2 | Each consumer repository's workflow is under fifteen lines and only calls the reusable workflow with its inputs. | `wc -l consumers/*/.github/workflows/ci.yml` and `make test` | 8, 10 and 9 lines. `tests/test_build_test_workflow.py` asserts, for each consumer, fewer than 15 lines, one job, a `uses:` of the platform and no `steps:`. `make run-all` runs each one through act. |
| 3 | The README explains the difference between passing a named secret and `secrets: inherit`, and which one you would allow by policy. | `make secrets-report` | [Secrets](#secrets-named-or-inherited) below, with the table the command prints. |
| 4 | Consumers on `v1` keep working during the upgrade, and the changelog says what each consumer must change. | `git tag -l`, `make run-v1`, [CHANGELOG.md](CHANGELOG.md) | Tags `v1.0.0`, `v1`, `v2.0.0`, `v2`. `make run-v1` runs a consumer that still calls `build-test@v1` with `python-version`: green after v2 exists (output below). `tests/test_build_test_workflow.py` fails when a release has no "Required changes for consumers" section; the `2.0.0` section gives the diff to apply. |
| 5 | The consumer pinned to `@v1` runs the changed code without any change of its own, and a consumer pinned to a full commit SHA does not. | `make demo-moved-tag` | Output below: the `@v1` run prints `THIS CODE WAS CHANGED AFTER RELEASE`, the run pinned to the commit of `v1.0.0` does not, and the script exits non-zero otherwise. |
| 6 | All consumers are pinned, the bot opens a pull request for the next platform release, and the README says how you would enforce SHA pinning across an organization. | `make lint`, [Pinning and keeping current](#pinning-and-keeping-current) | Every `uses:` in the platform and the consumers is a full SHA with the version in a comment (`python -m pipeline.pins` fails otherwise). Each consumer has a [`dependabot.yml`](consumers/svc-orders/.github/dependabot.yml) for `github-actions`. The organization section below says how to enforce it, with a script. |

### Step 1: the action, run by act

```text
[test-setup-toolchain/toolchain]   | setup-toolchain: python 3.12, cache keyed on requirements.txt
[test-setup-toolchain/toolchain]   | cache-hit=''
[test-setup-toolchain/toolchain]   | python-version='3.12.16'
[test-setup-toolchain/toolchain]   | Python 3.12.16
[test-setup-toolchain/toolchain]   ❗  ::error title=setup-toolchain::python-version must look like 3.12 or 3.12.7, got 'latest'
[test-setup-toolchain/toolchain]   ❌  Failure - Main Validate the inputs          <- the step given "latest"
[test-setup-toolchain/toolchain]   ✅  Success - Main The refusal really failed the step
[test-setup-toolchain/toolchain] 🏁  Job succeeded
```

### Step 2: all three consumers through the shared workflow (`make run-all`)

Each consumer's own `ci.yml` is run by act against the commits GitHub would resolve from its `uses:` line (the full SHA of `v2.0.0` and the action's pinned commit), and each runs its own tests:

```text
scripts/run_consumer.sh svc-orders
resolved .github/workflows/build-test.yml@fcd73fa6d311 -> fcd73fa6d311 (commit)
resolved .github/actions/setup-toolchain@d70ac3daf2d7 -> d70ac3daf2d7 (commit)
[ci/build-test/build-test]   | 10 passed in 1.17s
[ci/build-test/build-test] 🏁  Job succeeded
scripts/run_consumer.sh svc-billing
resolved .github/workflows/build-test.yml@fcd73fa6d311 -> fcd73fa6d311 (commit)
resolved .github/actions/setup-toolchain@d70ac3daf2d7 -> d70ac3daf2d7 (commit)
[ci/build-test/build-test]   | 11 passed in 0.22s
[ci/build-test/build-test] 🏁  Job succeeded
scripts/run_consumer.sh svc-search
resolved .github/workflows/build-test.yml@fcd73fa6d311 -> fcd73fa6d311 (commit)
resolved .github/actions/setup-toolchain@d70ac3daf2d7 -> d70ac3daf2d7 (commit)
[ci/build-test/build-test]   | 9 passed in 1.45s
[ci/build-test/build-test] 🏁  Job succeeded
```

### Step 4: a consumer still on `@v1`, after v2 exists

```text
$ make run-v1
resolved .github/workflows/build-test.yml@v1 -> 661d5382064e (label)
resolved .github/actions/setup-toolchain@d70ac3daf2d7 -> d70ac3daf2d7 (commit)
[ci/build-test/build-test]   | 10 passed in 9.82s
[ci/build-test/build-test]   ✅  Success - Main Test
[ci/build-test/build-test] 🏁  Job succeeded
```

### Step 5: the moved tag

`scripts/demo_moved_tag.sh` clones this repository into a temporary folder (this repository's tags are never touched), adds one commit to the reusable workflow that prints `THIS CODE WAS CHANGED AFTER RELEASE` (standing in for a malicious change), moves `v1` to it with `git tag -f`, then runs two consumers with act against that clone: `svc-orders` calling `@v1`, and `svc-search` calling the full commit of `v1.0.0`.

```text
v1 was 661d5382064e, now points to eb6bb50f3b83
== svc-orders, calling the shared workflow by the tag @v1
== svc-search, calling the shared workflow by the full commit of v1.0.0

-- by tag, lines containing the marker:
   [ci/build-test/build-test] ⭐ Run Main echo "THIS CODE WAS CHANGED AFTER RELEASE"
   [ci/build-test/build-test]   | THIS CODE WAS CHANGED AFTER RELEASE
   [ci/build-test/build-test]   ✅  Success - Main echo "THIS CODE WAS CHANGED AFTER RELEASE" [1.843428125s]
-- by commit, lines containing the marker:
RESULT: the consumer on @v1 ran the changed code; the consumer on the commit did not.
```

A real attacker, or a compromised maintainer account, could run anything the workflow is allowed to do, with the consumer's secrets in reach. The commit hash names one tree of files for ever; the tag is a label its owner can move.

## Secrets: named or inherited

`make secrets-report` reads each consumer's workflow and the shared workflow's declarations:

```text
consumer     secrets passed         what the shared workflow can read
svc-billing  PACKAGE_TOKEN (named)  PACKAGE_TOKEN only
svc-orders   none                   nothing
svc-search   inherit                every secret in svc-search (including ones it never asked for)
```

- **Nothing passed (`svc-orders`).** Without a `secrets:` key the shared workflow receives no secret. This is the default and the safe one.
- **One named secret (`svc-billing`).** `secrets: { PACKAGE_TOKEN: ${{ secrets.PACKAGE_TOKEN }} }`. The caller states exactly which secret crosses the boundary, and a later change to the shared workflow cannot read a secret that nobody passed. The shared workflow declares `PACKAGE_TOKEN` under `workflow_call.secrets` and ignores anything else.
- **`secrets: inherit` (`svc-search`).** Hands over every secret the caller can see, whether the callee asks for it or not, including secrets added next year. A change to the shared workflow, or to a tag it is called by, can then read them all.

**Policy: allow the named form, forbid `inherit`.** `svc-search` keeps `inherit` on purpose, as the example the table shows; in a real organization that line would be a review failure. To see the secret names a called workflow actually has, pass `report-secret-names: true`: it prints names only, never values (the platform's own `ci.yml` does, and the runtime list of an `inherit` caller is longer).

## Pinning and keeping current

- Every consumer calls the workflow as `uses: sumitsr/platform-ci/.github/workflows/build-test.yml@fcd73fa6d3117df6168d8f822e79577ac99cedfe # v2.0.0`. The comment is for people and for Dependabot, which reads it and opens a pull request like the lesson's `Bump sumitsr/platform-ci/.github/workflows/build-test.yml from 2.0.0 to 2.1.0` when a new release exists. Each consumer's [`.github/dependabot.yml`](consumers/svc-orders/.github/dependabot.yml) turns that on.
- The platform pins its own third-party actions the same way, and pins its own composite action to the commit of its last change ([ADR 0002](docs/adr/0002-pin-the-platforms-own-action-to-the-commit-of-its-last-change.md)).
- **Enforcing it across an organization.** (1) The organization setting "Require actions to be pinned to a full-length commit SHA" (Settings, Actions, General; `sha_pinning_required` in the API) makes GitHub refuse a run that uses a tag. (2) The allowed-actions list (`allowed-actions.txt` here) limits which actions may run at all. (3) A ruleset with a *required workflow* ([`pin-check.yml`](.github/workflows/pin-check.yml), registered by [`docs/org-ruleset.json`](docs/org-ruleset.json)) fails any pull request, in any repository, that adds a `uses:` without a SHA; it has no dependencies so it runs anywhere. (4) An update bot keeps the pins current so that pinning is not a tax. `scripts/org-policy.sh ORG` applies 1 to 3 (use `DRY_RUN=1` first). It was written to the API's documented shape and not run: a personal account has no organization.

## Stretch goals

| Stretch (from the lesson) | Built? |
| --- | --- |
| Add a required workflow or ruleset at organization level that every repository must run. | Written, not run. [`pin-check.yml`](.github/workflows/pin-check.yml) (tested against small repositories in `tests/test_pin_check_workflow.py`), [`docs/org-ruleset.json`](docs/org-ruleset.json) and [`scripts/org-policy.sh`](scripts/org-policy.sh). It needs an organization to apply. |
| Publish the composite action as a JavaScript action with tests and compare maintenance effort. | No. A JavaScript action adds a build step and a committed `dist/` for logic that is a few lines of shell; [ADR 0001](docs/adr/0001-a-reusable-workflow-and-a-composite-action.md) records why not. |
| Add a workflow that fails if any workflow in a repository uses an action not on an allowed list. | Yes. `python -m pipeline.pins --allowlist allowed-actions.txt` (part of `make lint`), tested in `tests/test_pins.py`. |

## What is simplified for teaching

Only what the lesson scopes out, plus where this build differs from the lesson's text:

- **One repository holds the platform and the consumers**, because one repository was asked for. Each consumer folder is a complete repository; the lesson's `platform-ci/actions/setup-toolchain` is at `.github/actions/setup-toolchain` here, which is where the task's conventions put composite actions.
- **The pinned commits are this history's commits**, so the repository has to be published as `sumitsr/platform-ci` with its history and tags. Publishing under another name needs a rewrite of every pinned reference, which would change the commits.
- **No real GitHub run was possible while this was written.** The commands in "Proof" run on your machine with act and git; the runtime facts only GitHub can show are listed below.
- The lesson uses `actions/checkout@v4` and `actions/setup-python@v5`; every action here is pinned to a full SHA of the current major (checkout v7.0.1, setup-python v7.1.0, cache v6.1.0). The lesson's `pip install -r requirements.txt` is `--require-hashes` here, and pytest is 9.0.3 because `pip-audit` flags 8.3.3.
- The lesson's reusable workflow puts `${{ inputs.test-command }}` straight into `run:`; here it arrives through an environment variable and `bash -c`, so the expression engine never splices it into script text.
- The lesson's action hard-codes `~/.cache/pip`; here the cache path comes from `python -m pip cache dir`.

**To confirm on GitHub after the first push** (none of these can be shown offline): the second run of `test-setup-toolchain` prints `cache-hit='true'`; the consumers' runs call the workflow at the pinned commit; the `consumers` job of `ci.yml` (the shared workflow called from this repository on each consumer's folder) is green; Dependabot opens the version-bump pull request after the next release; the organization policy script applies.

## Project structure

```text
.github/
  workflows/         build-test.yml (the reusable workflow), test-setup-toolchain.yml, ci.yml (the platform tests itself),
                     pin-check.yml (a dependency-free required workflow).
  actions/setup-toolchain/   action.yml, validate-inputs.sh, README.md. Tests in tests/test_setup_toolchain_action.py.
  dependabot.yml     actions and pip for the platform.
consumers/
  svc-orders/ svc-billing/ svc-search/    each a repository of its own: src/<pkg>/{domain,application,infrastructure,interfaces},
                     tests/, requirements.in/.txt, .github/workflows/ci.yml (under fifteen lines), .github/dependabot.yml.
pipeline/            pins (full SHA, fresh internal pin, allowed list), platform_refs (resolve @ref like GitHub), secrets_report.
scripts/             run_consumer.sh, demo_moved_tag.sh, org-policy.sh, install-actionlint.sh.
demo/                the two consumer workflows the moved-tag demo uses.
tests/               the tools, the action, build-test.yml, pin-check.yml.
docs/                adr/ (three decision records), org-ruleset.json.
ci/act-runner/       the Dockerfile of the image act uses as ubuntu-latest.
CHANGELOG.md         per release, what every consumer must change.
Makefile             the only commands a reader needs (make help).
```

Each consumer follows the layered rule inside its own `src`: domain imports nothing; application imports the domain; infrastructure and interfaces import below them; nothing imports interfaces (checked by review and by the layout; the platform's tools are flat modules).

To release: commit the change (action first, then the workflow that pins it), tag `vX.Y.Z` (annotated), move the major tag (`git tag -f -a vX`), add the CHANGELOG section with "Required changes for consumers", push `main` and the tags.

## Troubleshooting

- **`make run` cannot find the image:** run `make up`; it builds `gha-projects-act-runner:ubuntu-24.04`.
- **`make lint` says "stale internal pin":** you changed the action after the workflow pinned it. Commit the action alone, then update the commit named in `build-test.yml` to the one the message prints.
- **act asks for a GitHub token or tries to clone `github.com/sumitsr/platform-ci`:** use `scripts/run_consumer.sh`, not `act` directly; it supplies the local checkouts.
- **`make demo-moved-tag` leaves nothing behind:** it works in a temporary clone and deletes it; unpacked commits stay in `build/platform/` (ignored by git) and can be deleted.

## Author and license

Written by Sumit Srivastava. Released under the MIT License, see [LICENSE](LICENSE). Changes are in [CHANGELOG.md](CHANGELOG.md).
