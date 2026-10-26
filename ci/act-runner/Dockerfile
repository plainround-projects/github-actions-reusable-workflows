# The image `act` uses as `ubuntu-latest`: Ubuntu 24.04 (so actions/setup-python finds its prebuilt interpreters),
# Node for JavaScript actions, git, curl and a compiler. It is a stand-in for a GitHub-hosted runner, not a copy.
FROM ubuntu:24.04

ARG NODE_VERSION=22.12.0
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl git jq make sudo unzip xz-utils build-essential shellcheck \
 && rm -rf /var/lib/apt/lists/*

RUN arch="$(dpkg --print-architecture)"; \
    case "$arch" in arm64) node_arch=arm64 ;; amd64) node_arch=x64 ;; *) echo "unsupported $arch" >&2; exit 1 ;; esac; \
    curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-${node_arch}.tar.xz" \
      | tar -xJ -C /usr/local --strip-components=1 \
 && mkdir -p /opt/hostedtoolcache
