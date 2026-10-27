# 2. Pin the platform's own composite action to the commit of its last change

Status: accepted, 2026-10-27

## Context

`build-test.yml` calls `sumitsr/platform-ci/.github/actions/setup-toolchain@<ref>`. A tag is the obvious ref, and it is
the wrong one: the lesson's whole point is that a tag moves, and the action and the workflow live in the same repository,
so a moving tag in the middle of the shared code would let the action change under a consumer that pinned the workflow by
SHA. A workflow also cannot name its own commit (a commit hash cannot appear inside the commit it hashes).

## Decision

The workflow pins the action to a full commit SHA: **the last commit that changed the action's folder**. The action is
committed first; the workflow is committed afterwards, naming that commit. Every release then carries an action that no
tag can replace. `python -m pipeline.pins --internal sumitsr/platform-ci` (part of `make lint` and CI) fails when the pin is not the last commit that changed
the folder, ignoring README edits, so an edit to the action cannot ship while the workflow still runs the old one.
Dependabot is told to leave this one dependency alone.

## Alternatives considered

- **A moving major tag for the action** (`@v1`). Convenient, and exactly the risk the project demonstrates.
- **A second repository for the action.** Clean, but two repositories to release and keep in step for eight lines of shell.
- **Checking out the platform repository inside the workflow.** Needs the workflow's own commit, which GitHub does not expose
  to the workflow as a context value.

## Consequences

- Releasing a change to the action is two commits: the action, then the workflow that pins it. `make lint` tells you when
  you forgot the second one.
- The pinned commit appears in `build-test.yml` under the name `sumitsr/platform-ci`; the repository must be published
  under that name for the pin to resolve.
