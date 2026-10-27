# 3. Consumers pin by commit, majors are moving tags, secrets cross by name

Status: accepted, 2026-10-27

## Context

Three things decide how safe it is to share CI: what a consumer's `uses:` names, how a breaking change ships, and which
secrets cross into shared code.

## Decision

- **Releases** are exact tags `vX.Y.Z` that never move, plus a moving major tag `vX` that follows the latest `vX.Y.Z`.
  A breaking change (renaming an input) is a new major: `v2` was released while `v1` stayed where it was, so consumers on
  `v1` kept working, and `CHANGELOG.md` says for every release what each consumer must change.
- **Consumers** call the workflow by the full commit SHA with the version in a comment
  (`@fcd73fa... # v2.0.0`). The comment is for people and for Dependabot, which opens a pull request when a new release
  exists. `python -m pipeline.pins` fails on any `uses:` that is not a SHA.
- **Secrets** cross the boundary by name: `secrets: { PACKAGE_TOKEN: ${{ secrets.PACKAGE_TOKEN }} }`. Without a `secrets:`
  key the shared workflow receives none. `secrets: inherit` is not allowed by policy; `svc-search` keeps it as the example
  of what it hands over, and `make secrets-report` prints the difference.

## Alternatives considered

- **Consumers on `@v2`.** One line shorter, and a compromised or mistaken tag move reaches every consumer on its next run
  (`make demo-moved-tag` shows it). Acceptable only for code you own and review on every move.
- **Branch refs (`@main`).** The weakest: every merge reaches every consumer at once.
- **`secrets: inherit` everywhere.** Shortest, and it gives every shared workflow every secret of every caller, including
  ones it never asked for and ones added later.

## Consequences

- Every release needs one pull request per consumer to take it (the bot opens it).
- To enforce this across an organization: the "require actions to be pinned to a full-length commit SHA" setting (scripted
  in `scripts/org-policy.sh`), a ruleset or required workflow that runs `pipeline.pins`, and the allowed-actions list.
