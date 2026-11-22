"""Verify a release-candidate OCI archive: digest, every blob hash, SBOM and provenance.

The release candidate is built by BuildKit with ``outputs: type=oci`` and attestations, never
pushed to a registry (DR-13). This check proves that the archive kept as a CI artifact is the image
the build reported: the top-level index points at the reported digest, every referenced blob hashes
to its name, the image config carries the tested revision, and the attestation manifest holds an
SPDX SBOM and a SLSA provenance statement for that exact image manifest.
"""

import argparse
import hashlib
import json
import re
import tarfile
from pathlib import Path

DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
INDEX_TYPES = {
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.docker.distribution.manifest.list.v2+json",
}
SBOM_PREDICATE = "https://spdx.dev/Document"
PROVENANCE_PREDICATES = ("https://slsa.dev/provenance/v0.2", "https://slsa.dev/provenance/v1")
ATTESTATION_KIND = "vnd.docker.reference.type"
ATTESTED_DIGEST = "vnd.docker.reference.digest"
JSON_LIMIT = 64 * 1024 * 1024


class CandidateError(ValueError):
    """The archive is not a verifiable release candidate."""


def _read_archive(path: Path) -> tuple[dict, dict[str, bytes], set[str]]:
    """Hash every blob while streaming; keep only the top index and small JSON blobs."""
    index = None
    documents: dict[str, bytes] = {}
    blobs: set[str] = set()
    with tarfile.open(path) as archive:
        for member in archive:
            name = member.name.removeprefix("./")
            if not member.isfile():
                continue
            handle = archive.extractfile(member)
            if handle is None:
                continue
            if name == "index.json":
                index = json.loads(handle.read())
                continue
            match = re.fullmatch(r"blobs/sha256/([0-9a-f]{64})", name)
            if not match:
                continue
            digest = hashlib.sha256()
            head = b""
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
                if member.size <= JSON_LIMIT:
                    head += chunk
            if digest.hexdigest() != match.group(1):
                raise CandidateError(f"blob {name} does not match its digest")
            blobs.add("sha256:" + match.group(1))
            if member.size <= JSON_LIMIT:
                documents["sha256:" + match.group(1)] = head
    if index is None:
        raise CandidateError("archive has no index.json")
    return index, documents, blobs


def _document(digest: str, documents: dict[str, bytes]) -> dict:
    if digest not in documents:
        raise CandidateError(f"referenced document {digest} is missing")
    return json.loads(documents[digest])


def _statement(manifest: dict, predicate_types: tuple[str, ...], documents: dict) -> dict:
    for layer in manifest.get("layers", []):
        annotation = layer.get("annotations", {}).get("in-toto.io/predicate-type")
        if annotation in predicate_types:
            statement = _document(layer["digest"], documents)
            if statement.get("predicateType") != annotation:
                raise CandidateError(f"statement type differs from its annotation: {annotation}")
            return statement
    raise CandidateError(f"attestation missing: {' or '.join(predicate_types)}")


def verify(path: Path, expected_digest: str, revision: str, platform: str = "linux/amd64") -> dict:
    """Return the verified identity of the archive or raise CandidateError."""
    if not DIGEST.fullmatch(expected_digest):
        raise CandidateError("expected digest must be sha256:<64 hex>")
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise CandidateError("revision must be a full commit SHA")
    index, documents, blobs = _read_archive(path)
    roots = [entry["digest"] for entry in index.get("manifests", [])]
    if roots != [expected_digest]:
        raise CandidateError(
            f"index.json points at {roots}, not the built digest {expected_digest}"
        )
    image_index = _document(expected_digest, documents)
    if image_index.get("mediaType") not in INDEX_TYPES:
        raise CandidateError("built digest is not an image index; attestations are missing")
    os_name, arch = platform.split("/")
    images, attestations = [], []
    for entry in image_index.get("manifests", []):
        if entry.get("annotations", {}).get(ATTESTATION_KIND) == "attestation-manifest":
            attestations.append(entry)
        elif (
            entry.get("platform", {}).get("os"),
            entry.get("platform", {}).get("architecture"),
        ) == (
            os_name,
            arch,
        ):
            images.append(entry)
    if len(images) != 1:
        raise CandidateError(f"expected exactly one {platform} image, found {len(images)}")
    image_digest = images[0]["digest"]
    image = _document(image_digest, documents)
    for layer in image.get("layers", []):
        if layer["digest"] not in blobs:
            raise CandidateError(f"layer {layer['digest']} is missing from the archive")
    config = _document(image["config"]["digest"], documents)
    labels = config.get("config", {}).get("Labels") or {}
    if labels.get("org.opencontainers.image.revision") != revision:
        raise CandidateError("image revision label does not match the tested commit")
    bound = [a for a in attestations if a["annotations"].get(ATTESTED_DIGEST) == image_digest]
    if len(bound) != 1:
        raise CandidateError("expected exactly one attestation manifest for the image")
    attestation = _document(bound[0]["digest"], documents)
    sbom = _statement(attestation, (SBOM_PREDICATE,), documents)
    provenance = _statement(attestation, PROVENANCE_PREDICATES, documents)
    for statement in (sbom, provenance):
        subjects = {"sha256:" + s.get("digest", {}).get("sha256", "") for s in statement["subject"]}
        if image_digest not in subjects:
            raise CandidateError(f"{statement['predicateType']} does not name the image manifest")
    packages = sbom.get("predicate", {}).get("packages", [])
    if not packages:
        raise CandidateError("SBOM lists no packages")
    return {
        "index_digest": expected_digest,
        "image_manifest_digest": image_digest,
        "config_digest": image["config"]["digest"],
        "platform": platform,
        "revision": revision,
        "version": labels.get("org.opencontainers.image.version"),
        "layers": len(image.get("layers", [])),
        "sbom": {"predicate_type": SBOM_PREDICATE, "packages": len(packages)},
        "provenance": {"predicate_type": provenance["predicateType"]},
        "registry_push": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--digest", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = {"name": args.name, **verify(args.archive, args.digest, args.revision)}
    existing = json.loads(args.output.read_text()) if args.output.exists() else {"images": []}
    existing["images"] = [i for i in existing["images"] if i["name"] != args.name] + [result]
    args.output.write_text(json.dumps(existing, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
