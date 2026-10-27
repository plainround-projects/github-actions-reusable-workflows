# EditorConfig

## What it is

EditorConfig is a tiny settings file, `.editorconfig`, that most code editors read to apply the same basic text rules (indent size, line endings) to everyone who edits a project. It is a file format with sections named by file patterns.

<!-- words -->

<details>
<summary><b>Words this note uses, in case they are new to you</b> (click to open)</summary>

- **repository**: A project's folder of files together with its complete history of changes. On GitHub, a repository is a page with those files, issues and pull requests.
- **YAML**: A plain-text format for structured data that uses indentation instead of braces. GitHub workflows are YAML files.
- **folder**: A container for files and other folders on disk (also called a directory).
- **UTF-8**: The usual way of storing text as bytes, able to represent every written language.
- **formatter**: A program that rewrites code so its layout (spaces, line breaks) follows one fixed style, without changing what the code does.

</details>

<!-- /words -->

## Why this repository uses it

The template asks for an `.editorconfig` in every repository so a contributor's editor does not change tabs, line endings or trailing spaces behind the formatter's back.

## Where it appears

| Path | What it does with the format |
| --- | --- |
| `.editorconfig` | The rules. |

## How it works underneath

An editor looks for `.editorconfig` in the file's folder and each parent, stops at the first one with `root = true`, and applies every section whose pattern matches the file's name. Later sections override earlier ones.

## Walkthrough of this repository's use

```ini
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
indent_style = space
indent_size = 4

[*.{yml,yaml,json,toml,md}]
indent_size = 2

[Makefile]
indent_style = tab
```

`root = true` stops the search upward. `[*]` is every file: UTF-8 text, Unix line endings (`lf`), a newline at the end of the file, no spaces at line ends, indent with spaces, four per level. `[*.{yml,yaml,json,toml,md}]` overrides the indent to two for those file types (YAML needs spaces and the repository uses two). `[Makefile]` switches to tabs because Make requires a tab at the start of a recipe line (see `make.md`).

## Try it yourself

1. `cat .editorconfig` shows the file.
2. Open `Makefile` in an editor that supports EditorConfig and press Tab: it inserts a tab character.
3. `grep -n "	" Makefile | head -3` shows recipe lines that start with a tab.

## Mistakes people make

- Assuming the formatter reads it; ruff has its own settings in `pyproject.toml`.
- Mixed tabs and spaces in a Makefile.
- Forgetting `root = true` and inheriting rules from a parent folder.

## Check yourself

1. Who reads `.editorconfig`? *(The editor, via a built-in feature or a plugin.)*
2. Why a separate rule for `Makefile`? *(Make needs a tab.)*
3. What does `root = true` do? *(Stops the upward search for more `.editorconfig` files.)*
4. What indent do YAML files get? *(Two spaces.)*
5. What does `end_of_line = lf` mean? *(Unix line endings.)*

## Further reading

- EditorConfig specification: https://spec.editorconfig.org/
