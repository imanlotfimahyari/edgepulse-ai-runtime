FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash-completion \
    build-essential \
    ca-certificates \
    curl \
    git \
    gnupg \
    jq \
    make \
    openssh-client \
    python3 \
    python3-pip \
    python3-venv \
    pipx \
    shellcheck \
    unzip \
    wget \
    yamllint \
    zip \
  && rm -rf /var/lib/apt/lists/*

ENV PIPX_HOME=/opt/pipx
ENV PIPX_BIN_DIR=/usr/local/bin

RUN pipx install pre-commit \
  && pipx install ruff \
  && pipx install black \
  && pipx install checkov \
  && pipx install detect-secrets

USER vscode
