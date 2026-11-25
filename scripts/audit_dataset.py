"""Audit a pinned TechQA snapshot without printing source text."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import shutil
import statistics
import tempfile
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import yaml
from datasets import load_dataset
from huggingface_hub import HfApi, hf_hub_download

DATASET_FILES = (".gitattributes", "README.md", "corpus.zip", "train.json")
REQUIRED_FIELDS = ("id", "question", "answer", "is_impossible", "contexts")
REVIEW_SEED = 20261125


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as temporary:
        json.dump(value, temporary, ensure_ascii=False, indent=2, sort_keys=True)
        temporary.write("\n")
        temporary_path = Path(temporary.name)
    os.replace(temporary_path, path)


def copy_immutable(source: Path, destination: Path) -> dict[str, object]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_hash = sha256_file(source)
    if destination.exists():
        if sha256_file(destination) != source_hash:
            raise ValueError(f"Pinned raw file changed: {destination}")
    else:
        with tempfile.NamedTemporaryFile(
            dir=destination.parent, delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
        try:
            shutil.copyfile(source, temporary_path)
            os.replace(temporary_path, destination)
        finally:
            temporary_path.unlink(missing_ok=True)
    return {
        "path": destination.as_posix(),
        "bytes": destination.stat().st_size,
        "sha256": source_hash,
    }


def distribution(values: list[int]) -> dict[str, int | float | None]:
    if not values:
        return {"min": None, "median": None, "p95": None, "max": None}
    ordered = sorted(values)
    p95_index = max(0, (95 * len(ordered) + 99) // 100 - 1)
    return {
        "min": ordered[0],
        "median": statistics.median(ordered),
        "p95": ordered[p95_index],
        "max": ordered[-1],
    }


def normalized_question(value: str | None) -> str:
    return " ".join((value or "").casefold().split())


def masked_field_tree(record: dict) -> dict:
    """Describe a source row without copying question, answer, or context text."""
    return {
        "id": {
            "type": type(record["id"]).__name__,
            "sha256": sha256_text(record["id"]),
        },
        "question": {
            "type": type(record["question"]).__name__,
            "chars": len(record["question"] or ""),
        },
        "answer": {
            "type": type(record["answer"]).__name__,
            "chars": len(record["answer"] or ""),
        },
        "is_impossible": {"type": type(record["is_impossible"]).__name__},
        "contexts": {
            "type": type(record["contexts"]).__name__,
            "count": len(record["contexts"] or []),
            "items": [
                {
                    "filename": {
                        "type": type(context["filename"]).__name__,
                        "sha256": sha256_text(context["filename"] or ""),
                    },
                    "text": {
                        "type": type(context["text"]).__name__,
                        "chars": len(context["text"] or ""),
                    },
                }
                for context in (record["contexts"] or [])
            ],
        },
    }


def validate_record(record: object, position: int) -> dict:
    if not isinstance(record, dict):
        raise TypeError(f"Row {position} must be an object")
    missing = set(REQUIRED_FIELDS) - record.keys()
    if missing:
        raise ValueError(f"Row {position} is missing fields: {sorted(missing)}")
    if not isinstance(record["id"], str) or not record["id"].strip():
        raise ValueError(f"Row {position} needs a nonempty string id")
    for field in ("question", "answer"):
        if record[field] is not None and not isinstance(record[field], str):
            raise ValueError(f"Row {position} has a nonstring {field}")
    if record["is_impossible"] is not None and not isinstance(
        record["is_impossible"], bool
    ):
        raise ValueError(f"Row {position} has a nonboolean is_impossible")
    contexts = record["contexts"]
    if contexts is not None and not isinstance(contexts, list):
        raise ValueError(f"Row {position} has a nonlist contexts value")
    for context_index, context in enumerate(contexts or []):
        if not isinstance(context, dict) or not {"filename", "text"} <= context.keys():
            raise ValueError(
                f"Row {position} context {context_index} needs filename and text"
            )
        for field in ("filename", "text"):
            if context[field] is not None and not isinstance(context[field], str):
                raise ValueError(
                    f"Row {position} context {context_index} has a nonstring {field}"
                )
    return record


def audit_records(records: object) -> dict:
    if not isinstance(records, list):
        raise TypeError("train.json must contain a list of records")

    id_counts: Counter[str] = Counter()
    question_groups: dict[str, list[str]] = defaultdict(list)
    context_references: dict[tuple[str, str], set[str]] = defaultdict(set)
    context_sizes: dict[tuple[str, str], int] = {}
    filename_counts: Counter[str] = Counter()
    context_counts: list[int] = []
    context_lengths: list[int] = []
    null_counts: Counter[str] = Counter()
    impossible_counts: Counter[str] = Counter()
    empty_answer_ids: list[str] = []
    empty_question_ids: list[str] = []
    replacement_character_contexts = 0

    for position, raw_record in enumerate(records):
        record = validate_record(raw_record, position)
        query_id = record["id"]
        id_counts[query_id] += 1
        for field in REQUIRED_FIELDS:
            null_counts[field] += record[field] is None

        question = normalized_question(record["question"])
        question_groups[question].append(query_id)
        if not question:
            empty_question_ids.append(query_id)
        if not (record["answer"] or "").strip():
            empty_answer_ids.append(query_id)

        flag = record["is_impossible"]
        impossible_counts["null" if flag is None else str(flag).lower()] += 1
        contexts = record["contexts"] or []
        context_counts.append(len(contexts))
        for context in contexts:
            filename = context["filename"] or ""
            text = context["text"] or ""
            filename_counts[filename] += 1
            content_hash = sha256_text(text)
            context_references[(filename, content_hash)].add(query_id)
            context_sizes[(filename, content_hash)] = len(text)
            context_lengths.append(len(text))
            replacement_character_contexts += "\ufffd" in text

    rows_by_id = {record["id"]: record for record in records}
    duplicate_groups = []
    for question, ids in sorted(question_groups.items()):
        if len(ids) < 2:
            continue
        ordered_ids = sorted(ids)
        first = rows_by_id[ordered_ids[0]]
        duplicate_groups.append(
            {
                "query_ids": ordered_ids,
                "normalized_question_sha256": sha256_text(question),
                "same_contexts": all(
                    rows_by_id[id_]["contexts"] == first["contexts"]
                    for id_ in ordered_ids
                ),
                "same_answers": all(
                    (rows_by_id[id_]["answer"] or "").strip()
                    == (first["answer"] or "").strip()
                    for id_ in ordered_ids
                ),
                "same_impossible": all(
                    rows_by_id[id_]["is_impossible"] == first["is_impossible"]
                    for id_ in ordered_ids
                ),
            }
        )

    unique_questions = sorted(question_groups)
    question_tokens = {question: set(question.split()) for question in unique_questions}
    near_duplicates = []
    for index, first in enumerate(unique_questions):
        first_tokens = question_tokens[first]
        if not first_tokens:
            continue
        for second in unique_questions[index + 1 :]:
            second_tokens = question_tokens[second]
            if (
                not second_tokens
                or min(len(first_tokens), len(second_tokens))
                / max(len(first_tokens), len(second_tokens))
                < 0.9
            ):
                continue
            score = len(first_tokens & second_tokens) / len(
                first_tokens | second_tokens
            )
            if score >= 0.9:
                near_duplicates.append(
                    {
                        "query_ids_a": sorted(question_groups[first]),
                        "query_ids_b": sorted(question_groups[second]),
                        "token_jaccard": round(score, 4),
                    }
                )

    context_variants = [
        {
            "filename": filename,
            "text_sha256": content_hash,
            "query_ids": sorted(query_ids),
        }
        for (filename, content_hash), query_ids in sorted(context_references.items())
    ]
    return {
        "row_count": len(records),
        "unique_ids": len(id_counts),
        "duplicate_id_entries": sum(count - 1 for count in id_counts.values()),
        "duplicate_id_groups": [
            {"id": id_, "count": count}
            for id_, count in sorted(id_counts.items())
            if count > 1
        ],
        "null_counts": dict(sorted(null_counts.items())),
        "empty_question_ids": sorted(empty_question_ids),
        "empty_answer_ids": sorted(empty_answer_ids),
        "impossible_counts": dict(sorted(impossible_counts.items())),
        "empty_context_rows": sum(count == 0 for count in context_counts),
        "context_count_per_query": distribution(context_counts),
        "context_text_length_chars": distribution(context_lengths),
        "context_occurrences": sum(context_counts),
        "unique_context_filenames": len(filename_counts),
        "unique_context_text_hashes": len({hash_ for _, hash_ in context_references}),
        "unique_context_variants": len(context_references),
        "reused_context_variants": sum(
            len(ids) > 1 for ids in context_references.values()
        ),
        "max_queries_per_context_variant": max(
            (len(ids) for ids in context_references.values()), default=0
        ),
        "filename_reuse": [
            {"filename": name, "occurrences": count}
            for name, count in sorted(filename_counts.items())
            if count > 1
        ],
        "context_variants": context_variants,
        "long_contexts_over_50000_chars": [
            {
                "filename": filename,
                "text_sha256": content_hash,
                "characters": size,
                "query_ids": sorted(context_references[(filename, content_hash)]),
            }
            for (filename, content_hash), size in sorted(context_sizes.items())
            if size > 50_000
        ],
        "replacement_character_contexts": replacement_character_contexts,
        "duplicate_question_entries": sum(
            len(ids) - 1 for ids in question_groups.values()
        ),
        "duplicate_question_groups": duplicate_groups,
        "near_duplicate_policy": "Distinct normalized question strings with token-set Jaccard >= 0.9",
        "near_duplicate_pairs": near_duplicates,
    }


def audit_corpus(archive_path: Path, context_variants: list[dict]) -> dict:
    filenames: dict[str, str] = {}
    filename_collisions: list[str] = []
    content_hashes: set[str] = set()
    sizes: list[int] = []
    undecodable_utf8 = 0
    with zipfile.ZipFile(archive_path) as archive:
        for item in archive.infolist():
            if item.is_dir():
                continue
            name = Path(item.filename).name
            content = archive.read(item)
            content_hash = hashlib.sha256(content).hexdigest()
            if name in filenames:
                filename_collisions.append(name)
            filenames[name] = content_hash
            content_hashes.add(content_hash)
            sizes.append(len(content))
            try:
                content.decode("utf-8")
            except UnicodeDecodeError:
                undecodable_utf8 += 1

    missing = []
    content_mismatches = []
    for context in context_variants:
        filename = context["filename"]
        if filename not in filenames:
            missing.append(filename)
        elif filenames[filename] != context["text_sha256"]:
            content_mismatches.append(filename)
    return {
        "file_count": len(sizes),
        "unique_filenames": len(filenames),
        "unique_content_hashes": len(content_hashes),
        "size_bytes": distribution(sizes),
        "total_uncompressed_bytes": sum(sizes),
        "undecodable_utf8_files": undecodable_utf8,
        "duplicate_filenames": sorted(set(filename_collisions)),
        "context_variants_with_matching_filename": len(context_variants) - len(missing),
        "context_variants_with_matching_content": len(context_variants)
        - len(missing)
        - len(content_mismatches),
        "missing_context_filenames": sorted(set(missing)),
        "context_content_mismatch_filenames": sorted(set(content_mismatches)),
    }


def select_review_sample(
    records: list[dict], seed: int = REVIEW_SEED
) -> tuple[dict, list[dict]]:
    by_id = {record["id"]: record for record in records}
    targeted = sorted(
        record["id"]
        for record in records
        if record["is_impossible"] is False and not (record["answer"] or "").strip()
    )
    answerable = sorted(
        record["id"]
        for record in records
        if record["is_impossible"] is False and (record["answer"] or "").strip()
    )
    impossible = sorted(
        record["id"] for record in records if record["is_impossible"] is True
    )
    generator = random.Random(seed)
    selected = (
        [
            (id_, "random_answerable")
            for id_ in generator.sample(answerable, min(25, len(answerable)))
        ]
        + [
            (id_, "random_impossible")
            for id_ in generator.sample(impossible, min(10, len(impossible)))
        ]
        + [(id_, "targeted_empty_answer") for id_ in targeted]
    )
    entries = []
    packets = []
    for query_id, selection_reason in selected:
        record = by_id[query_id]
        contexts = record["contexts"] or []
        context_ids = [
            sha256_text((context["filename"] or "") + "\0" + (context["text"] or ""))
            for context in contexts
        ]
        entries.append(
            {
                "query_id": query_id,
                "context_ids": context_ids,
                "selection_reason": selection_reason,
            }
        )
        packets.append(
            {
                "query_id": query_id,
                "question": record["question"],
                "answer": record["answer"],
                "is_impossible": record["is_impossible"],
                "selection_reason": selection_reason,
                "contexts": [
                    {"context_id": id_, **context}
                    for id_, context in zip(context_ids, contexts, strict=True)
                ],
            }
        )
    manifest = {
        "schema_version": 1,
        "seed": seed,
        "selection_policy": "25 random nonempty-answer answerable queries, 10 random impossible queries, plus all answerable empty-answer queries",
        "population_answerable_nonempty": len(answerable),
        "population_impossible": len(impossible),
        "entries": entries,
        "review_status": "pending_human_review",
    }
    return manifest, packets


def prepare_review_form(path: Path, manifest: dict, revision: str) -> None:
    fields = (
        "dataset_revision",
        "query_id",
        "context_id",
        "selection_reason",
        "relevant_yes_no",
        "answer_supported",
        "impossible_label_valid",
        "reviewer",
        "reason",
    )
    expected = [
        (revision, entry["query_id"], context_id, entry["selection_reason"])
        for entry in manifest["entries"]
        for context_id in (entry["context_ids"] or [""])
    ]
    if path.exists():
        with path.open(newline="", encoding="utf-8") as source:
            reader = csv.DictReader(source)
            if reader.fieldnames != list(fields):
                raise ValueError(
                    f"Review form columns differ from expected schema: {path}"
                )
            actual = [
                (
                    row["dataset_revision"],
                    row["query_id"],
                    row["context_id"],
                    row["selection_reason"],
                )
                for row in reader
            ]
        if actual != expected:
            raise ValueError(f"Review form sample differs from pinned snapshot: {path}")
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", newline="", encoding="utf-8") as destination:
        writer = csv.writer(destination)
        writer.writerow(fields)
        for identity in expected:
            writer.writerow([*identity, "", "", "", "", ""])


def render_report(summary: dict, snapshot: dict, review: dict) -> str:
    metrics = summary["records"]
    corpus = summary["corpus"]
    duplicate_groups = metrics["duplicate_question_groups"]
    same_contexts = sum(group["same_contexts"] for group in duplicate_groups)
    different_flags = sum(not group["same_impossible"] for group in duplicate_groups)
    lines = [
        "# DATA-001 資料稽核",
        "",
        f"來源為 NVIDIA `nvidia/TechQA-RAG-Eval`，revision `{snapshot['revision']}`。",
        f"資料卡標示授權為 `{snapshot['license']}`。來源標註與 context 關聯尚待人工審核。",
        "固定版本資料卡記載 908 組問答；本次原始 `train.json` 與 Datasets loader 均為 910 列。以下統計以原始檔實測為準。",
        "",
        "## 來源與完整性",
        "",
        f"原始 `train.json` SHA-256 為 `{snapshot['files']['train.json']['sha256']}`。",
        f"`corpus.zip` SHA-256 為 `{snapshot['files']['corpus.zip']['sha256']}`。",
        "其餘來源檔的大小與雜湊見 `data/manifests/raw_snapshot.json`。原始檔保存在 `data/raw/`，由 Git 排除。",
        "",
        "## 資料列統計",
        "",
        "| 指標 | 實測結果 |",
        "|---|---:|",
        f"| `train` 列數 | {metrics['row_count']} |",
        f"| 唯一 ID | {metrics['unique_ids']} |",
        f"| 重複 ID 額外筆數 | {metrics['duplicate_id_entries']} |",
        f"| `is_impossible=true` | {metrics['impossible_counts'].get('true', 0)} |",
        f"| `is_impossible=false` | {metrics['impossible_counts'].get('false', 0)} |",
        f"| 空問題 | {len(metrics['empty_question_ids'])} |",
        f"| 空答案 | {len(metrics['empty_answer_ids'])} |",
        f"| 空 contexts | {metrics['empty_context_rows']} |",
        f"| 正規化問題文字重複群組 | {len(duplicate_groups)} |",
        f"| 近似問題候選配對 | {len(metrics['near_duplicate_pairs'])} |",
        f"| context 出現次數 | {metrics['context_occurrences']} |",
        f"| 唯一 context 檔名 | {metrics['unique_context_filenames']} |",
        f"| 唯一 context 文字 SHA-256 | {metrics['unique_context_text_hashes']} |",
        f"| 多題共用的 context 版本 | {metrics['reused_context_variants']} |",
        "",
        f"空答案 ID 為 {', '.join(f'`{id_}`' for id_ in metrics['empty_answer_ids']) or '無'}。",
        "問題正規化採 Unicode casefold、移除多餘空白。近似問題候選使用不同問題文字的 token set Jaccard >= 0.9，屬於待人工確認的候選。",
        "",
        "來源欄位及巢狀型別由 pinned snapshot 的 Datasets loader 驗證。實際 features 如下。",
        "前兩筆的遮罩欄位樹記於 JSON 報告的 `first_two_masked_field_trees`，僅保留型別、長度與雜湊。",
        "",
        f"`{summary['dataset_features']}`",
        "",
        "| 欄位 | null 筆數 |",
        "|---|---:|",
    ]
    for field, count in metrics["null_counts"].items():
        lines.append(f"| `{field}` | {count} |")
    lines.extend(
        [
            "",
            "## 文件與 context",
            "",
            "| 長度分布 | 最小 | 中位數 | p95 | 最大 |",
            "|---|---:|---:|---:|---:|",
            f"| 每題 context 數 | {metrics['context_count_per_query']['min']} | {metrics['context_count_per_query']['median']} | {metrics['context_count_per_query']['p95']} | {metrics['context_count_per_query']['max']} |",
            f"| context 文字字元數 | {metrics['context_text_length_chars']['min']} | {metrics['context_text_length_chars']['median']} | {metrics['context_text_length_chars']['p95']} | {metrics['context_text_length_chars']['max']} |",
            f"| corpus 文件 bytes | {corpus['size_bytes']['min']} | {corpus['size_bytes']['median']} | {corpus['size_bytes']['p95']} | {corpus['size_bytes']['max']} |",
            "",
            f"`corpus.zip` 有 {corpus['file_count']} 個檔案，解壓後總計 {corpus['total_uncompressed_bytes']} bytes，唯一檔名 {corpus['unique_filenames']} 個。",
            f"{corpus['context_variants_with_matching_filename']} / {metrics['unique_context_variants']} 個來源 context 版本在 corpus 中找到同名檔案；{corpus['context_variants_with_matching_content']} / {metrics['unique_context_variants']} 個內容 SHA-256 也相符。",
            f"無法以 UTF-8 解碼的 corpus 檔案有 {corpus['undecodable_utf8_files']} 個；來源 context 文字含替代字元的出現次數有 {metrics['replacement_character_contexts']} 次。",
            f"同一 context 版本最多出現在 {metrics['max_queries_per_context_variant']} 筆查詢。檔名重複出現的明細及所有 context 指紋見 JSON 報告。",
            f"字元數超過 50,000 的不同 context 版本共有 {len(metrics['long_contexts_over_50000_chars'])} 個。",
            "",
            "## 重複問題與標註風險",
            "",
            f"{len(duplicate_groups)} 組問題文字相同，其中 {same_contexts} 組 contexts 相同，{different_flags} 組 `is_impossible` 標記不同。",
            "下表保存每組來源 ID 與欄位相等結果。字串相等不代表答案正確，也不建立正式 relevance label。",
            "",
            "| 來源 ID | contexts 相同 | 答案字串相同 | `is_impossible` 相同 |",
            "|---|---|---|---|",
        ]
    )
    for group in duplicate_groups:
        ids = ", ".join(f"`{id_}`" for id_ in group["query_ids"])
        lines.append(
            f"| {ids} | {group['same_contexts']} | {group['same_answers']} | {group['same_impossible']} |"
        )
    lines.extend(
        [
            "",
            "## 近似問題候選",
            "",
            "以下比較採不同正規化文字的 token 集合 Jaccard。分數是自動候選指標，需人工判讀；ID 群組內可能含完全相同文字的多筆記錄。",
            "",
            "| ID 群組 A | ID 群組 B | Jaccard |",
            "|---|---|---:|",
        ]
    )
    for pair in metrics["near_duplicate_pairs"]:
        first_ids = ", ".join(f"`{id_}`" for id_ in pair["query_ids_a"])
        second_ids = ", ".join(f"`{id_}`" for id_ in pair["query_ids_b"])
        lines.append(f"| {first_ids} | {second_ids} | {pair['token_jaccard']} |")
    lines.extend(
        [
            "",
            "## 人工審核樣本",
            "",
            f"固定 seed `{review['seed']}`。抽樣 {sum(entry['selection_reason'] == 'random_answerable' for entry in review['entries'])} 筆有答案且標為可回答、{sum(entry['selection_reason'] == 'random_impossible' for entry in review['entries'])} 筆標為不可回答，另納入 {sum(entry['selection_reason'] == 'targeted_empty_answer' for entry in review['entries'])} 筆空答案異常。",
            "樣本選取與來源 ID 見 `data/manifests/relevance_review_sample.json`。人工審核結果填於 `reports/relevance_review.csv`；包含原始文字的本地審核包保存在 `data/review/review_packets.json`。重跑稽核腳本會保留已填寫的審核表。目前狀態為待人工審核。",
            "審核時依 `query_id` 對照本地審核包的 question、answer、contexts。可回答題填 `relevant_yes_no`（context 是否切題）與 `answer_supported`（context 是否足以支持答案）；不可回答題因無來源 context，前兩欄填 `N/A`，檢查 `impossible_label_valid`。空答案異常需在 `reason` 說明。每列填 `reviewer` 與判斷理由；不確定時填 `unsure` 並說明。",
            "",
            "## 尚待決策",
            "",
            "來源 context 僅作 relevance 候選。人工審核完成後，記錄支持比例、錯誤案例與 Gate A 決策。資料切分需把相同或近似問題及共用文件關係納入檢查。資料集未提供經驗證的語言標籤，本輪未推斷完整語言分布。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/data.yaml"))
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    dataset_id = config["dataset_id"]
    revision = config["revision"]
    if len(revision) != 40 or any(char not in "0123456789abcdef" for char in revision):
        raise ValueError(
            "Dataset revision must be a full lowercase 40-character commit SHA"
        )

    source_info = HfApi().dataset_info(
        dataset_id, revision=revision, files_metadata=True
    )
    if source_info.sha != revision:
        raise ValueError(
            f"Resolved revision {source_info.sha} differs from pinned {revision}"
        )
    raw_directory = Path("data/raw/TechQA-RAG-Eval") / revision
    raw_files = {}
    for name in DATASET_FILES:
        cached = Path(
            hf_hub_download(
                dataset_id, filename=name, revision=revision, repo_type="dataset"
            )
        )
        raw_files[name] = copy_immutable(cached, raw_directory / name)

    snapshot = {
        "schema_version": 1,
        "dataset_id": dataset_id,
        "revision": revision,
        "license": getattr(source_info.card_data, "license", None),
        "files": raw_files,
    }
    with (raw_directory / "train.json").open(encoding="utf-8") as source:
        records = json.load(source)
    record_metrics = audit_records(records)
    corpus_metrics = audit_corpus(
        raw_directory / "corpus.zip", record_metrics["context_variants"]
    )

    loaded = load_dataset(dataset_id, revision=revision)
    if set(loaded) != {"train"} or len(loaded["train"]) != len(records):
        raise ValueError("Pinned datasets loader disagrees with raw train.json")

    review_manifest, review_packets = select_review_sample(records)
    review_manifest["dataset_id"] = dataset_id
    review_manifest["revision"] = revision
    review_manifest["raw_train_sha256"] = raw_files["train.json"]["sha256"]
    summary = {
        "schema_version": 1,
        "dataset_id": dataset_id,
        "revision": revision,
        "source_split": "train",
        "raw_train_sha256": raw_files["train.json"]["sha256"],
        "dataset_features": str(loaded["train"].features),
        "first_two_masked_field_trees": [
            masked_field_tree(record) for record in records[:2]
        ],
        "dataset_fingerprint": loaded["train"]._fingerprint,
        "label_provenance": "source_context_candidates_unreviewed",
        "records": record_metrics,
        "corpus": corpus_metrics,
        "review_status": "pending_human_review",
    }
    write_json(Path("data/manifests/raw_snapshot.json"), snapshot)
    write_json(Path("data/manifests/relevance_review_sample.json"), review_manifest)
    write_json(Path("data/review/review_packets.json"), review_packets)
    prepare_review_form(Path("reports/relevance_review.csv"), review_manifest, revision)
    write_json(Path("reports/dataset_audit.json"), summary)
    Path("reports/dataset_audit.md").write_text(
        render_report(summary, snapshot, review_manifest), encoding="utf-8"
    )
    print(f"revision: {revision}")
    print(f"rows: {record_metrics['row_count']}")
    print(f"raw train SHA-256: {raw_files['train.json']['sha256']}")
    print("audit: reports/dataset_audit.md, reports/dataset_audit.json")
    print("human review: pending")


if __name__ == "__main__":
    main()
