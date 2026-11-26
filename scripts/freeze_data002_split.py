"""Freeze or verify the DATA-002 query split from the reviewed inputs."""

import csv
import hashlib
import json
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory

import pyarrow as pa
import pyarrow.parquet as pq

SEED = 42
WEIGHTS = {"train": 70, "val": 15, "test": 15}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def group_queries(records: list[dict], review: list[dict]) -> dict[str, str]:
    parent = {row["id"]: row["id"] for row in records}
    first_seen = {}

    def root(query_id: str) -> str:
        while parent[query_id] != query_id:
            parent[query_id] = parent[parent[query_id]]
            query_id = parent[query_id]
        return query_id

    def connect(query_id: str, key: tuple[str, str]) -> None:
        parent[root(query_id)] = root(first_seen.setdefault(key, query_id))

    for row in sorted(records, key=lambda row: row["id"]):
        query_id = row["id"]
        question = " ".join(
            unicodedata.normalize("NFKC", row["question"]).casefold().split()
        )
        if question:
            connect(query_id, ("question", question))
        for context in row["contexts"]:
            text = context["text"].replace("\r\n", "\n").replace("\r", "\n")
            connect(query_id, ("filename", Path(context["filename"]).name))
            connect(query_id, ("content", digest(text.encode("utf-8"))))

    for row in review:
        if (
            row["decision"] not in {"merge", "keep_separate"}
            or not row["reason"].strip()
        ):
            raise ValueError("Every candidate pair requires a decision and reason")
        left, right = root(row["left_id"]), root(row["right_id"])
        if row["decision"] == "merge":
            parent[left] = right
    members = defaultdict(list)
    for query_id in sorted(parent):
        members[root(query_id)].append(query_id)
    return {
        query_id: digest("\n".join(group).encode("utf-8"))
        for group in members.values()
        for query_id in group
    }


def allocate(groups: dict[str, str], category: dict[str, str]) -> dict[str, str]:
    members = defaultdict(list)
    for query_id, group_id in groups.items():
        members[group_id].append(query_id)
    totals = Counter(category.values())
    counts = {split: Counter() for split in WEIGHTS}
    result = {}
    ordered = sorted(
        members,
        key=lambda group: (-len(members[group]), digest(f"{SEED}:{group}".encode())),
    )
    for group_id in ordered:
        group = members[group_id]
        distribution = Counter(category[query_id] for query_id in group)

        costs = {
            split: sum(
                count
                * ((2 * counts[split][label] + count) / weight - totals[label] / 50)
                for label, count in distribution.items()
            )
            for split, weight in WEIGHTS.items()
        }

        split = min(costs, key=costs.__getitem__)
        counts[split].update(distribution)
        result.update(dict.fromkeys(group, split))
    return result


