# JSON

## What it is

JSON is a text format for data: objects (`{"name": value}`), lists (`[1, 2]`), text in double quotes, numbers, `true`, `false` and `null`. It is how programs exchange data, including GitHub's web API. It has no comments.

## Why this repository uses it

The organization-wide pin policy is sent to GitHub's API as a JSON document (a **ruleset**). The branch and settings scripts send small JSON bodies. The `jq` step reads JSON (see `jq.md`).

## Where it appears

| Path | What it does with JSON |
| --- | --- |
| `docs/org-ruleset.json` | The body of the organization ruleset that requires the pin-check workflow. |
| `scripts/org-policy.sh` | Sends it with `gh api -X POST orgs/$org/rulesets --input docs/org-ruleset.json`. |
| `.github/workflows/build-test.yml` | `toJSON(secrets)` produces JSON that `jq` reads. |

## How it works underneath

A program that receives JSON text **parses** it into its own objects. A request body in JSON must be valid: keys in double quotes, no trailing commas, no comments. Because of that, a JSON file can be checked by any JSON parser.

## Walkthrough of this repository's use

```json
{
  "name": "require-pin-check",
  "target": "branch",
  "enforcement": "active",
  "conditions": {
    "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] },
    "repository_name": { "include": ["~ALL"], "exclude": [] }
  },
  "rules": [
    {
      "type": "workflows",
      "parameters": {
        "do_not_enforce_on_create": false,
        "workflows": [
          { "repository_id": 0, "path": ".github/workflows/pin-check.yml", "ref": "refs/heads/main" }
        ]
      }
    }
  ]
}
```

A **ruleset** is a GitHub policy. `target: "branch"` applies it to branches, `enforcement: "active"` makes it binding. `conditions` say where it applies: `~DEFAULT_BRANCH` is GitHub's special word for each repository's default branch, and `~ALL` means every repository in the organization. The one rule has `type: "workflows"`, a *required workflow*: the named workflow file must pass before a pull request can merge. `repository_id: 0` is a placeholder for the numeric id of the repository that holds `pin-check.yml`, which you fill in after publishing (the id exists only on GitHub). The script was written to the API's documented shape and has not been run, because an organization is needed.

## Try it yourself

1. `.venv/bin/python -m json.tool docs/org-ruleset.json | head -5` pretty-prints it, which also proves it is valid JSON.
2. `jq '.rules[0].type' docs/org-ruleset.json` prints `"workflows"`.
3. `DRY_RUN=1 scripts/org-policy.sh example-org` prints the three `gh api` commands, the last using this file.

## Mistakes people make

- Trailing commas and comments, which JSON forbids.
- Single quotes instead of double quotes.
- Leaving the placeholder `repository_id: 0` and expecting it to work.

## Check yourself

1. Can JSON have comments? *(No.)*
2. What does `~DEFAULT_BRANCH` mean? *(Each repository's default branch.)*
3. What is a required workflow? *(A workflow that must pass before merging.)*
4. Why is `repository_id` 0 here? *(The real id exists only after publishing.)*
5. How can you check the file is valid? *(Parse it with `python -m json.tool` or `jq`.)*

## Further reading

- JSON specification: https://www.json.org/
- Rulesets API: https://docs.github.com/en/rest/orgs/rules
