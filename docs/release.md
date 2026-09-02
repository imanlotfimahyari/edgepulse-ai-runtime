# Release and Image Publishing

EdgePulse runtime images are published to GitHub Container Registry by:

```text
.github/workflows/release-image.yaml
```

Image repository:

```text
ghcr.io/imanlotfimahyari/edgepulse-runtime
```

## Release triggers

The workflow supports two release paths.

### Semantic-version tag

Any tag matching:

```text
v*.*.*
```

starts the release workflow.

For example:

```text
v0.9.0
```

### Manual workflow run

`workflow_dispatch` can publish an explicit manual image tag. This is useful for controlled development or validation builds that should still use the normal GHCR/signing pipeline.

## Version-tag output

For `v0.9.0`, Docker metadata generates:

```text
ghcr.io/imanlotfimahyari/edgepulse-runtime:0.9.0
ghcr.io/imanlotfimahyari/edgepulse-runtime:0.9
ghcr.io/imanlotfimahyari/edgepulse-runtime:latest
```

The build uses:

```text
context: ./runtime
Dockerfile: ./runtime/Dockerfile
```

## Release pipeline

```text
Git tag / manual dispatch
          |
          v
checkout + Buildx
          |
          v
login to GHCR
          |
          v
build runtime image
          |
          v
push tags to GHCR
          |
          v
Cosign keyless signing at image digest
```

The workflow has only the permissions it needs for this path:

```text
contents: read
packages: write
id-token: write
```

`id-token: write` is used for keyless Cosign signing through GitHub Actions OIDC.

## Suggested version release checklist

Before creating a version tag:

1. merge the intended changes to `main`;
2. ensure CI is green;
3. ensure runtime/chart documentation reflects the release;
4. keep `charts/edgepulse-runtime/Chart.yaml` `version` and `appVersion` aligned when the chart changes with the application;
5. verify the default runtime image tag in chart values;
6. create and push the tag.

Example:

```bash
git switch main
git fetch origin
git merge --ff-only origin/main

git tag v0.9.0
git push origin v0.9.0
```

Do not move or reuse a published semantic-version tag. Publish a new patch/minor version instead.

## Verify the published image

After the workflow succeeds:

```bash
docker pull ghcr.io/imanlotfimahyari/edgepulse-runtime:0.9.0
```

Inspect:

```bash
docker image inspect ghcr.io/imanlotfimahyari/edgepulse-runtime:0.9.0
```

Then verify the Cosign signature as documented in `docs/image-signing.md`.

## Relationship to CI and container security

The release workflow is responsible for **publishing and signing**.

Other workflows cover different concerns:

```text
CI workflow
  -> tests, lint, Helm, dependency/IaC checks, Compose E2E

container-security workflow
  -> SBOM + vulnerability scan

release-image workflow
  -> GHCR publication + keyless signature
```

Keeping these responsibilities separate makes failures easier to diagnose and keeps pull-request validation independent from registry publication.
