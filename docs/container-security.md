# Container Security

EdgePulse includes a container security workflow that builds the runtime image, generates an SBOM, and scans the image for known vulnerabilities.

## Workflow

```text
.github/workflows/container-security.yaml
```

## What it does

The workflow:

1. Builds the runtime container image from `runtime/Dockerfile`.
2. Generates an SPDX JSON SBOM.
3. Uploads the SBOM as a GitHub Actions artifact.
4. Scans the image for known vulnerabilities.
5. Uploads vulnerability results as a SARIF workflow artifact.

## Image scanned

The workflow builds and scans a local CI image:

```text
edgepulse-runtime:security-scan
```

This avoids requiring GHCR credentials during pull-request validation.

## SBOM

The generated SBOM artifact is:

```text
edgepulse-runtime.spdx.json
```

## Vulnerability scan mode

The vulnerability scan is currently configured as visibility-first:

```yaml
fail-build: false
severity-cutoff: high
```

This means findings are reported but do not block the build yet.

After baseline findings are reviewed, this can be tightened to:

```yaml
fail-build: true
severity-cutoff: critical
```

## Related checks

This complements the existing security checks:

- `pip-audit` for Python dependencies;
- `checkov` for Helm and Dockerfile checks;
- pre-commit validation;
- Docker image build validation.


## SARIF artifact

The vulnerability scan produces a SARIF artifact:

```text
edgepulse-runtime-vulnerability-sarif
```

The SARIF file is uploaded as a workflow artifact instead of being uploaded to GitHub Code Scanning.

This keeps the workflow compatible with private repositories that may not have Code Scanning upload permissions or GitHub Advanced Security enabled.
