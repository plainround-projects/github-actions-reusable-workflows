# act

## What it is

act is a command-line tool that runs GitHub Actions workflows on your own machine. It reads the workflow YAML, starts a Docker container for each job (see `docker.md`) and runs the steps inside. It is an imitation of GitHub's runner, not an exact copy. This repository uses act 0.2.89.

## Why this repository uses it

Everything in the lesson normally needs GitHub and several repositories. With act the repository can run a consumer's real `ci.yml`, calling the shared workflow and the composite action, and can show the moved-tag demonstration, with no push.

## Where it appears

| Path | What it does with act |
| --- | --- |
| `.actrc` | Default options (runner image, architecture). |
| `scripts/run_consumer.sh` | Runs one consumer with `--local-repository` mappings made from Git. |
| `scripts/demo_moved_tag.sh` | Runs two consumers against a throwaway clone. |
| `Makefile` | `run`, `run-v1`, `run-all`, `demo-moved-tag`, `down`. |
| `ci/act-runner/Dockerfile` | The image act uses as `ubuntu-latest`. |

## How it works underneath

act builds the job graph from the YAML, picks an image for each `runs-on` label, starts a container, copies the working folder in, downloads each `uses:` action from github.com (cached under `~/.cache/act`) and runs the steps. A step that uses a *remote reusable workflow* or action normally makes act clone it. `--local-repository 'owner/repo@ref=/path'` says "when something asks for this repository at this ref, use the folder instead". It cannot run Windows or macOS jobs.

## Walkthrough of this repository's use

### `.actrc`

```text
-P ubuntu-latest=gha-projects-act-runner:ubuntu-24.04
--pull=false
--container-architecture linux/arm64
--container-daemon-socket -
```

`-P` maps the runner label to our image. `--pull=false` never downloads it. `--container-architecture linux/arm64` runs native containers on Apple silicon (remove on Intel). `--container-daemon-socket -` stops act mounting Docker's socket file, which does not exist inside Docker Desktop's VM. act reads `.actrc` from the folder where you start it, so the scripts start `act` from the repository root and use `-C` to pick the workspace.

### The test workflow

```make
act push --concurrent-jobs 1 -W .github/workflows/test-setup-toolchain.yml
```

`push` simulates a push; `-W` selects one workflow; `--concurrent-jobs 1` runs jobs one at a time. The workflow uses `./.github/actions/setup-toolchain` (a local path), prints the action's outputs, and then calls it with `python-version: latest` under `continue-on-error: true` to prove the validation step rejects it.

### Running a consumer against the platform's own history

```bash
act push -C "consumers/$service" -W "$workflow" "${flags[@]}" "${@:3}"
```

`-C DIR` sets the workspace (the consumer's folder). `-W` is the consumer's `ci.yml`, which says `uses: sumitsr/platform-ci/.github/workflows/build-test.yml@<ref>`. act would try to clone that from github.com, where the repository does not exist yet. So the script first resolves the ref in this repository's Git history (`pipeline/platform_refs.py`), unpacks each needed commit with `git archive`, and adds:

```text
--local-repository sumitsr/platform-ci@fcd73fa6d3117df6168d8f822e79577ac99cedfe=/.../build/platform/fcd73fa6d3117df6168d8f822e79577ac99cedfe
--local-repository sumitsr/platform-ci@d70ac3daf2d7ada75bcbd1bc34d83a6f29ce9abd=/.../build/platform/d70ac3daf2d7ada75bcbd1bc34d83a6f29ce9abd
```

One mapping per reference: the reusable workflow, and the composite action that the reusable workflow itself uses. The key includes the ref exactly as written in the YAML (a tag or a SHA), so the same commit can be mapped under two spellings.

### The moved-tag demonstration

`scripts/demo_moved_tag.sh` clones the repository, adds one harmless extra step to the reusable workflow, moves the tag `v1` to that commit, and runs `run_consumer.sh` twice with `PLATFORM_GIT` set to the clone: `svc-orders` calling `@v1` and `svc-search` calling the commit of `v1.0.0`. Because `run_consumer.sh` resolves refs the way GitHub does, the first run executes the new step and the second does not. The script exits 0 only when exactly that happens.

### Details that matter

- The cache service: act's own cache and artifact servers cannot be reached from a runner container on Docker Desktop, so `actions/cache` warns and continues (the install runs in full). Consumers' workflows have no artifact upload, so nothing else is replaced.
- Python installed by `setup-python` goes into `/opt/hostedtoolcache`, a Docker volume act creates and reuses, so each Python is downloaded once.
- A busy Docker daemon can make act exit with an error after a job reported "Job succeeded"; `run_consumer.sh` checks the log and accepts it.

## Try it yourself

1. `act --version` prints `act version 0.2.89`.
2. `.venv/bin/python -m pipeline.platform_refs consumers/svc-orders/.github/workflows/ci.yml --platform sumitsr/platform-ci` prints the two references act will be told about.
3. `make run-all` (Docker needed) runs all three consumers; each ends with `Job succeeded`.
4. `make demo-moved-tag` prints `v1 was 661d5382064e, now points to eb6bb50f3b83` (the second id differs) and ends with `RESULT: the consumer on @v1 ran the changed code; the consumer on the commit did not.`
5. `ls build/platform` lists the unpacked commits used by the last runs (the folder is ignored by Git).

## Mistakes people make

- Running `act` from a subfolder and losing `.actrc`.
- Expecting act to resolve a remote reusable workflow offline without `--local-repository`.
- Expecting identical behavior to GitHub for permissions, secrets and caches.
- Moving the real `v1` tag to try the demo: the script uses a clone for exactly that reason.

## Check yourself

1. What does `--local-repository A@REF=DIR` do? *(Uses the folder when something asks for repository A at that ref.)*
2. Why does the script unpack with `git archive`? *(To get the files of an exact commit without a network.)*
3. Why must the consumer run from the root with `-C`? *(So act reads `.actrc` there.)*
4. Why are two mappings needed per consumer? *(The reusable workflow and the composite action it uses are separate references.)*
5. What makes the demo exit 0? *(The marker appears in the tag run and not in the commit run.)*

## Further reading

- act user guide: https://nektosact.com/
- act 0.2.89: https://github.com/nektos/act/tree/v0.2.89#readme