def main() -> None:
    processed = Path("data/processed")
    manifests = Path("data/manifests")
    snapshot = json.loads((manifests / "raw_snapshot.json").read_text(encoding="utf-8"))
    source = snapshot["files"]["train.json"]
    raw = Path(source["path"]).read_bytes()
    if digest(raw) != source["sha256"]:
        raise ValueError("Question snapshot hash mismatch")
    records = json.loads(raw)

    review_path = processed / "near_duplicate_review.csv"
    with review_path.open(encoding="utf-8-sig", newline="") as file:
        review = list(csv.DictReader(file))
    unique_pairs = {tuple(sorted((row["left_id"], row["right_id"]))) for row in review}
    if len(review) != len(unique_pairs):
        raise ValueError("Duplicate reviewed pairs")

    queries_path = processed / "queries.parquet"
    queries = pq.read_table(queries_path)
    rows = sorted(queries.to_pylist(), key=lambda row: row["query_id"])
    expected = {
        row["id"]: (row["question"], row["answer"], row["is_impossible"])
        for row in records
    }
    actual = {
        row["query_id"]: (
            row["question"],
            row["reference_answer"],
            row["is_impossible"],
        )
        for row in rows
    }
    if actual != expected or len(rows) != len(records) or len(rows) != len(actual):
        raise ValueError("Query table does not match the pinned source")
    labels_path = manifests / "curated_upstream_qrels.csv"
    with labels_path.open(encoding="utf-8", newline="") as file:
        positive_ids = {row["query_id"] for row in csv.DictReader(file)}
    qrels = pq.read_table(processed / "qrels.parquet", columns=["query_id"])
    if Counter(qrels["query_id"].to_pylist()) != Counter(positive_ids):
        raise ValueError("Processed qrels disagree with the curated query IDs")
    category = {
        query_id: "unanswerable"
        if values[2]
        else "known_positive"
        if query_id in positive_ids
        else "answerable_without_qrel"
        for query_id, values in actual.items()
    }
    if {
        query_id for query_id, label in category.items() if label == "known_positive"
    } != positive_ids:
        raise ValueError("A positive qrel is missing its answerable query")

    groups = group_queries(records, review)
    splits = allocate(groups, category)
    if groups != group_queries(records[::-1], review[::-1]) or splits != allocate(
        dict(reversed(list(groups.items()))), category
    ):
        raise ValueError("Assignments changed after reversing the input order")
    per_group = defaultdict(set)
    summary = {split: Counter() for split in WEIGHTS}
    for row in rows:
        query_id = row["query_id"]
        group_id, split = groups[query_id], splits[query_id]
        if row["group_id"] not in (None, group_id) or row["split"] not in (None, split):
            raise ValueError(f"Refusing to change existing assignment for {query_id}")
        row.update(group_id=group_id, split=split)
        per_group[group_id].add(split)
        summary[split].update([category[query_id], "total"])
    if any(len(values) != 1 for values in per_group.values()):
        raise ValueError("Group crosses splits")
    for row in review:
        merged = groups[row["left_id"]] == groups[row["right_id"]]
        if merged != (row["decision"] == "merge"):
            raise ValueError(
                f"Group assignment contradicts review: {row['left_id']}, {row['right_id']}"
            )

    manifest = {
        "schema_version": 1,
        "dataset_id": snapshot["dataset_id"],
        "dataset_revision": snapshot["revision"],
        "source_questions_sha256": source["sha256"],
        "curated_qrels_sha256": digest(labels_path.read_bytes()),
        "near_duplicate_review_sha256": digest(review_path.read_bytes()),
        "seed": SEED,
        "target_percent": WEIGHTS,
        "grouping": "nfkc_casefold_whitespace_question + context_basename_or_normalized_text_hash + reviewed_near_duplicates",
        "allocation": "largest_group_first_seeded_order_greedy_stratified_squared_error",
        "corpus_policy": "shared_search_corpus; held-out queries, answers and supervision excluded from training and mining",
        "group_count": len(per_group),
        "counts": summary,
        "assignments": [
            {field: row[field] for field in ("query_id", "group_id", "split")}
            for row in rows
        ],
    }
    payload = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    manifest_path = manifests / "split_manifest.json"
    if manifest_path.exists() and manifest_path.read_bytes() != payload:
        raise ValueError("Computed split differs from the frozen manifest")
    updated = pa.Table.from_pylist(rows, schema=queries.schema)
    if not queries.equals(updated):
        with TemporaryDirectory(dir=processed) as directory:
            staged = Path(directory) / queries_path.name
            pq.write_table(updated, staged)
            if not pq.read_table(staged).equals(updated):
                raise ValueError("Staged query table failed verification")
            staged.replace(queries_path)
    if not manifest_path.exists():
        with TemporaryDirectory(dir=manifests) as directory:
            staged = Path(directory) / manifest_path.name
            staged.write_bytes(payload)
            staged.replace(manifest_path)
    print(json.dumps(summary, sort_keys=True))
    print(
        f"Groups: {len(per_group)}, largest: {max(Counter(groups.values()).values())}"
    )
    print(f"Manifest SHA-256: {digest(payload)}")


if __name__ == "__main__":
    main()
