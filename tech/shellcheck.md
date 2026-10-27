# ShellCheck

## What it is

ShellCheck is a static analyzer for shell scripts. It reads a script without running it and warns about common mistakes: unquoted variables, commands that may not do what they look like, features that your shell does not have. Each warning has a code such as `SC2086`. This repository uses version 0.11.0.

<!-- words -->

<details>
<summary><b>Words this note uses, in case they are new to you</b> (click to open)</summary>

- **shell**: The program inside a terminal that reads what you type and starts other programs. Bash is a shell.
- **repository**: A project's folder of files together with its complete history of changes. On GitHub, a repository is a page with those files, issues and pull requests.
- **variable**: A name for a place that holds a value which can be used later in the code.
- **list**: An ordered collection of values written one after another.
- **version**: A number such as `1.2.3` that names one release of software (major.minor.patch).
- **compiler**: A program that translates code written in one language into another form, and checks it on the way.

</details>

<!-- /words -->

## Why this repository uses it

Bash is easy to get subtly wrong (see `bash.md`), and these scripts handle untrusted-looking input such as refs and organization names. ShellCheck turns most of the mistakes into build failures.

## Where it appears

| Path | What it does with ShellCheck |
| --- | --- |
| `Makefile` | `lint` runs `shellcheck scripts/*.sh .github/actions/*/*.sh`. |
| `scripts/*.sh`, `.github/actions/setup-toolchain/validate-inputs.sh` | The files it checks. |
| `.github/workflows/*.yml` | Checked through actionlint; `pin-check.yml` has one deliberate `# shellcheck disable=SC2086`. |

## How it works underneath

ShellCheck parses the script into the same kind of tree that Bash builds, then applies a long list of rules to it. It reads the shebang line (`#!/usr/bin/env bash`) to know which shell to assume. `-e`-style behaviors are not run; it only reasons about the text.

## Walkthrough of this repository's use

```bash
shellcheck scripts/*.sh .github/actions/*/*.sh
```

The globs expand to every script. A clean run prints nothing and exits 0.

The one deliberate exception is in `pin-check.yml`:

```bash
# shellcheck disable=SC2086

bad=$(grep -nE '^[[:space:]-]*uses:' $files ...
```

`SC2086` warns that an unquoted `$files` will be split on whitespace and expanded as a pattern. Here that is the point: `$files` holds a list of file names that must become separate arguments. The comment sits directly above the line and silences exactly that code for that line.

Other rules the scripts satisfy: variables are quoted (`"$work"`), `[[ ... ]]` is used for tests, `read -r` is used so backslashes are kept, and `$(...)` is used instead of backticks.

## Try it yourself

1. `shellcheck --version` shows `version: 0.11.0`.
2. `shellcheck scripts/*.sh .github/actions/*/*.sh; echo "exit $?"` prints `exit 0`.
3. `printf '#!/bin/bash\necho $1\n' > /tmp/s.sh && shellcheck /tmp/s.sh` reports `SC2086` with a suggested fix.
4. `shellcheck -f gcc scripts/run_consumer.sh` prints findings in compiler style (none here).

## Mistakes people make

- Disabling a rule globally to make noise stop.
- Writing `#!/bin/sh` but using Bash-only features; ShellCheck then warns.
- Running it on only some scripts.

## Check yourself

1. What does it analyze? *(The text of shell scripts, without running them.)*
2. What does `SC2086` warn about? *(An unquoted variable that can be split into several words.)*
3. How do you silence one finding? *(A `# shellcheck disable=SCxxxx` comment above the line.)*
4. How does it know which shell to assume? *(From the shebang.)*
5. How is it used on workflows? *(Through actionlint.)*

## Further reading

- ShellCheck wiki (0.11): https://www.shellcheck.net/wiki/
