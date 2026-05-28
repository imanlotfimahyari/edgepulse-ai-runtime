# Image Signing

EdgePulse runtime images are signed with Sigstore Cosign during the release workflow.

## Workflow

```text
.github/workflows/release-image.yaml
```

## Signing model

The release workflow uses keyless signing with GitHub Actions OIDC.

This avoids storing a private signing key in the repository or in GitHub Secrets.

## Image

```text
ghcr.io/imanlotfimahyari/edgepulse-runtime
```

## Signed tags

Version-tagged releases publish and sign:

```text
ghcr.io/imanlotfimahyari/edgepulse-runtime:<version>
ghcr.io/imanlotfimahyari/edgepulse-runtime:<major>.<minor>
ghcr.io/imanlotfimahyari/edgepulse-runtime:latest
```

For example, `v0.8.0` publishes and signs:

```text
ghcr.io/imanlotfimahyari/edgepulse-runtime:0.8.0
ghcr.io/imanlotfimahyari/edgepulse-runtime:0.8
ghcr.io/imanlotfimahyari/edgepulse-runtime:latest
```

## Verify image signature

Install Cosign locally, then verify the image signature.

```bash
cosign verify \
  --certificate-identity-regexp "https://github.com/imanlotfimahyari/edgepulse-ai-runtime/.github/workflows/release-image.yaml@refs/tags/v.*" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
  ghcr.io/imanlotfimahyari/edgepulse-runtime:0.8.0
```

## Notes

The image must already exist in GHCR before verification.

The package must be public, or the verifier must authenticate to GHCR before verification.
