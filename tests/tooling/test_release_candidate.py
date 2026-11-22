"""The release-candidate verifier accepts only an archive whose digest, blobs and attestations agree."""

import hashlib
import io
import json
import tarfile

import pytest

from scripts.release_candidate import CandidateError, verify

REVISION = "c" * 40
LAYER_ID = "sha256:" + "1" * 64


def _blob(blobs: dict[str, bytes], value) -> dict:
    data = value if isinstance(value, bytes) else json.dumps(value).encode()
    digest = "sha256:" + hashlib.sha256(data).hexdigest()
    blobs[digest] = data
    return {"digest": digest, "size": len(data)}


def _statement(predicate_type: str, subject: str, predicate: dict) -> dict:
    return {
        "_type": "https://in-toto.io/Statement/v0.1",
        "predicateType": predicate_type,
        "subject": [{"name": "image", "digest": {"sha256": subject.removeprefix("sha256:")}}],
        "predicate": predicate,
    }


def _candidate(
    tmp_path,
    *,
    revision=REVISION,
    sbom=True,
    provenance=True,
    packages=({"name": "x"},),
    attest_other=False,
    tamper=False,
    drop_layer=False,
    flat_root=False,
):
    blobs: dict[str, bytes] = {}
    layer = _blob(blobs, b"layer-bytes")
    config = _blob(
        blobs,
        {
            "config": {"Labels": {"org.opencontainers.image.revision": revision}},
            "rootfs": {"type": "layers", "diff_ids": [LAYER_ID]},
        },
    )
    image = _blob(
        blobs,
        {
            "mediaType": "application/vnd.oci.image.manifest.v1+json",
            "config": config,
            "layers": [layer],
        },
    )
    subject = "sha256:" + "d" * 64 if attest_other else image["digest"]
    layers = []
    if provenance:
        layers.append(
            {
                **_blob(
                    blobs,
                    _statement("https://slsa.dev/provenance/v0.2", subject, {"builder": {}}),
                ),
                "annotations": {"in-toto.io/predicate-type": "https://slsa.dev/provenance/v0.2"},
            }
        )
    if sbom:
        statement = _statement("https://spdx.dev/Document", subject, {"packages": list(packages)})
        layers.append(
            {
                **_blob(blobs, statement),
                "annotations": {"in-toto.io/predicate-type": "https://spdx.dev/Document"},
            }
        )
    attestation = _blob(
        blobs,
        {
            "mediaType": "application/vnd.oci.image.manifest.v1+json",
            "config": _blob(blobs, {}),
            "layers": layers,
        },
    )
    index = _blob(
        blobs,
        {
            "mediaType": "application/vnd.oci.image.index.v1+json",
            "manifests": [
                {**image, "platform": {"os": "linux", "architecture": "amd64"}},
                {
                    **attestation,
                    "platform": {"os": "unknown", "architecture": "unknown"},
                    "annotations": {
                        "vnd.docker.reference.type": "attestation-manifest",
                        "vnd.docker.reference.digest": image["digest"],
                    },
                },
            ],
        },
    )
    path = tmp_path / "candidate.oci.tar"
    with tarfile.open(path, "w") as archive:
        root = image if flat_root else index
        top = json.dumps({"schemaVersion": 2, "manifests": [root]}).encode()
        files = {"index.json": top, "oci-layout": b'{"imageLayoutVersion":"1.0.0"}'}
        for digest, data in blobs.items():
            if tamper and data == b"layer-bytes":
                data = b"other-bytes"
            if drop_layer and data == b"layer-bytes":
                continue
            files["blobs/sha256/" + digest.removeprefix("sha256:")] = data
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return path, (image if flat_root else index)["digest"], image["digest"]


def test_valid_candidate_reports_its_identity(tmp_path):
    path, digest, image = _candidate(tmp_path)
    result = verify(path, digest, REVISION, [LAYER_ID])
    assert result["index_digest"] == digest
    assert result["image_manifest_digest"] == image
    assert result["sbom"]["packages"] == 1
    assert result["provenance"]["predicate_type"] == "https://slsa.dev/provenance/v0.2"
    assert result["registry_push"] is False


def test_rejects_a_digest_other_than_the_build_output(tmp_path):
    path, _, _ = _candidate(tmp_path)
    with pytest.raises(CandidateError, match="not the built digest"):
        verify(path, "sha256:" + "e" * 64, REVISION)


def test_rejects_a_tampered_blob(tmp_path):
    path, digest, _ = _candidate(tmp_path, tamper=True)
    with pytest.raises(CandidateError, match="does not match its digest"):
        verify(path, digest, REVISION)


def test_rejects_a_missing_sbom(tmp_path):
    path, digest, _ = _candidate(tmp_path, sbom=False)
    with pytest.raises(CandidateError, match="spdx"):
        verify(path, digest, REVISION)


def test_rejects_an_image_built_from_another_revision(tmp_path):
    path, digest, _ = _candidate(tmp_path, revision="f" * 40)
    with pytest.raises(CandidateError, match="revision label"):
        verify(path, digest, REVISION)


def test_rejects_attestations_naming_another_image(tmp_path):
    path, digest, _ = _candidate(tmp_path, attest_other=True)
    with pytest.raises(CandidateError, match="does not name the image manifest"):
        verify(path, digest, REVISION)


@pytest.mark.parametrize(
    ("digest", "revision"),
    [("sha256:short", REVISION), ("sha256:" + "a" * 64, "develop")],
)
def test_rejects_malformed_inputs(tmp_path, digest, revision):
    path, _, _ = _candidate(tmp_path)
    with pytest.raises(CandidateError):
        verify(path, digest, revision)


@pytest.mark.parametrize(
    ("options", "message"),
    [
        ({"drop_layer": True}, "missing from the archive"),
        ({"provenance": False}, "slsa"),
        ({"packages": ()}, "no packages"),
        ({"flat_root": True}, "not an image index"),
    ],
)
def test_rejects_incomplete_candidates(tmp_path, options, message):
    path, digest, _ = _candidate(tmp_path, **options)
    with pytest.raises(CandidateError, match=message):
        verify(path, digest, REVISION)


def test_rejects_layers_other_than_the_tested_image(tmp_path):
    path, digest, _ = _candidate(tmp_path)
    with pytest.raises(CandidateError, match="tested image"):
        verify(path, digest, REVISION, ["sha256:" + "2" * 64])


def test_malformed_documents_fail_closed_as_candidate_errors(tmp_path):
    path, digest, _ = _candidate(tmp_path)
    with tarfile.open(path, "a") as archive:
        data = json.dumps({"schemaVersion": 2, "manifests": [{"size": 1}]}).encode()
        info = tarfile.TarInfo("index.json")
        info.size = len(data)
        archive.addfile(info, io.BytesIO(data))
    with pytest.raises(CandidateError):
        verify(path, digest, REVISION)
