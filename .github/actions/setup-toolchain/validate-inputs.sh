#!/usr/bin/env bash
# Fail early, with a message that names the input, when the action is given a version it cannot install.
# Reads INPUT_PYTHON_VERSION and INPUT_REQUIREMENTS_FILE from the environment (set by action.yml).
set -euo pipefail

version="${INPUT_PYTHON_VERSION:-}"
requirements="${INPUT_REQUIREMENTS_FILE:-}"

if [[ ! "$version" =~ ^3\.[0-9]{1,2}(\.[0-9]{1,2})?$ ]]; then
  echo "::error title=setup-toolchain::python-version must look like 3.12 or 3.12.7, got '${version}'"
  exit 1
fi

if [[ -z "$requirements" ]]; then
  echo "::error title=setup-toolchain::requirements-file must not be empty"
  exit 1
fi

echo "setup-toolchain: python ${version}, cache keyed on ${requirements}"
