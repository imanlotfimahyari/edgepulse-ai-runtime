# Security

EdgePulse treats security as a set of layered controls across source code, dependencies, containers, MQTT transport, and Kubernetes deployment.

The project is a demonstration environment, not a complete security product. Test credentials and local certificates must not be treated as production secrets.

## Security layers

```text
source hygiene
   |
dependency / IaC checks
   |
container hardening + scanning
   |
MQTT authentication + TLS
   |
Kubernetes Secret delivery
   |
release provenance
```

## MQTT client security

The runtime supports:

- MQTT username/password authentication;
- TLS server verification with a CA file;
- optional client certificate and key.

Runtime settings:

```text
MQTT_USERNAME
MQTT_PASSWORD
MQTT_TLS_ENABLED
MQTT_TLS_CA_FILE
MQTT_TLS_CERT_FILE
MQTT_TLS_KEY_FILE
```

Configuration validation rejects inconsistent combinations such as:

- password configured without a username;
- client certificate without a matching key;
- TLS files configured while TLS is disabled.

The runtime does not log MQTT passwords or key contents. Startup logs expose only whether authentication/TLS are enabled.

## Docker Compose security model

The local integration stack uses a dedicated security-init image to generate ephemeral test material into a Docker volume:

```text
MQTT test CA certificate
server certificate and private key
Mosquitto password database
```

The CA private key is removed after signing the server certificate. No generated private key is committed to Git.

The initialization script is idempotent: if complete security material already exists in the volume, it reuses it rather than rotating the live CA underneath the running broker.

The secured E2E path uses separate identities for the runtime and simulator and validates the broker certificate.

The local credentials embedded in Compose configuration are **test-only values** used to exercise authentication behavior. They must never be reused outside the local test environment.

## Kubernetes / Helm security model

The Helm chart references existing Secrets rather than generating production secrets.

Responsibilities are separated as follows:

| Secret material | Consumer |
| --- | --- |
| Mosquitto password file | Broker |
| Broker `tls.crt` / `tls.key` | Broker |
| Runtime MQTT username/password | Runtime |
| Runtime CA certificate | Runtime |
| Optional runtime client cert/key | Runtime |

This makes the chart compatible with platform-native lifecycle tools such as cert-manager and External Secrets.

## Container and pod hardening

The runtime and chart include controls such as:

- non-root runtime user;
- explicit high UID/GID;
- dropped Linux capabilities;
- `allowPrivilegeEscalation: false`;
- read-only root filesystem;
- `RuntimeDefault` seccomp profile;
- disabled automatic ServiceAccount token mounting;
- liveness/readiness probes;
- resource requests/limits;
- NetworkPolicy support.

Readiness is dependency-aware: when MQTT is enabled but disconnected, the runtime remains live but reports not ready.

## Development and CI checks

The repository uses:

- Ruff for Python lint/format consistency;
- pre-commit validation;
- private-key detection;
- YAML/JSON/TOML validation;
- `pip-audit` for Python dependency vulnerabilities;
- Checkov for Helm and Dockerfile scanning;
- runtime tests and Compose E2E validation.

## Checkov policy

Checkov currently runs in soft-fail mode so findings are visible without automatically blocking development.

Explicit Helm exceptions currently documented by the project include:

| Check | Rationale |
| --- | --- |
| `CKV_K8S_21` | Reusable Helm templates should not hardcode `metadata.namespace`; namespace is selected at install time. |
| `CKV_K8S_15` | `IfNotPresent` is valid for local k3d workflows and versioned image tags. |
| `CKV_K8S_43` | Digest pinning can be introduced deliberately as release/deployment promotion becomes more mature. |

These exceptions should be revisited as the deployment model evolves.

## Container supply-chain controls

A dedicated workflow produces:

- SPDX JSON SBOM;
- vulnerability scan results as SARIF.

See `docs/container-security.md`.

Release images are signed using keyless Cosign with GitHub Actions OIDC. See `docs/image-signing.md`.

## Current boundaries

Not yet implemented as full production security subsystems:

- per-device broker ACL lifecycle;
- device registry and identity issuance;
- automatic certificate rotation orchestration inside the project;
- admission-policy enforcement of signed images;
- signed model artifact verification;
- secret-manager integration manifests.

These are appropriate future increments, but the existing design deliberately leaves credential/certificate lifecycle to standard platform tooling rather than embedding a custom PKI in EdgePulse.
