# Dependabot

## What it is

Dependabot is a GitHub service that opens pull requests to update your dependencies when new versions come out. You configure it with a YAML file. It can watch GitHub Actions versions, Python packages and many other kinds.

<!-- words -->

<details>
<summary><b>Words this note uses, in case they are new to you</b> (click to open)</summary>

- **commit**: A saved snapshot of a project's files in Git, with a message and an author. Every commit has a unique 40-character name (its SHA).
- **pull request**: A proposal on GitHub to merge the commits of one branch into another. People review it and automation checks it before it is merged.
- **repository**: A project's folder of files together with its complete history of changes. On GitHub, a repository is a page with those files, issues and pull requests.
- **CI**: Continuous integration: running checks (build, tests, linters) automatically every time code changes.
- **YAML**: A plain-text format for structured data that uses indentation instead of braces. GitHub workflows are YAML files.
- **dependency**: A package that your project needs in order to work.
- **folder**: A container for files and other folders on disk (also called a directory).
- **version**: A number such as `1.2.3` that names one release of software (major.minor.patch).

</details>

<!-- /words -->

## Why this repository uses it

Every action is pinned to a 40-character SHA, and the lesson's step 6 expects "the bot opens a pull request for the next platform release". Dependabot proposes the update as a pull request, so keeping current is a review instead of a chore. Each consumer has its own file for exactly that: when the platform ships `v2.1.0`, each consumer's bot proposes the new SHA.

## Where it appears

| Path | What it does with Dependabot |
| --- | --- |
| `.github/dependabot.yml` | The platform: actions at the root, pip at the root, actions inside the composite action's folder. |
| `consumers/svc-orders/.github/dependabot.yml`, `svc-billing`, `svc-search` | Each consumer: `github-actions`, weekly. |

## How it works underneath

On the schedule, Dependabot reads your files, looks up newer versions, and for a pinned action reads the `# v7.0.1` comment to learn which version the SHA stands for. It opens a pull request that changes both the SHA and the comment. Pull requests from Dependabot run your normal CI.

## Walkthrough of this repository's use

```yaml
version: 2
updates:
  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
    groups:
      actions:
        patterns: ["*"]
    ignore:
      - dependency-name: "sumitsr/platform-ci*"
  - package-ecosystem: pip
    directory: /
    schedule:
      interval: weekly
  - package-ecosystem: github-actions
    directory: /.github/actions/setup-toolchain
    schedule:
      interval: weekly
```

`package-ecosystem` is the kind of dependency; `directory` where to look (for `github-actions`, `/` means `.github/workflows` at the root). `groups` bundles every action update into one pull request. The `ignore` entry tells the bot to leave the platform's own references alone: the composite action is pinned *by hand* to the commit of its last change (checked by `python -m pipeline.pins --internal`), so a bot proposing a different commit would only create a failing check. The third entry watches the actions used *inside* the composite action.

A consumer's file is the short form:

```yaml
version: 2
updates:
  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
```

It reads the `# v2.0.0` comment next to the pinned SHA of `build-test.yml`, and when a newer release exists it opens a pull request that changes both the SHA and the comment, like the lesson's "Bump sumitsr/platform-ci/.github/workflows/build-test.yml from 2.0.0 to 2.1.0".

## Try it yourself

1. `.venv/bin/python -c "import yaml; print([u['directory'] for u in yaml.safe_load(open('.github/dependabot.yml'))['updates']])"` prints `['/', '/', '/.github/actions/setup-toolchain']`.
2. `cat consumers/svc-search/.github/dependabot.yml` shows the short form.
3. Dependabot does not run locally; its first pull request appears after the first scheduled run on GitHub.

## Mistakes people make

- Pinning to SHAs without the version comment, so the bot cannot tell what to bump to.
- Letting the bot open one pull request per dependency and drowning in them; `groups` helps.
- Editing the lock files by hand next to the bot.

## Check yourself

1. What does `package-ecosystem` choose? *(The kind of dependency to watch.)*
2. How does it know the version of a pinned action? *(From the `# vX.Y.Z` comment next to the SHA.)*
3. What does `groups` do? *(Combines several updates into one pull request.)*
4. Does it run on your laptop? *(No, it is a GitHub service.)*
5. Why does this repository need it? *(Pins go stale; the bot proposes the new SHAs.)*

## Further reading

- Dependabot options reference: https://docs.github.com/en/code-security/dependabot/working-with-dependabot/dependabot-options-reference
