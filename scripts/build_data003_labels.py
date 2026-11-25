"""Align original human-annotated TechQA labels to the pinned RAG corpus."""

from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from collections import Counter
from pathlib import Path

import yaml

from scripts.audit_dataset import sha256_file, sha256_text, write_json
from scripts.extract_original_techqa import ORIGINAL_REVISION

ORIGINAL_ROOT = Path("data/raw/TechQA-original") / ORIGINAL_REVISION
ADAPTED_ROOT = Path("data/raw/TechQA-RAG-Eval")
QREL_FIELDS = [
    "query_id",
    "source_filename",
    "source_text_sha256",
    "context_id",
    "relevance",
    "label_source",
    "label_status",
    "original_document_id",
    "answer_span_start",
    "answer_span_end",
    "original_answer_sha256",
    "local_review_status",
]
EXCLUSION_FIELDS = [
    "query_id",
    "original_document_id",
    "source_filename",
    "reason_codes",
    "local_review_status",
]


def normalized(value: str) -> str:
    return " ".join(value.split())


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def read_review(path: Path) -> dict[str, dict]:
    with path.open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    by_id = {row["query_id"]: row for row in rows}
    if len(by_id) != len(rows):
        raise ValueError("Review CSV contains duplicate query IDs")
    return by_id


def verify_raw_files(root: Path, manifest: dict) -> None:
    for filename, metadata in manifest["files"].items():
        path = root / filename
        if not path.is_file() or sha256_file(path) != metadata["sha256"]:
            raise ValueError(f"Raw source hash mismatch: {path}")


def review_status(review: dict | None) -> str:
    if review is None:
        return "not_sampled"
    reviewer = review["reviewer"]
    if reviewer.startswith("Codex"):
        return "ai_preliminary"
    if reviewer and review["relevant_yes_no"] in {"yes", "no"}:
        return "local_human_assisted"
    return "unattributed"


