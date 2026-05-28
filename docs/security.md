# Security Notes

EdgePulse uses several security checks during development and CI:

- `pip-audit` for Python dependency vulnerability checks.
- `checkov` for Helm chart and Dockerfile security scanning.
- pre-commit hooks for formatting, YAML/JSON validation, private key detection, and linting.

## Checkov mode

Checkov currently runs in soft-fail mode.

This means findings are reported, but they do not block development yet. The goal is to progressively reduce findings before making Checkov blocking.

## Current explicit Checkov exceptions

The Helm Checkov scan skips these checks intentionally:

| Check | Reason |
|---|---|
| `CKV_K8S_21` | Reusable Helm charts should not hardcode `metadata.namespace`; namespace is controlled by Helm install flags. |
| `CKV_K8S_15` | `IfNotPresent` is valid for local k3d development and pinned image tags. |
| `CKV_K8S_43` | Image digest pinning should be introduced after GHCR image publishing is in place. |

## Hardening already implemented

The runtime and Helm chart include:

- non-root runtime container user;
- explicit high UID/GID;
- disabled service account token automount;
- dropped Linux capabilities;
- disabled privilege escalation;
- read-only root filesystem;
- RuntimeDefault seccomp profile;
- liveness/readiness probes;
- Dockerfile healthcheck;
- optional ServiceMonitor support;
- NetworkPolicy template.
