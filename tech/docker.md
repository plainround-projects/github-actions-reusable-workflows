# Docker and Dockerfiles

## What it is

Docker runs programs in **containers**: isolated processes that see their own file system, their own installed software and their own network view, while sharing the computer's kernel. A container starts from an **image**, a packaged, read-only snapshot of a file system. A **Dockerfile** is the text recipe that builds an image, one instruction per layer. On a Mac, Docker Desktop runs a small Linux virtual machine and all containers live inside it.

<!-- words -->

<details>
<summary><b>Words this note uses, in case they are new to you</b> (click to open)</summary>

- **shell**: The program inside a terminal that reads what you type and starts other programs. Bash is a shell.
- **environment variable**: A named piece of text that is handed to a program by whoever starts it, for example `HOME` or `CI`. Programs read them to learn about the setting they run in.
- **process**: A program while it is running, with its own memory. Starting a program creates a process; when it ends the process is gone.
- **repository**: A project's folder of files together with its complete history of changes. On GitHub, a repository is a page with those files, issues and pull requests.
- **workflow**: A GitHub Actions automation described in a YAML file under `.github/workflows/`. It names the events that start it and the jobs it runs.
- **runner**: The computer, usually a virtual machine, on which GitHub runs a job. It starts clean for every job.
- **HTTP**: The protocol (agreed rules) that web browsers and servers use to talk. A request names a **method** (`GET` to read, `POST` to create, `PATCH` to change part, `PUT` to replace, `DELETE` to remove) and an address; the answer carries a **status code** (200 means success, 404 not found, 500 server problem).
- **module**: A file, or a folder of files, that other code can load and use. In Terraform, a module is a folder of configuration used like a function.
- **variable**: A name for a place that holds a value which can be used later in the code.
- **server**: A program that waits for requests and answers them.
- **client**: A program that sends requests to a server.
- **folder**: A container for files and other folders on disk (also called a directory).
- **compiler**: A program that translates code written in one language into another form, and checks it on the way.

</details>

<!-- /words -->

## Why this repository uses it

Docker is not part of the platform's code. It is there so `act` (see `act.md`) can run a consumer's workflow locally: act starts a container per job, and the container must look enough like a GitHub-hosted Ubuntu runner for `actions/setup-python` and the shared workflow to work. The one Dockerfile in this repository builds that container image.

## Where it appears

| Path | What it does with Docker |
| --- | --- |
| `ci/act-runner/Dockerfile` | The recipe for the runner image `gha-projects-act-runner:ubuntu-24.04`. |
| `Makefile` | `up` builds the image (`docker build -q -t ... ci/act-runner`); `down` removes leftover containers. |
| `scripts/run_consumer.sh` | Runs `act`, which starts containers from this image. |
| `.actrc` | Maps the label `ubuntu-latest` to this image. |

## How it works underneath

`docker build` reads the Dockerfile from top to bottom. Each instruction makes a **layer**: a set of file changes on top of the previous one. Layers are cached by the exact text of the instruction and the layers before it, so an unchanged prefix is not rebuilt. `docker run IMAGE` creates a container from the layers plus a thin writable layer, starts one process in it, and removes the writable layer when you delete the container. A **tag** (`name:version`) is a label for an image. Tags on one machine are shared by everyone using that Docker, so a project-specific name avoids collisions.

## Walkthrough of this repository's use

```dockerfile
FROM ubuntu:24.04
```

Start from the official Ubuntu 24.04 image. Ubuntu matters: `setup-python` downloads prebuilt Pythons keyed by the operating system version, and a Debian image would find none.

```dockerfile
ARG NODE_VERSION=22.12.0
ENV DEBIAN_FRONTEND=noninteractive
```

`ARG` is a build-time variable with a default. `ENV` sets an environment variable in the image; `noninteractive` stops `apt` from asking questions.

```dockerfile
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl git jq make sudo unzip xz-utils build-essential shellcheck \
 && rm -rf /var/lib/apt/lists/*
```

