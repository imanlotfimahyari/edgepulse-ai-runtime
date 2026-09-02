# Container Security

EdgePulse has a dedicated container-security workflow that builds the runtime image, generates an SBOM, and scans the image for known vulnerabilities.

Workflow:

```text
.github/workflows/container-security.yaml
```

## Pipeline

```text
runtime/Dockerfile
      |
      v
local CI image
edgepulse-runtime:security-scan
      |
      +--> SPDX JSON SBOM
      |
      +--> vulnerability scan
              |
              v
           SARIF artifact
```

The workflow deliberately scans a locally built image so pull-request validation does not depend on GHCR authentication or a previously published release.

## SBOM

The workflow uses Anchore's SBOM action and emits SPDX JSON:

```text
edgepulse-runtime.spdx.json
```

It is uploaded as the GitHub Actions artifact:

```text
edgepulse-runtime-sbom
```

The SBOM provides a machine-readable inventory of image packages and dependencies that can be retained with CI evidence or consumed by later supply-chain tooling.

## Vulnerability scan

The runtime image is scanned with Anchore's scan action.

Current policy:

```text
severity cutoff: high
fail build: false
output: SARIF
```

This is currently **visibility-first**: high-severity findings are reported but do not block the workflow.

The SARIF result is uploaded as:

```text
edgepulse-runtime-vulnerability-sarif
```

The artifact is retained as workflow evidence instead of being uploaded to GitHub Code Scanning, which keeps the workflow usable in repositories or plans where Code Scanning upload is unavailable.

## Related security checks

Container scanning complements, rather than replaces, the other repository controls:

| Layer | Check |
| --- | --- |
| Python dependencies | `pip-audit` |
| Helm / Dockerfile IaC | Checkov |
| Source hygiene | pre-commit hooks |
| Private-key leakage | pre-commit private-key detection |
| Runtime image | Anchore vulnerability scan |
| Software inventory | SPDX SBOM |
| Release provenance | keyless Cosign signing |

See `docs/security.md` for the complete security posture and `docs/image-signing.md` for release image verification.

## Future tightening

A reasonable future progression is:

1. establish a reviewed vulnerability baseline;
2. document accepted exceptions with expiry/owner information;
3. fail releases on actionable critical findings;
4. optionally apply stricter blocking policy to `main` after false positives and inherited base-image findings are understood.

Blocking thresholds should be introduced intentionally rather than treating scanner output as equivalent to exploitable risk.
