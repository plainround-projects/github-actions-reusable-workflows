# Git: commits, tags and `.gitignore`

## What it is

Git is a version-control system. It records snapshots of a folder (**commits**) so you can see history, undo mistakes and share work. A **repository** is the folder plus its history in a hidden `.git` folder. A **commit** has a 40-character fingerprint, its **SHA**, computed from its contents, its message and its parent commit. A **tag** is a name attached to a commit. A **branch** is a name that moves forward as you commit. `.gitignore` lists files Git must not track.

## Why this repository uses it

This repository is about *what a name points to*. A GitHub workflow call such as `@v1` is a Git ref, and the lesson's step 5 shows that moving a tag changes what consumers run, while a SHA never changes. So Git is not just storage here: the tools in `pipeline/` and `scripts/` call Git to resolve refs, unpack commits and find the last commit that touched a folder. The history is also the lesson's story, written as real commits.

## Where it appears

| Path | What it does with Git |
| --- | --- |
| `pipeline/platform_refs.py` | `git rev-parse` to turn a ref into a commit; `git show` to read a file at a commit. |
| `pipeline/pins.py` | `git log -1 -- DIR` to find the last commit that changed the action's folder. |
| `scripts/run_consumer.sh` | `git archive COMMIT \| tar -x` to unpack a commit into a folder. |
| `scripts/demo_moved_tag.sh` | `git clone`, `git checkout --detach`, `git commit`, `git tag -f` on a throwaway copy. |
| `tests/test_pins.py`, `tests/test_platform_refs.py` | Build tiny temporary repositories to test the tools. |
| `.gitignore` | Keeps `.venv`, caches, `build/` and `.tools/` out. |
| tags `v1.0.0`, `v1`, `v2.0.0`, `v2` | The releases. |

## How it works underneath

Git stores four kinds of objects, each named by its SHA: **blobs** (file contents), **trees** (folders), **commits** and **tag objects**. A commit points to one tree (the whole snapshot) and its parent commit. A **lightweight tag** is only a name that points at a commit. An **annotated tag** (`git tag -a`) is its own object with a message, a tagger and a date, and points at a commit; the commit is what `ref^{commit}` reaches. A tag name is a file that holds a SHA, so it can be changed with `git tag -f`; a SHA cannot be changed, because changing the contents changes the SHA.

## Walkthrough of this repository's use

### Resolve a name to a commit

```python
["git", "-C", str(repo), "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"]
```

`-C DIR` runs Git as if started in that folder. `rev-parse` prints the SHA a name stands for. `--verify` insists on exactly one valid object, `--quiet` suppresses the error message and only sets the exit code. `v1^{commit}` means "peel the tag until you reach a commit": it works for lightweight and annotated tags. A full SHA resolves to itself; a tag resolves to wherever it points *now*, which is the whole risk this repository demonstrates.

### Find the last commit that changed a folder

```python
_git(root, "log", "-1", "--format=%H", "--", directory, f":(exclude){directory}/README.md")
```

`log -1` shows one commit, the latest. `--format=%H` prints only its SHA. The words after `--` are **pathspecs**: only commits touching those paths count. `:(exclude)PATH` is a pathspec that removes a path, so editing the action's README does not make the pin stale. `pipeline/pins.py --internal` compares this SHA with the one written in `build-test.yml`.

### Unpack a commit

```bash
git -C "$repo" archive "$commit" | tar -x -C "$dir"
```

`git archive COMMIT` writes the files of that commit as a tar stream (no `.git` folder). The pipe sends it to `tar -x`, which extracts into `-C DIR`. `scripts/run_consumer.sh` does this so `act` can use "the platform at that exact commit" without any network.

### The moved-tag demo

```bash
git clone -q --no-hardlinks "$root" "$work/platform-ci"
original="$(git -C "$work/platform-ci" rev-parse 'v1.0.0^{commit}')"
git checkout -q --detach "$original"
git -c user.name=attacker -c user.email=attacker@example.invalid commit -q -am "ci: an extra step"
git -c user.name=attacker -c user.email=attacker@example.invalid tag -f -a v1 -m "moved" >/dev/null
```

`clone --no-hardlinks` makes an independent copy, so nothing done to it can touch this repository's objects or tags. `checkout --detach SHA` moves to a commit without a branch. `-c user.name=... -c user.email=...` sets the author for one command, since a throwaway clone may have no identity. `commit -am` stages tracked changes and commits. `tag -f -a v1` **forces** the existing tag `v1` onto the new commit. After that, `v1` and the original `v1.0.0` point at different commits; a consumer calling `@v1` runs the new one, a consumer calling the SHA of `v1.0.0` runs the old one.

### Tests with throwaway repositories

```python
env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
done = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=True, env=env)
```

Each test makes a temporary folder, runs `git init`, makes commits with fixed identities from environment variables, and then checks the tools against it, for example that a moved tag resolves to a different commit but a SHA does not.

### The release history

```text
a416c63 chore: scaffold ...
d70ac3d feat(actions): add the setup-toolchain composite action ...   <- the pinned action commit
661d538 feat(workflows): add the reusable build-test workflow (v1 API) ...   <- tag v1.0.0, v1
...
fcd73fa feat(workflows)!: rename the build-test input python-version to python (v2.0.0)   <- tag v2.0.0, v2
```

The action is committed before the workflow that pins it, because a commit cannot contain its own hash. Commit messages follow the "semantic" style: `feat`, `fix`, `chore`, `docs`, `ci`, with `!` marking a breaking change.

## Try it yourself

1. `git tag -l` prints `v1`, `v1.0.0`, `v2`, `v2.0.0`.
2. `git rev-parse 'v1^{commit}' 'v1.0.0^{commit}'` prints the same SHA twice, `661d5382...`.
3. `git log -1 --format=%H -- .github/actions/setup-toolchain ':(exclude).github/actions/setup-toolchain/README.md'` prints `d70ac3daf2d7ada75bcbd1bc34d83a6f29ce9abd`, the SHA written in `build-test.yml`.
4. `git archive v1.0.0 | tar -t | head` lists the files of release 1.0.0.
5. `git cat-file -t v1` prints `tag` (an annotated tag object); `git cat-file -t v1^{commit}` prints `commit`.

## Mistakes people make

- Thinking a tag is permanent. Anyone with push rights can move it, and `git push -f` publishes the move.
- Pinning a SHA from a fork.
- Rewriting history after SHAs were pinned: every pin to a rewritten commit breaks.
- Committing `.venv`, caches or secrets.
- Running `git tag -f` or `git push --force` in your real repository when you meant a throwaway clone.

## Check yourself

1. What is the difference between a tag and a SHA? *(A tag is a movable name; a SHA is the fingerprint of one exact commit and cannot move.)*
2. What does `v1^{commit}` do? *(Follows a tag to the commit it names.)*
3. Why `clone --no-hardlinks` in the demo? *(So the copy shares nothing with the real repository.)*
4. What does `:(exclude)PATH` do in a pathspec? *(Removes that path from the match.)*
5. Why is the action committed before the workflow? *(A commit cannot contain its own hash, so the workflow names an earlier commit.)*

## Further reading

- Pro Git book: https://git-scm.com/book/en/v2
- `git rev-parse`: https://git-scm.com/docs/git-rev-parse
- `git archive`: https://git-scm.com/docs/git-archive
- Pathspecs: https://git-scm.com/docs/gitglossary#def_pathspec
