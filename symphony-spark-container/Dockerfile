FROM node:26.7.0-bookworm-slim

ARG APP_GID=1003
ARG APP_UID=1003
ARG CODEX_VERSION=0.155.1
ARG SYMPHONY_VERSION=v0.0.3
ARG TARGETARCH

ENV NPM_CONFIG_FUND=false \
    NPM_CONFIG_UPDATE_NOTIFIER=false

RUN apt-get update \
  && apt-get install --yes --no-install-recommends \
    build-essential \
    ca-certificates \
    curl \
    git \
    jq \
    openssh-client \
    procps \
    python3 \
    ripgrep \
    tini \
  && npm install --global "@openai/codex@${CODEX_VERSION}" pnpm@11.24.0 \
  && case "${TARGETARCH}" in \
       amd64) symphony_arch="x86_64" ;; \
       arm64) symphony_arch="arm64" ;; \
       *) echo "Unsupported target architecture: ${TARGETARCH}" >&2; exit 1 ;; \
     esac \
  && symphony_asset="symphony-${SYMPHONY_VERSION}-linux_${symphony_arch}" \
  && curl --fail --location --silent --show-error \
    --output "/tmp/${symphony_asset}" \
    "https://github.com/openai/symphony/releases/download/${SYMPHONY_VERSION}/${symphony_asset}" \
  && curl --fail --location --silent --show-error \
    --output "/tmp/${symphony_asset}.sha256" \
    "https://github.com/openai/symphony/releases/download/${SYMPHONY_VERSION}/${symphony_asset}.sha256" \
  && cd /tmp \
  && sha256sum --check "${symphony_asset}.sha256" \
  && install --mode 0755 "/tmp/${symphony_asset}" /usr/local/bin/symphony \
  && groupadd --gid "${APP_GID}" symphony \
  && useradd --uid "${APP_UID}" --gid "${APP_GID}" --create-home --shell /bin/bash symphony \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/* /tmp/symphony-*

COPY github-known-hosts /etc/ssh/ssh_known_hosts
COPY config /opt/symphony/config
COPY scripts /usr/local/lib/symphony

RUN chmod 0644 /etc/ssh/ssh_known_hosts /opt/symphony/config/config.toml /opt/symphony/config/agents/*.toml \
  && chmod 0755 /usr/local/lib/symphony/*.sh

ENV CODEX_HOME=/var/lib/symphony/codex \
    HOME=/var/lib/symphony/home \
    NPM_CONFIG_CACHE=/var/lib/symphony/cache/npm \
    npm_config_cache=/var/lib/symphony/cache/npm \
    PNPM_HOME=/var/lib/symphony/cache/pnpm \
    SYMPHONY_LOGS_ROOT=/var/lib/symphony/logs \
    SYMPHONY_WORKSPACE_ROOT=/var/lib/symphony/workspaces \
    XDG_CACHE_HOME=/var/lib/symphony/cache

USER symphony:symphony
WORKDIR /opt/symphony

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/lib/symphony/symphony-entrypoint.sh"]
