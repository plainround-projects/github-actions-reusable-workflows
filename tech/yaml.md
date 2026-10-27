# YAML

## What it is

YAML is a text format for structured data: lists, named values, and nests of both. People read and write it easily and programs parse it. It is a **file format**, not a language that runs. Every workflow, action definition and Dependabot setting in this repository is YAML (`.yml`).

## Why this repository uses it

GitHub Actions accepts only YAML for workflows and actions, and Dependabot only reads YAML. This repository also has Python code that reads those files as data (the pin checker, the ref resolver, the secrets report) and tests that assert facts about them.

## Where it appears

| Path | What it does with YAML |
| --- | --- |
| `.github/workflows/*.yml` | The reusable workflow, the platform's CI, the action's test workflow and the pin check. |
| `.github/actions/setup-toolchain/action.yml` | The composite action's definition. |
| `consumers/*/.github/workflows/ci.yml`, `demo/*.yml` | The callers. |
| `.github/dependabot.yml`, `consumers/*/.github/dependabot.yml` | Update-bot settings. |
| `pipeline/*.py`, `tests/*.py` | Python code that loads these files (see `pyyaml.md`). |

## How it works underneath

A **parser** reads the text and builds a **mapping** (names with values), a **sequence** (a list) or a **scalar** (one value). Indentation shows nesting, with spaces and never tabs. `key: value` is a mapping entry, `- item` a list entry, `[a, b]` and `{x: 1}` the one-line forms, `#` starts a comment, and `|` after a key begins a **block scalar**: the indented lines below are one text with line breaks kept. Without quotes the parser guesses types: `3.10` becomes the number 3.1; in older YAML rules `on` and `yes` become true.

## Walkthrough of this repository's use

```yaml
name: ci
on: [push, pull_request]
permissions:
  contents: read
jobs:
  ci:
    uses: sumitsr/platform-ci/.github/workflows/build-test.yml@fcd73fa6... # v2.0.0
    with: { python: "3.12" }
```

A whole consumer workflow. `on: [push, pull_request]` is a list in the one-line form. `with: { python: "3.12" }` is a mapping in the one-line form (a **flow mapping**). `"3.12"` is quoted so it is text; unquoted, `3.12` would be a number, and `3.10` would lose its trailing zero. After `#` is a comment: the version, for people and for the update bot.

```yaml
run: |
  printf '%s' "$SECRETS_CONTEXT" | jq -r 'keys[] | "can read secret=" + .'
```

The `|` keeps the script as written. This is not just style: the script contains `: ` inside the `jq` program text. In a one-line plain value, a colon followed by a space makes YAML read the start of a nested mapping and fail with "mapping values are not allowed in this context". Inside a block scalar there is no such rule.

```yaml
secrets:
  PACKAGE_TOKEN: ${{ secrets.PACKAGE_TOKEN }}
```

`${{ ... }}` is GitHub's expression syntax. To the YAML parser it is plain text; GitHub fills it in later.

```yaml
secrets: inherit
```

A plain word as the value: here it means "pass every secret".

### YAML in Python

```python
WORKFLOW = yaml.safe_load(TEXT)
CALL = WORKFLOW[True]["workflow_call"]
```

PyYAML follows YAML 1.1, where the bare word `on` is the boolean true. So the workflow's `on:` key arrives as the Python value `True`, and the tests index it with `[True]`.

## Try it yourself

1. `.venv/bin/python -c "import yaml; print(list(yaml.safe_load(open('.github/workflows/build-test.yml'))))"` prints `['name', True, 'permissions', 'jobs']`.
2. `.venv/bin/python -c "import yaml; print(yaml.safe_load('v: 3.10'), yaml.safe_load('v: \"3.10\"'))"` prints `{'v': 3.1} {'v': '3.10'}`.
3. `.venv/bin/python -c "import yaml; print(yaml.safe_load(open('consumers/svc-orders/.github/workflows/ci.yml'))['jobs']['ci']['with'])"` prints `{'python': '3.12'}`.
4. `actionlint` finds syntax errors with line numbers.

## Mistakes people make

- Unquoted version numbers.
- Tabs for indentation.
- A colon and a space inside an unquoted value.
- Treating `on`, `yes`, `no` as text.
- Changing indentation by one space and moving a key under a different parent.

## Check yourself

1. Why `"3.12"` in quotes? *(Unquoted it is a number, and `3.10` would become 3.1.)*
2. What is `with: { python: "3.12" }`? *(A mapping written on one line.)*
3. Why does `on:` appear as `True` in Python? *(PyYAML reads `on` as a boolean.)*
4. Why is the `jq` script in a `|` block? *(It contains `: `, which a plain one-line value cannot.)*
5. Is `${{ ... }}` YAML? *(No, it is GitHub's expression syntax inside text.)*

## Further reading

- YAML 1.2.2: https://yaml.org/spec/1.2.2/
- PyYAML 6.0.2: https://pyyaml.org/wiki/PyYAMLDocumentation
