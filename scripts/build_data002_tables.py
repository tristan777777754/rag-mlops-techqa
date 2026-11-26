import argparse
import csv
import json
from hashlib import file_digest, sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import pyarrow as pa
import pyarrow.parquet as pq


def sha256_file(path: Path) -> str:
    with path.open("rb") as file:
        return file_digest(file, "sha256").hexdigest()


def verified_source(snapshot: dict, filename: str) -> Path:
    entry = snapshot["files"][filename]
    path = Path(entry["path"])
    if sha256_file(path) != entry["sha256"]:
        raise ValueError(f"Source hash mismatch: {path}")
    return path


def build_documents(corpus: Path) -> tuple[list[dict], dict]:
    documents = []
    doc_ids = {}
    seen_ids = set()

    with ZipFile(corpus) as archive:
        for entry in archive.infolist():
            if entry.is_dir():
                continue

            filename = Path(entry.filename).name
            raw = archive.read(entry)
            source_hash = sha256(raw).hexdigest()
            text = raw.decode("utf-8")
            normalized = text.replace("\r\n", "\n").replace("\r", "\n")
            normalized_hash = sha256(normalized.encode("utf-8")).hexdigest()
            doc_id = sha256(
                f"{filename}\n{normalized_hash}".encode("utf-8")
            ).hexdigest()

            key = (filename, source_hash)
            if key in doc_ids or doc_id in seen_ids:
                raise ValueError(f"Duplicate document: {filename}")

            doc_ids[key] = doc_id
            seen_ids.add(doc_id)
            documents.append({
                "doc_id": doc_id,
                "source_filename": filename,
                "source_text_sha256": source_hash,
                "normalized_text_sha256": normalized_hash,
                "text": text,
            })

    documents.sort(key=lambda row: row["doc_id"])
    return documents, doc_ids


def build_queries(source: Path, split_manifest: dict) -> list[dict]:
    records = json.loads(source.read_text(encoding="utf-8"))
    assignments = split_manifest["assignments"]
    by_id = {row["query_id"]: row for row in assignments}

    if len(by_id) != len(assignments):
        raise ValueError("Duplicate query ID in split manifest")
    if set(by_id) != {row["id"] for row in records} or len(records) != len(by_id):
        raise ValueError("Source query IDs do not match the split manifest")

    return [
        {
            "query_id": row["id"],
            "question": row["question"],
            "reference_answer": row["answer"],
            "is_impossible": row["is_impossible"],
            "split": by_id[row["id"]]["split"],
            "group_id": by_id[row["id"]]["group_id"],
        }
        for row in sorted(records, key=lambda row: row["id"])
    ]


def build_qrels(labels: Path, doc_ids: dict, queries: list[dict]) -> list[dict]:
    answerable = {row["query_id"] for row in queries if not row["is_impossible"]}
    qrels = []
    seen_pairs = set()

    with labels.open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            query_id = row["query_id"]
            key = (row["source_filename"], row["source_text_sha256"])
            if query_id not in answerable or key not in doc_ids:
                raise ValueError(f"Unresolved positive qrel: {query_id}, {key[0]}")

            doc_id = doc_ids[key]
            pair = (query_id, doc_id)
            if pair in seen_pairs or int(row["relevance"]) != 1:
                raise ValueError(f"Invalid or duplicate positive qrel: {pair}")

            seen_pairs.add(pair)
            qrels.append({
                **row,
                "doc_id": doc_id,
                "relevance": int(row["relevance"]),
                "answer_span_start": int(row["answer_span_start"]),
                "answer_span_end": int(row["answer_span_end"]),
            })

    qrels.sort(key=lambda row: (row["query_id"], row["doc_id"]))
    return qrels


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild the DATA-002 tables")
    parser.add_argument("--output-dir", required=True, type=Path)
    output = parser.parse_args().output_dir
    if output.exists():
        raise FileExistsError(f"Use a new output directory: {output}")

    manifests = Path("data/manifests")
    snapshot = json.loads(
        (manifests / "raw_snapshot.json").read_text(encoding="utf-8")
    )
    split_manifest = json.loads(
        (manifests / "split_manifest.json").read_text(encoding="utf-8")
    )
    labels = manifests / "curated_upstream_qrels.csv"
    corpus = verified_source(snapshot, "corpus.zip")
    source_queries = verified_source(snapshot, "train.json")

    if (
        split_manifest["dataset_revision"] != snapshot["revision"]
        or split_manifest["source_questions_sha256"]
        != snapshot["files"]["train.json"]["sha256"]
        or split_manifest["curated_qrels_sha256"] != sha256_file(labels)
    ):
        raise ValueError("Frozen split inputs do not match the pinned data")

    documents, doc_ids = build_documents(corpus)
    queries = build_queries(source_queries, split_manifest)
    qrels = build_qrels(labels, doc_ids, queries)
    counts = (len(documents), len(queries), len(qrels))
    if counts != (28_481, 910, 595):
        raise ValueError(f"Unexpected table counts: {counts}")

    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent) as temporary:
        staged = Path(temporary) / "tables"
        staged.mkdir()
        for name, rows in (
            ("documents", documents),
            ("queries", queries),
            ("qrels", qrels),
        ):
            pq.write_table(pa.Table.from_pylist(rows), staged / f"{name}.parquet")
        staged.rename(output)

    print(f"Documents: {len(documents):,}")
    print(f"Queries: {len(queries):,}")
    print(f"Qrels: {len(qrels):,}")
    print(f"Saved: {output}")


if __name__ == "__main__":
    main()