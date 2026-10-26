# Changelog

All notable changes to the platform are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/). Each release says what **every consumer must change**, as an instruction.

Tags: `vX.Y.Z` is exact and never moves. `vX` is the moving major tag; it follows the latest `vX.Y.Z` of that major. Consumers should still pin to the commit (see the README).

## [1.0.0] - 2026-10-27

First release of the shared build-test workflow and the setup-toolchain action.

### Added

- `.github/actions/setup-toolchain`: installs a pinned Python and restores the pip cache. Inputs `python-version` and `requirements-file`; outputs `cache-hit` and `python-version`.
- `.github/workflows/build-test.yml`: reusable workflow. Inputs `python-version` (required), `test-command`, `working-directory`, `report-secret-names`; optional secret `PACKAGE_TOKEN`; output `cache-hit`.

### Required changes for consumers

None. Call it with `uses: sumitsr/platform-ci/.github/workflows/build-test.yml@v1` and `with: { python-version: "3.12" }`.
