"""Offline checks for the pinned dataset audit contracts."""

import copy
import csv
import json
import zipfile

import pytest

from scripts.audit_dataset import (
    audit_corpus,
    audit_records,
    prepare_review_form,
    select_review_sample,
    sha256_text,
)


def example_records():
    return [
        {
            "id": "Q1",
            "question": "How do I configure the service?",
            "answer": "Configure it in the console.",
            "is_impossible": False,
            "contexts": [
                {"filename": "guide.txt", "text": "Configure it in the console."}
            ],
        },
        {
            "id": "Q2",
            "question": "Where is the missing setting?",
            "answer": "-",
            "is_impossible": True,
            "contexts": [],
        },
    ]


def test_missing_source_field_is_rejected():
    records = example_records()
    del records[0]["contexts"]
    with pytest.raises(ValueError, match="missing fields"):
        audit_records(records)


def test_missing_nested_context_field_is_rejected():
    records = example_records()
    del records[0]["contexts"][0]["filename"]
    with pytest.raises(ValueError, match="needs filename and text"):
        audit_records(records)


def test_duplicate_ids_and_empty_contexts_are_reported():
    records = example_records()
    duplicate = copy.deepcopy(records[0])
    duplicate["question"] = "A different question"
    records.append(duplicate)
    report = audit_records(records)
    assert report["duplicate_id_entries"] == 1
    assert report["duplicate_id_groups"] == [{"id": "Q1", "count": 2}]
    assert report["empty_context_rows"] == 1
    assert report["impossible_counts"] == {"false": 2, "true": 1}


def test_audit_hashes_are_stable_across_row_order():
    records = example_records()
    first = audit_records(records)
    second = audit_records(list(reversed(records)))
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert first["context_variants"][0]["text_sha256"] == sha256_text(
        "Configure it in the console."
    )


def test_review_sample_records_provenance_without_labels():
    records = example_records()
    records[0]["answer"] = ""
    manifest, packets = select_review_sample(records)
    assert manifest["review_status"] == "pending_human_review"
    assert {entry["selection_reason"] for entry in manifest["entries"]} == {
        "targeted_empty_answer",
        "random_impossible",
    }
    assert all("reviewer" not in entry for entry in manifest["entries"])
    assert len(packets) == 2


def test_review_form_preserves_existing_assessment(tmp_path):
    manifest, _ = select_review_sample(example_records())
    form = tmp_path / "review.csv"
    revision = "a" * 40
    prepare_review_form(form, manifest, revision)
    with form.open(newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        fields = reader.fieldnames
        rows = list(reader)
    rows[0]["reviewer"] = "human-reviewer"
    with form.open("w", newline="", encoding="utf-8") as destination:
        writer = csv.DictWriter(destination, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    prepare_review_form(form, manifest, revision)
    assert "human-reviewer" in form.read_text(encoding="utf-8")


def test_corpus_match_uses_source_filename_and_content(tmp_path):
    archive_path = tmp_path / "corpus.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("corpus/guide.txt", "Configure it in the console.")
    variants = audit_records(example_records())["context_variants"]
    report = audit_corpus(archive_path, variants)
    assert report["context_variants_with_matching_content"] == 1
    assert report["missing_context_filenames"] == []
    assert report["undecodable_utf8_files"] == 0
