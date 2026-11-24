from pathlib import Path

import yaml
from datasets import load_dataset

config = yaml.safe_load(
    Path("configs/data.yaml").read_text(encoding="utf-8")
)

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