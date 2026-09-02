# Image Signing

EdgePulse release images are signed with Sigstore Cosign by the release workflow.

Workflow:

```text
.github/workflows/release-image.yaml
```

## Signing model

The workflow uses **keyless signing** with GitHub Actions OIDC.

```text
GitHub Actions workload identity
          |
          v
      OIDC token
          |
          v
       Cosign
          |
          v
image digest signature + certificate
```

No long-lived private signing key needs to be committed to the repository or stored as a GitHub Secret.

## Image repository

```text
ghcr.io/imanlotfimahyari/edgepulse-runtime
```

## Version-tagged releases

A Git tag such as:

```text
v0.9.0
```

publishes and signs:

```text
ghcr.io/imanlotfimahyari/edgepulse-runtime:0.9.0
ghcr.io/imanlotfimahyari/edgepulse-runtime:0.9
ghcr.io/imanlotfimahyari/edgepulse-runtime:latest
```

The workflow signs each published tag at the immutable image digest produced by the build.

## Manual releases

The workflow can also be started manually with `workflow_dispatch` and an explicit image tag. That image is built, pushed, and signed through the same keyless OIDC flow.

## Verify a release

Install Cosign, then verify the image against the expected GitHub Actions identity and OIDC issuer:

```bash
cosign verify \
  --certificate-identity-regexp \
  'https://github.com/imanlotfimahyari/edgepulse-ai-runtime/.github/workflows/release-image.yaml@refs/tags/v.*' \
  --certificate-oidc-issuer \
  'https://token.actions.githubusercontent.com' \
  ghcr.io/imanlotfimahyari/edgepulse-runtime:0.9.0
```

A successful verification confirms that the signature certificate matches the configured GitHub Actions workflow identity and issuer.

## Verification scope

Signature verification establishes provenance for the published image; it does not by itself prove that the image is vulnerability-free or that every dependency is trusted.

Use it together with:

- the container SBOM;
- vulnerability scanning;
- dependency auditing;
- reviewed CI results;
- immutable/digest-aware deployment practices where appropriate.

See `docs/container-security.md` and `docs/release.md`.

## Registry access

The image must exist in GHCR before verification. If the package is private, authenticate to GHCR before pulling or verifying it.