def build_labels(
    original_rows: list[dict],
    adapted_rows: list[dict],
    documents: dict[str, dict],
    reviews: dict[str, dict],
    corpus_hashes: dict[str, str],
) -> tuple[list[dict], list[dict], dict, dict]:
    original_by_id = {row["QUESTION_ID"]: row for row in original_rows}
    adapted_by_id = {row["id"]: row for row in adapted_rows}
    if len(original_by_id) != len(original_rows) or len(adapted_by_id) != len(
        adapted_rows
    ):
        raise ValueError("Duplicate question ID in raw sources")
    if original_by_id.keys() != adapted_by_id.keys():
        raise ValueError("Original and adapted question IDs differ")
    if not reviews.keys() <= adapted_by_id.keys():
        raise ValueError("Review CSV refers to unknown question IDs")

    qrels = []
    exclusions = []
    candidate_pools = {}
    counts = Counter()
    all_candidate_ids = set()
    for query_id in sorted(original_by_id):
        original = original_by_id[query_id]
        adapted = adapted_by_id[query_id]
        answerable = original["ANSWERABLE"] == "Y"
        if original["ANSWERABLE"] not in {"Y", "N"}:
            raise ValueError(f"Unknown ANSWERABLE value for {query_id}")
        if normalized(
            original["QUESTION_TITLE"] + " " + original["QUESTION_TEXT"]
        ) != normalized(adapted["question"]):
            raise ValueError(f"Question text differs for {query_id}")
        if normalized(original["ANSWER"]) != normalized(adapted["answer"]):
            raise ValueError(f"Reference answer differs for {query_id}")
        if answerable == adapted["is_impossible"]:
            raise ValueError(f"Answerability differs for {query_id}")
        candidates = original["DOC_IDS"]
        if not isinstance(candidates, list) or not all(
            isinstance(item, str) for item in candidates
        ):
            raise ValueError(f"Invalid candidate document IDs for {query_id}")
        all_candidate_ids.update(candidates)
        candidate_pools[query_id] = {
            "candidate_document_ids": candidates,
            "original_answerable": answerable,
        }
        counts["total_queries"] += 1
        counts["original_answerable" if answerable else "original_unanswerable"] += 1

        contexts = adapted["contexts"] or []
        if not answerable:
            if contexts or original["DOCUMENT"] not in {"", "-", None}:
                raise ValueError(
                    f"Unanswerable query has a source positive: {query_id}"
                )
            continue
        if len(contexts) != 1 or original["DOCUMENT"] not in candidates:
            raise ValueError(
                f"Answerable query has invalid positive context: {query_id}"
            )
        document_id = original["DOCUMENT"]
        document = documents.get(document_id)
        if document is None or document["id"] != document_id:
            raise ValueError(f"Original document missing or mismatched for {query_id}")
        context = contexts[0]
        filename = f"{document_id}.txt"
        if context["filename"] != filename:
            raise ValueError(f"Positive filename differs for {query_id}")
        expected_text = f"Title: {document['title']}\n\nText:\n{document['text']}"
        if context["text"] != expected_text:
            raise ValueError(
                f"Original and adapted document text differ for {query_id}"
            )
        context_hash = sha256_text(expected_text)
        if corpus_hashes.get(filename) != context_hash:
            raise ValueError(f"Pinned corpus document differs for {query_id}")

        review = reviews.get(query_id)
        local_status = review_status(review)
        reasons = []
        try:
            start = int(original["START_OFFSET"])
            end = int(original["END_OFFSET"])
        except TypeError, ValueError:
            start, end = -1, -1
        answer = original["ANSWER"]
        if not answer.strip():
            reasons.append("empty_reference_answer")
        if (
            not (0 <= start < end <= len(document["text"]))
            or document["text"][start:end].strip() != answer.strip()
        ):
            reasons.append("answer_span_mismatch")
        if review and review["relevant_yes_no"] in {"no", "unsure"}:
            reasons.append("local_review_" + review["relevant_yes_no"])

        if reasons:
            exclusions.append(
                {
                    "query_id": query_id,
                    "original_document_id": document_id,
                    "source_filename": filename,
                    "reason_codes": "|".join(reasons),
                    "local_review_status": local_status,
                }
            )
            counts["excluded_answerable"] += 1
            for reason in reasons:
                counts[f"excluded_{reason}"] += 1
            continue
        qrels.append(
            {
                "query_id": query_id,
                "source_filename": filename,
                "source_text_sha256": context_hash,
                "context_id": sha256_text(filename + "\0" + expected_text),
                "relevance": 1,
                "label_source": "original_techqa_human_annotated",
                "label_status": "accepted_after_source_and_span_alignment",
                "original_document_id": document_id,
                "answer_span_start": start,
                "answer_span_end": end,
                "original_answer_sha256": sha256_text(answer),
                "local_review_status": local_status,
            }
        )
        counts["accepted_positive_qrels"] += 1
        counts[f"accepted_local_status_{local_status}"] += 1

    counts["unique_original_candidate_documents"] = len(all_candidate_ids)
    counts["candidate_documents_missing_from_adapted_corpus"] = len(
        {f"{item}.txt" for item in all_candidate_ids} - corpus_hashes.keys()
    )
    counts["original_candidate_pools_with_49_documents"] = sum(
        len(value["candidate_document_ids"]) == 49 for value in candidate_pools.values()
    )
    return qrels, exclusions, candidate_pools, dict(sorted(counts.items()))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def render_report(report: dict, exclusions: list[dict]) -> str:
    counts = report["counts"]
    lines = [
        "# DATA-003 原始人工標註對齊報告",
        "",
        f"原始資料為 [PrimeQA/TechQA](https://huggingface.co/datasets/PrimeQA/TechQA) revision `{report['original_dataset_revision']}`；NVIDIA RAG 版本為 [TechQA-RAG-Eval](https://huggingface.co/datasets/nvidia/TechQA-RAG-Eval) revision `{report['adapted_dataset_revision']}`。兩份原始檔的 SHA-256 見各自的 `data/manifests/*snapshot.json`。原始壓縮檔內 README 記載 CDLA-Permissive-1.0，NVIDIA 資料卡記載 Apache-2.0；兩個來源的授權資料分別保留。",
        "",
        "## 標註來源與判斷範圍",
        "",
        "[原始 TechQA 論文第 3.2–3.5 節](https://aclanthology.org/2020.acl-main.117.pdf)記載：問題與文件由人工標註，通過篩選的題目由兩人獨立標註，再人工裁決。原始檔保存 `QUESTION_ID`、`ANSWERABLE`、`DOCUMENT`、`DOC_IDS`、`ANSWER` 與答案字元範圍；沒有釋出逐列審核者身分或日期。因此匯出標為 `original_techqa_human_annotated`，不冒稱本專案逐列重新人工驗證。",
        "",
        "原始 `ANSWERABLE=N` 表示原始每題約 50 份 `DOC_IDS` 候選文件中未找到答案，**不代表**完整 28,481 份 NVIDIA corpus 都沒有答案。因此本輪只匯出正向、文件層級 qrels；不可回答題另保留原始候選清單，不產生全 corpus 負標籤。後續檢索指標只能稱作對已知相關文件的 Recall/MRR，不能假裝所有相關文件已列盡。",
        "",
        "## 實測結果",
        "",
        "| 指標 | 筆數 |",
        "|---|---:|",
        f"| 原始與 NVIDIA 題號、問題、答案、可回答標記對齊 | {counts['total_queries']} |",
        f"| 原始可回答題，正確文件與 NVIDIA context 對齊 | {counts['original_answerable']} |",
        f"| 答案字元範圍與文件文字不一致 | {counts['excluded_answer_span_mismatch']} |",
        f"| 因本地 AI 初審 `no` 或 `unsure` 暫排除 | {counts['excluded_local_review_no'] + counts['excluded_local_review_unsure']} |",
        f"| 匯出可追溯正向 qrels | {counts['accepted_positive_qrels']} |",
        f"| 其中另有本地使用者協助確認 | {counts.get('accepted_local_status_local_human_assisted', 0)} |",
        f"| 原始候選範圍內不可回答題 | {counts['original_unanswerable']} |",
        f"| 原始候選文件唯一 ID | {counts['unique_original_candidate_documents']} |",
        f"| 原始候選文件未收錄於 NVIDIA corpus | {counts['candidate_documents_missing_from_adapted_corpus']} |",
        "",
        f"{counts['excluded_answer_span_mismatch']} 筆答案範圍異常包含 {counts['excluded_empty_reference_answer']} 筆空參考答案；原因會重疊計數，總排除為 {counts['excluded_answerable']} 筆。原始候選文件未收錄於 NVIDIA corpus 的 ID 為 {', '.join(f'`{value}`' for value in report['candidate_document_ids_missing_from_adapted_corpus']) or '無'}，沒有正向 qrel 指向它。候選清單為 49 份的題號為 {', '.join(f'`{value}`' for value in report['candidate_pool_49_query_ids']) or '無'}，其餘為 50 份。",
        "",
        "## 排除明細",
        "",
        "| query_id | 原始文件 ID | 原因代碼 |",
        "|---|---|---|",
    ]
    for item in exclusions:
        lines.append(
            f"| `{item['query_id']}` | `{item['original_document_id']}` | `{item['reason_codes']}` |"
        )
    lines += [
        "",
        "## 產物與使用限制",
        "",
        "`data/manifests/curated_upstream_qrels.csv` 是來源人工標註再經版本、文件文字與答案範圍核對後的正向文件標註。`data/manifests/data003_exclusions.csv` 留存排除理由，`data/manifests/original_candidate_pools.json` 留存原始評估範圍。`reports/data003_labels.json` 保存計數、來源版本與各產物雜湊。完整原始檔留在 Git 排除的 `data/raw/`。",
        "",
        "這些 qrels 尚未做本專案的 train/validation/test 分組。DATA-002 必須依重複問題與共用文件分組，避免交叉洩漏；不應沿用原始 TRAIN/DEV 字樣直接當本專案切分。AI 初審只用來保守排除爭議列，未升格為人類 gold 標籤。",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    config = yaml.safe_load(Path("configs/data.yaml").read_text(encoding="utf-8"))
    revision = config["revision"]
    adapted_root = ADAPTED_ROOT / revision
    adapted_manifest = read_json(Path("data/manifests/raw_snapshot.json"))
    original_manifest = read_json(Path("data/manifests/original_techqa_snapshot.json"))
    if (
        adapted_manifest["revision"] != revision
        or original_manifest["revision"] != ORIGINAL_REVISION
    ):
        raise ValueError("Source manifests disagree with pinned revisions")
    verify_raw_files(adapted_root, adapted_manifest)
    verify_raw_files(ORIGINAL_ROOT, original_manifest)

    original_rows = read_json(ORIGINAL_ROOT / "training_Q_A.json") + read_json(
        ORIGINAL_ROOT / "dev_Q_A.json"
    )
    adapted_rows = read_json(adapted_root / "train.json")
    documents = read_json(ORIGINAL_ROOT / "training_dev_technotes.json")
    reviews = read_review(Path("reports/relevance_review.csv"))
    with zipfile.ZipFile(adapted_root / "corpus.zip") as archive:
        corpus_hashes = {
            Path(info.filename).name: hashlib.sha256(archive.read(info)).hexdigest()
            for info in archive.infolist()
            if info.filename.endswith(".txt")
        }
    qrels, exclusions, candidate_pools, counts = build_labels(
        original_rows, adapted_rows, documents, reviews, corpus_hashes
    )
    qrels_path = Path("data/manifests/curated_upstream_qrels.csv")
    exclusions_path = Path("data/manifests/data003_exclusions.csv")
    pools_path = Path("data/manifests/original_candidate_pools.json")
    write_csv(qrels_path, QREL_FIELDS, qrels)
    write_csv(exclusions_path, EXCLUSION_FIELDS, exclusions)
    write_json(pools_path, candidate_pools)
    report = {
        "schema_version": 1,
        "original_dataset_id": original_manifest["dataset_id"],
        "original_dataset_revision": ORIGINAL_REVISION,
        "original_archive_sha256": original_manifest["archive_sha256"],
        "adapted_dataset_id": adapted_manifest["dataset_id"],
        "adapted_dataset_revision": revision,
        "adapted_train_sha256": adapted_manifest["files"]["train.json"]["sha256"],
        "local_review_csv_sha256": sha256_file(Path("reports/relevance_review.csv")),
        "label_provenance": "Original TechQA human annotation team; specific per-row reviewer identities and dates were not released",
        "label_methodology": "https://aclanthology.org/2020.acl-main.117.pdf",
        "unanswerable_scope": "No answer found among each query's original DOC_IDS candidate pool; not a full-corpus negative label",
        "qrel_scope": "positive document-level labels only; known-label retrieval metrics, not exhaustive relevance",
        "counts": counts,
        "excluded_query_ids": [item["query_id"] for item in exclusions],
        "candidate_document_ids_missing_from_adapted_corpus": sorted(
            {
                doc_id
                for pool in candidate_pools.values()
                for doc_id in pool["candidate_document_ids"]
            }
            - {Path(filename).stem for filename in corpus_hashes}
        ),
        "candidate_pool_49_query_ids": sorted(
            query_id
            for query_id, pool in candidate_pools.items()
            if len(pool["candidate_document_ids"]) == 49
        ),
        "artifacts": {
            "curated_upstream_qrels.csv": sha256_file(qrels_path),
            "data003_exclusions.csv": sha256_file(exclusions_path),
            "original_candidate_pools.json": sha256_file(pools_path),
        },
    }
    write_json(Path("reports/data003_labels.json"), report)
    Path("reports/data003_labels.md").write_text(
        render_report(report, exclusions), encoding="utf-8"
    )
    print(f"aligned queries: {counts['total_queries']}")
    print(f"accepted upstream positive qrels: {counts['accepted_positive_qrels']}")
    print(f"excluded answerable records: {counts['excluded_answerable']}")
    print(
        f"original candidate-scoped unanswerable queries: {counts['original_unanswerable']}"
    )


if __name__ == "__main__":
    main()