`RUN` executes a command at build time. `apt-get update` downloads the package lists; `install -y` installs without asking; `--no-install-recommends` skips optional extras; the packages are the usual tools a runner has (git, curl, jq, make, a compiler, ShellCheck). `\` continues the line and `&&` runs the next command only if the previous succeeded. Deleting `/var/lib/apt/lists/*` in the same `RUN` keeps the downloaded lists out of the layer, which keeps the image smaller.

```dockerfile
RUN arch="$(dpkg --print-architecture)"; \
    case "$arch" in arm64) node_arch=arm64 ;; amd64) node_arch=x64 ;; *) echo "unsupported $arch" >&2; exit 1 ;; esac; \
    curl --http1.1 --fail --silent --show-error --location --retry 5 --retry-all-errors \
      "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-${node_arch}.tar.xz" -o /tmp/node.tar.xz \
 && tar -xJ -C /usr/local --strip-components=1 -f /tmp/node.tar.xz \
 && rm /tmp/node.tar.xz \
 && mkdir -p /opt/hostedtoolcache
```

Node.js is needed because many actions are JavaScript programs. The shell picks the download name from the machine's CPU type (`dpkg --print-architecture` gives `arm64` or `amd64`). The file is downloaded to disk first, with retries (`--retry 5 --retry-all-errors`, plain HTTP/1.1), and only then unpacked: a connection that drops mid-download cannot leave a half-extracted tree. `tar -xJ` extracts an xz archive; `--strip-components=1` drops the archive's top folder; `-C /usr/local` extracts there. `/opt/hostedtoolcache` is the folder where `setup-python` installs interpreters.

```dockerfile
COPY --from=python:3.12.8-slim-bookworm /usr/lib/*-linux-gnu/libsqlite3.so.0* /usr/lib/
```

`COPY --from=IMAGE` copies files from *another* image. The SQLite library is missing from the base Ubuntu image, and Python's `sqlite3` module (which `coverage` imports) needs it. The `*-linux-gnu` wildcard matches both `aarch64-linux-gnu` and `x86_64-linux-gnu`, so the line works on both CPU types.

### Using the image

```bash
docker build -q -t gha-projects-act-runner:ubuntu-24.04 ci/act-runner
```

`-q` prints only the image id. `-t` names (tags) the result. The last word is the folder holding the Dockerfile.

```bash
docker ps -aq --filter "ancestor=gha-projects-act-runner:ubuntu-24.04" | xargs docker rm -f
```

Lists the ids of all containers started from this image (`-a` includes stopped ones, `-q` ids only) and force-removes them. Filtering by image keeps `make down` from touching other projects' containers.

## Try it yourself

1. `docker --version` prints the client version.
2. `docker build -t gha-projects-act-runner:ubuntu-24.04 ci/act-runner` builds the image (first time: minutes). Run it twice; the second run says `CACHED` for every layer.
3. `docker run --rm gha-projects-act-runner:ubuntu-24.04 sh -c 'node -v; ls /usr/lib/libsqlite3*; cat /etc/os-release | head -2'` prints `v22.12.0`, the two SQLite files, and the Ubuntu 24.04 name.
4. `docker images gha-projects-act-runner` lists the image and its size.
5. `docker history gha-projects-act-runner:ubuntu-24.04` shows one line per layer.

## Mistakes people make

- Installing packages in one `RUN` and cleaning up in another; the first layer still carries the junk.
- Using `latest` tags, so a rebuild changes silently. This Dockerfile pins the base and the Node version.
- Running containers as root in a service; this image is a throwaway tool image, not a server, so it stays simple.
- Sharing one image name across projects and finding someone else's build under it.
- Forgetting that a container's changes vanish when the container is removed.

## Check yourself

1. Image versus container? *(An image is a read-only snapshot; a container is a running instance of one.)*
2. Why does the `RUN apt-get ...` end with `rm -rf /var/lib/apt/lists/*`? *(So the package lists are not stored in the layer.)*
3. Why Ubuntu and not Debian? *(`setup-python` finds its prebuilt Pythons by Ubuntu version.)*
4. What does `COPY --from` copy from? *(Another image.)*
5. Why does `make down` filter by `ancestor`? *(To remove only containers from this project's image.)*

## Further reading

- Dockerfile reference: https://docs.docker.com/reference/dockerfile/
- Docker CLI reference: https://docs.docker.com/reference/cli/docker/
