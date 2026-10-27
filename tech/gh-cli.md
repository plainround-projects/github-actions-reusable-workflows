# GitHub CLI (`gh`)

## What it is

`gh` is GitHub's official command-line program. After you sign in once (`gh auth login`), it sends requests to GitHub for you. `gh api PATH` sends any request to GitHub's REST API.

## Why this repository uses it

The lesson's last step asks how you would enforce SHA pinning across an organization. The answer is organization settings, an allowed-actions list and a ruleset. Those are changed through GitHub's API, so `scripts/org-policy.sh` shows them as `gh api` calls. It could not be run here (a personal account has no organization), so it has a dry-run mode and the README says so.

## Where it appears

| Path | What it does with `gh` |
| --- | --- |
| `scripts/org-policy.sh` | Three `gh api` calls: require pinned SHAs, set the allowed list, create the ruleset. |
| `docs/org-ruleset.json` | The body of the third call. |
| `README.md` | Names the script and its `DRY_RUN=1` mode. |

## How it works underneath

`gh` keeps a token from `gh auth login` and turns each command into an HTTPS request to `api.github.com`. `-X METHOD` sets the HTTP method (GET reads, PUT replaces, POST creates). `-f key=value` sends a text field; `-F key=value` sends a typed field (`true` becomes a JSON boolean). `--input FILE` sends a file as the body. A key ending in `[]`, like `patterns_allowed[]`, means "add one item to a list".

## Walkthrough of this repository's use

```bash
gh_api -X PUT "orgs/$org/actions/permissions" -f enabled_repositories=all -f allowed_actions=selected -F sha_pinning_required=true
```

Sets the organization's Actions policy: Actions are enabled in all repositories, only "selected" actions may run (the list comes next), and `sha_pinning_required` makes GitHub refuse a run that uses an action by tag instead of full SHA.

```bash
gh_api -X PUT "orgs/$org/actions/permissions/selected-actions" -F github_owned_allowed=false "${patterns[@]}"
```

The allowed list. The patterns are built from `allowed-actions.txt` (`actions/*` and `sumitsr/platform-ci`), each written as `-f 'patterns_allowed[]=actions/*@*'`, meaning "that repository at any ref". `github_owned_allowed=false` means the GitHub-owned actions are not allowed by default; they are allowed through the explicit `actions/*` pattern instead.

```bash
gh api -X POST "orgs/$org/rulesets" --input "$ruleset"
```

Creates the ruleset from `docs/org-ruleset.json` (see `json.md`): a required workflow, `pin-check.yml`, in every repository.

```bash
if [[ ! "$org" =~ ^[A-Za-z0-9_.-]+$ ]]; then
  echo "org-policy: '$org' is not an organization name" >&2
  exit 2
fi
```

The argument is checked before it is placed in a URL path. `DRY_RUN=1` prints each call instead of sending it:

```text
gh api -X PUT orgs/example-org/actions/permissions -f enabled_repositories=all -f allowed_actions=selected -F sha_pinning_required=true
```

## Try it yourself

1. `gh --version` prints the version.
2. `DRY_RUN=1 scripts/org-policy.sh example-org` prints three numbered steps and the three `gh api` lines; nothing is sent.
3. `scripts/org-policy.sh 'bad name'; echo "exit $?"` prints `org-policy: 'bad name' is not an organization name` and `exit 2`.
4. `gh api --help` explains `-f`, `-F`, `--input`.

## Mistakes people make

- Running the real call against the wrong organization. Use the dry run first.
- Forgetting that `-f` sends text and `-F` sends booleans and numbers as such.
- Believing the script was tested: it follows the API documentation, but needs an organization to run.

## Check yourself

1. What does `-X PUT` mean? *(An HTTP PUT request, which replaces a resource's settings.)*
2. `-f` versus `-F`? *(`-f` sends a string; `-F` sends a typed value such as `true`.)*
3. What does `sha_pinning_required` do? *(GitHub refuses runs that use actions by tag instead of full commit SHA.)*
4. What does `DRY_RUN=1` do here? *(Prints the calls without sending them.)*
5. Where does the allowed list come from? *(`allowed-actions.txt`.)*

## Further reading

- GitHub CLI manual: https://cli.github.com/manual/
- Organization Actions permissions API: https://docs.github.com/en/rest/actions/permissions
- Rulesets API: https://docs.github.com/en/rest/orgs/rules
