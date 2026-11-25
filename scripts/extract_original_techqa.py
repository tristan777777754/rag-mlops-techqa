"""Extract the small labeled files from a pinned original TechQA archive."""

from __future__ import annotations

import argparse
import hashlib
import os
import tarfile
import tempfile
from pathlib import Path

from huggingface_hub import hf_hub_download

from scripts.audit_dataset import sha256_file, write_json

ORIGINAL_DATASET_ID = "PrimeQA/TechQA"
ORIGINAL_REVISION = "60437bc79ab217679682217598a3693cab78365b"
ARCHIVE_SHA256 = "6b094ef9a69718f727ce8d7e15c4d961e51032cefaa952e0d6af9d176d7ba118"
EXPECTED_FILES = {
    "README.txt",
    "CDLA-Permissive-v1.0.pdf",
    "training_Q_A.json",
    "dev_Q_A.json",
    "training_dev_technotes.json",
}


def extract_pinned_files(archive_path: Path, destination: Path) -> dict:
    if sha256_file(archive_path) != ARCHIVE_SHA256:
        raise ValueError("Original TechQA archive SHA-256 does not match the pin")
    destination.mkdir(parents=True, exist_ok=True)
    files = {}
    with tarfile.open(archive_path, mode="r|gz") as archive:
        for member in archive:
            name = Path(member.name).name
            if name not in EXPECTED_FILES or not member.isfile():
                continue
            expected_parent = (
                "TechQA"
                if name in {"README.txt", "CDLA-Permissive-v1.0.pdf"}
                else "TechQA/training_and_dev"
            )
            if member.name != f"{expected_parent}/{name}":
                continue
            if name in files:
                raise ValueError(f"Duplicate archive member: {name}")
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError(f"Cannot read archive member: {name}")
            with tempfile.NamedTemporaryFile(
                dir=destination, delete=False
            ) as temporary:
                temporary_path = Path(temporary.name)
                digest = hashlib.sha256()
                size = 0
                while block := stream.read(1024 * 1024):
                    temporary.write(block)
                    digest.update(block)
                    size += len(block)
            target = destination / name
            if target.exists():
                if sha256_file(target) != digest.hexdigest():
                    temporary_path.unlink(missing_ok=True)
                    raise ValueError(f"Extracted file changed: {target}")
                temporary_path.unlink()
            else:
                os.replace(temporary_path, target)
            files[name] = {"bytes": size, "sha256": digest.hexdigest()}
            print(f"extracted: {name} ({size} bytes)")
            if files.keys() == EXPECTED_FILES:
                break
    if files.keys() != EXPECTED_FILES:
        raise ValueError(
            f"Missing archive files: {sorted(EXPECTED_FILES - files.keys())}"
        )
    readme = (destination / "README.txt").read_text(encoding="utf-8")
    if "Community Data License Agreement - Permissive - Version 1.0" not in readme:
        raise ValueError("Original archive README license wording changed")
    return {
        "schema_version": 1,
        "dataset_id": ORIGINAL_DATASET_ID,
        "revision": ORIGINAL_REVISION,
        "archive_filename": "TechQA.tar.gz",
        "archive_sha256": ARCHIVE_SHA256,
        "archive_bytes": archive_path.stat().st_size,
        "license_in_archive_readme": "CDLA-Permissive-1.0",
        "files": dict(sorted(files.items())),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--archive", type=Path, help="Use an already downloaded archive"
    )
    args = parser.parse_args()
    archive_path = args.archive or Path(
        hf_hub_download(
            ORIGINAL_DATASET_ID,
            filename="TechQA.tar.gz",
            repo_type="dataset",
            revision=ORIGINAL_REVISION,
        )
    )
    destination = Path("data/raw/TechQA-original") / ORIGINAL_REVISION
    manifest = extract_pinned_files(archive_path, destination)
    write_json(Path("data/manifests/original_techqa_snapshot.json"), manifest)
    print("manifest: data/manifests/original_techqa_snapshot.json")


if __name__ == "__main__":
    main()
