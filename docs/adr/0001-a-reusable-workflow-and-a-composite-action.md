# 1. A reusable workflow for the job, a composite action for the toolchain

Status: accepted, 2026-10-27

## Context

Every service needs the same build and test job, and every job needs the same toolchain setup. GitHub has two ways to
share them and they are not interchangeable.

## Decision

- `build-test.yml` is a **reusable workflow**: a whole job (runner, permissions, timeout, secrets, outputs) called at the
  job level with `uses:`. It owns what must be the same everywhere: `permissions`, the timeout, `persist-credentials: false`,
  `--require-hashes`, how the test command is passed.
- `setup-toolchain` is a **composite action**: a bundle of steps called inside a job. It owns "install this Python and
  restore this cache", so a consumer that needs a different job shape can still reuse the toolchain step.

## Alternatives considered

- **Only a reusable workflow.** Consumers with a different job (a matrix, a service container) would copy the setup steps.
- **Only a composite action.** Each consumer would repeat `permissions`, the runner and the checkout, which is where the
  security decisions live.
- **A JavaScript action.** More maintenance and a build step for logic that is eight lines of shell (the lesson's stretch
  compares them).

## Consequences

- A reusable workflow cannot be called from inside a step, and it cannot see the caller's files unless it checks them out;
  `build-test.yml` checks out the caller's repository itself.
- The workflow calls the action by repository path, not `./`, because a `./` path inside a reusable workflow is resolved in
  the caller's workspace, where the action does not exist (ADR 0002 says what that path pins).
