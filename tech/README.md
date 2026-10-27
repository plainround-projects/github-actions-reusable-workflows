# Technology notes for github-actions-reusable-workflows

This folder teaches every technology the repository uses, from zero, through the repository's own files. Each note says what the technology is, why this repository uses it, where it appears, how it works underneath, and then walks through the repository's own lines, flag by flag. You need no earlier knowledge.

## The files and the order to read them

Read from the top: the idea of the project first, then the file formats and the language, then the build and test tools, then the code checkers, then the scripts and the pieces that run it locally, then the tools around the code.

| # | Note | Role in this repository |
| ---: | --- | --- |
| 1 | [GitHub Actions: reusable workflows and composite actions](github-actions.md) | the service and the two sharing mechanisms: `workflow_call`, inputs, `secrets: inherit`, composite actions, pinning by SHA |
| 2 | [YAML](yaml.md) | the file format of every workflow, action and config, with its traps |
| 3 | [Python](python.md) | the language of the checker library, the tests and the three services |
| 4 | [TOML](toml.md) | the format of `pyproject.toml`, which configures every Python tool |
| 5 | [pip, virtual environments and lock files](pip.md) | installs packages; the hashed lock files of the platform and each consumer |
| 6 | [uv](uv.md) | makes the universal lock files |
| 7 | [pytest, pytest-cov and coverage](pytest.md) | runs the platform's tests and each consumer's tests |
| 8 | [PyYAML](pyyaml.md) | lets Python tests read the workflows and the composite action |
| 9 | [Ruff](ruff.md) | lints and formats the Python |
| 10 | [mypy](mypy.md) | checks the type hints |
| 11 | [pip-audit](pip-audit.md) | checks the locked packages for known vulnerabilities |
| 12 | [JSON](json.md) | the format of the organization ruleset and of `gh` output |
| 13 | [jq](jq.md) | reads and reshapes JSON on the command line |
| 14 | [Bash](bash.md) | the scripts: resolve refs, run the consumers, show a moved tag, apply the org policy |
| 15 | [Make](make.md) | the `make test`, `make lint`, `make run` commands |
| 16 | [actionlint](actionlint.md) | checks workflow files before GitHub sees them |
| 17 | [ShellCheck](shellcheck.md) | checks the shell scripts |
| 18 | [Docker](docker.md) | the Dockerfile for the image `act` uses |
| 19 | [act](act.md) | runs the consumers against the platform on your machine |
| 20 | [Dependabot](dependabot.md) | proposes the new platform SHA to every consumer |
| 21 | [GitHub CLI](gh-cli.md) | reads releases and applies the organization ruleset |
| 22 | [Git and .gitignore](git.md) | tags, SHAs, `git archive`, and why a moved tag matters |
| 23 | [EditorConfig](editorconfig.md) | the same indentation and line endings in every editor |
| 24 | [Markdown and Mermaid](markdown.md) | the documents, the changelog the tests read, the diagram |

## If you have ten minutes

Read these three, in this order:

1. [GitHub Actions](github-actions.md): the whole lesson, a workflow that other repositories call and the pin that decides what they get.
2. [Git and .gitignore](git.md): why a tag can move and a commit SHA cannot, which is the reason for every pin.
3. [act](act.md): how to watch a consumer call the platform on your machine without pushing.
