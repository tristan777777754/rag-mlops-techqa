from hashlib import sha256
from pathlib import Path

import yaml
from datasets import load_dataset

config = yaml.safe_load(Path("configs/data.yaml").read_text(encoding="utf-8"))

dataset = load_dataset(
    config["dataset_id"],
    revision=config["revision"],
)

for split_name, rows in dataset.items():
    print("split:", split_name)
    print("rows:", len(rows))
    print("columns:", rows.column_names)
    print("features:", rows.features)
    print("impossible:", sum(bool(row["is_impossible"]) for row in rows))
    print("empty answers:", sum(not (row["answer"] or "").strip() for row in rows))
    print("empty contexts:", sum(not row["contexts"] for row in rows))
    print(
        "impossible and empty contexts:",
        sum(row["is_impossible"] and not row["contexts"] for row in rows),
    )
    print(
        "answerable but empty contexts:",
        sum(not row["is_impossible"] and not row["contexts"] for row in rows),
    )
    for row in rows:
        if not (row["answer"] or "").strip():
            print("empty answer ID:", row["id"], "impossible:", row["is_impossible"])
    ids = [row["id"] for row in rows]
    print("duplicate ID entries:", len(ids) - len(set(ids)))
    questions = [" ".join((row["question"] or "").casefold().split()) for row in rows]
    print("duplicate question entries:", len(questions) - len(set(questions)))

    question_ids = {}
    for row, question in zip(rows, questions):
        question_ids.setdefault(question, []).append(row["id"])

    duplicate_groups = [
        group_ids for group_ids in question_ids.values() if len(group_ids) > 1
    ]
    print("empty questions:", sum(not question for question in questions))
    print("duplicate question groups:", len(duplicate_groups))
    for group_ids in duplicate_groups:
        print("group IDs:", group_ids)

    check_ids = {"TRAIN_Q285", "DEV_Q094", "TRAIN_Q299", "DEV_Q014"}
    for row in rows:
        if row["id"] in check_ids:
            print(
                row["id"],
                "impossible:",
                row["is_impossible"],
                "answer chars:",
                len((row["answer"] or "").strip()),
                "contexts:",
                len(row["contexts"] or []),
            )

            context = row["contexts"][0]
            text_hash = sha256((context["text"] or "").encode("utf-8")).hexdigest()
            print("context source:", row["id"], context["filename"], text_hash)

    rows_by_id = {row["id"]: row for row in rows}
    for group_ids in duplicate_groups:
        first = rows_by_id[group_ids[0]]
        second = rows_by_id[group_ids[1]]
        print(
            group_ids,
            "same contexts:",
            first["contexts"] == second["contexts"],
            "same answers:",
            (first["answer"] or "").strip() == (second["answer"] or "").strip(),
            "same impossible:",
            first["is_impossible"] == second["is_impossible"],
        )
