# jq

## What it is

jq is a command-line tool that reads JSON text, picks parts out of it, and prints the result. Think of it as a small language for filtering JSON, the way `grep` filters lines of text. It is preinstalled on GitHub's Ubuntu runners.

<!-- words -->

<details>
<summary><b>Words this note uses, in case they are new to you</b> (click to open)</summary>

- **standard output**: The stream where a program writes its normal results (its counterpart, standard error, is for problems).
- **pipe**: The `|` symbol between two commands: the output of the first becomes the input of the second.
- **repository**: A project's folder of files together with its complete history of changes. On GitHub, a repository is a page with those files, issues and pull requests.
- **workflow**: A GitHub Actions automation described in a YAML file under `.github/workflows/`. It names the events that start it and the jobs it runs.
- **runner**: The computer, usually a virtual machine, on which GitHub runs a job. It starts clean for every job.
- **secret**: A value such as a password stored in a repository's settings. Workflows can read it, but GitHub hides it in logs.
- **JSON**: A plain-text format for structured data: objects `{ "name": "value" }`, lists `[1, 2]`, texts in double quotes, numbers, `true`, `false`, `null`. It has no comments.
- **image**: A read-only package that holds everything needed to start a container: a file system plus settings. A running **container** is made from an image.
- **function**: A named piece of code that takes inputs (parameters), does something, and may return a result.
- **list**: An ordered collection of values written one after another.
- **string**: A piece of text in a program.
- **version**: A number such as `1.2.3` that names one release of software (major.minor.patch).

</details>

<!-- /words -->

## Why this repository uses it

The reusable workflow can print which secrets it can read. GitHub gives the workflow a `secrets` object; the step turns it into JSON and uses `jq` to print only the names, never the values.

## Where it appears

| Path | What it does with jq |
| --- | --- |
| `.github/workflows/build-test.yml` | The step "List the secret names this workflow can read". |
| `ci/act-runner/Dockerfile` | Installs `jq` so the same step works under `act`. |

## How it works underneath

jq reads JSON from standard input, applies a **filter** (the quoted program) and writes results to standard output. `.` means "the whole input"; `keys` returns the names of an object's fields; `[]` iterates over a list; `+` joins text; `|` sends one filter's output into the next. `-r` ("raw") prints text without JSON quotes.

## Walkthrough of this repository's use

```yaml
- name: List the secret names this workflow can read
  if: inputs.report-secret-names
  env:
    SECRETS_CONTEXT: ${{ toJSON(secrets) }}
  run: |
    printf '%s' "$SECRETS_CONTEXT" | jq -r 'keys[] | "can read secret=" + .'
```

- `toJSON(secrets)` is GitHub's function that renders the secrets object as JSON text. It goes into an environment variable so it is not pasted into the script.
- `printf '%s' "$SECRETS_CONTEXT"` writes the text exactly, without adding or interpreting anything (unlike `echo` for text with backslashes).
- The pipe sends it to `jq`.
- The filter `keys[] | "can read secret=" + .` reads: take the object's keys, one by one (`keys[]`); for each, build the text `can read secret=` followed by the key itself (`.` is the current item).

GitHub always includes `github_token` in the list, plus any secrets the caller passed. A caller that passes none prints only `can read secret=github_token`. With `secrets: inherit`, every secret the caller has is listed. Values are never printed, because the filter only touches keys.

## Try it yourself

1. `echo '{"A":"x","B":"y"}' | jq -r 'keys[] | "can read secret=" + .'` prints `can read secret=A` and `can read secret=B`.
2. `echo '{"A":"x"}' | jq .` pretty-prints the JSON.
3. `echo '[1,2,3]' | jq 'map(. * 2)'` prints `[2,4,6]`.
4. `jq --version` prints the installed version (the runner image downloads a release build).

## Mistakes people make

- Printing the whole object when only names are wanted; that would put secret values into logs (GitHub masks known secrets, but not reliably in every form).
- Forgetting `-r` and getting quoted strings.
- Building the JSON text with `echo "..."` and string pasting instead of letting a tool encode it.

## Check yourself

1. What does `keys[]` return? *(Each field name of an object, one per line of output.)*
2. What does `-r` do? *(Prints raw text without JSON quotes.)*
3. Why is the context passed through `env`? *(So GitHub does not paste it into the script text.)*
4. Why can this step not leak values? *(The filter reads only the keys.)*
5. Which name is always in the list? *(`github_token`.)*

## Further reading

- jq manual: https://jqlang.org/manual/
