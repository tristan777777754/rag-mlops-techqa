"""Offline checks for original-label alignment and conservative qrel export."""

import hashlib
import io
import tarfile

import pytest

from scripts import extract_original_techqa
from scripts.audit_dataset import sha256_text
from scripts.build_data003_labels import build_labels


def fixture_rows():
    text = "Title: Support note\n\nText:\nThe setting is enabled."
    original = [
        {
            "QUESTION_ID": "Q1",
            "QUESTION_TITLE": "Is it enabled?",
            "QUESTION_TEXT": " Check the setting.",
            "ANSWERABLE": "Y",
            "ANSWER": "enabled",
            "DOCUMENT": "doc1",
            "DOC_IDS": ["doc1", "doc2"],
            "START_OFFSET": "15",
            "END_OFFSET": "22",
        },
        {
            "QUESTION_ID": "Q2",
            "QUESTION_TITLE": "Is it missing?",
            "QUESTION_TEXT": " Check the setting.",
            "ANSWERABLE": "N",
            "ANSWER": "-",
            "DOCUMENT": "-",
            "DOC_IDS": ["doc1", "doc2"],
            "START_OFFSET": "-",
            "END_OFFSET": "-",
        },
    ]
    adapted = [
        {
            "id": "Q1",
            "question": "Is it enabled? Check the setting.",
            "answer": "enabled",
            "is_impossible": False,
            "contexts": [{"filename": "doc1.txt", "text": text}],
        },
        {
            "id": "Q2",
            "question": "Is it missing? Check the setting.",
            "answer": "-",
            "is_impossible": True,
            "contexts": [],
        },
    ]
    documents = {
        "doc1": {
            "id": "doc1",
            "title": "Support note",
            "text": "The setting is enabled.",
        }
    }
    corpus = {"doc1.txt": sha256_text(text), "doc2.txt": "unused"}
    return original, adapted, documents, corpus


def test_accepted_label_keeps_original_human_provenance_and_no_impossible_negative():
    original, adapted, documents, corpus = fixture_rows()
    qrels, exclusions, pools, counts = build_labels(
        original, adapted, documents, {}, corpus
    )
    assert len(qrels) == 1
    assert qrels[0]["query_id"] == "Q1"
    assert qrels[0]["label_source"] == "original_techqa_human_annotated"
    assert qrels[0]["relevance"] == 1
    assert exclusions == []
    assert pools["Q2"]["original_answerable"] is False
    assert counts["original_unanswerable"] == 1


def test_bad_answer_span_and_local_uncertainty_are_excluded():
    original, adapted, documents, corpus = fixture_rows()
    original[0]["START_OFFSET"] = "0"
    review = {
        "Q1": {"reviewer": "Codex (AI preliminary review)", "relevant_yes_no": "unsure"}
    }
    qrels, exclusions, _, counts = build_labels(
        original, adapted, documents, review, corpus
    )
    assert qrels == []
    assert "answer_span_mismatch" in exclusions[0]["reason_codes"]
    assert "local_review_unsure" in exclusions[0]["reason_codes"]
    assert counts["excluded_answerable"] == 1


def test_changed_adapted_document_is_rejected():
    original, adapted, documents, corpus = fixture_rows()
    adapted[0]["contexts"][0]["text"] += " altered"
    with pytest.raises(ValueError, match="document text differ"):
        build_labels(original, adapted, documents, {}, corpus)


def test_missing_corpus_positive_is_rejected():
    original, adapted, documents, _ = fixture_rows()
    with pytest.raises(ValueError, match="Pinned corpus document differs"):
        build_labels(original, adapted, documents, {}, {})


def test_archive_extraction_uses_exact_expected_paths(tmp_path, monkeypatch):
    members = {
        "TechQA/README.txt": b"Community Data License Agreement - Permissive - Version 1.0",
        "TechQA/CDLA-Permissive-v1.0.pdf": b"license",
        "TechQA/technote_corpus/CDLA-Permissive-v1.0.pdf": b"other license",
        "TechQA/training_and_dev/training_Q_A.json": b"[]",
        "TechQA/training_and_dev/dev_Q_A.json": b"[]",
        "TechQA/training_and_dev/training_dev_technotes.json": b"{}",
    }
    archive_path = tmp_path / "original.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        for name, content in members.items():
            member = tarfile.TarInfo(name)
            member.size = len(content)
            archive.addfile(member, io.BytesIO(content))
    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    monkeypatch.setattr(extract_original_techqa, "ARCHIVE_SHA256", digest)
    output = tmp_path / "extracted"
    manifest = extract_original_techqa.extract_pinned_files(archive_path, output)
    assert len(manifest["files"]) == 5
    assert (output / "CDLA-Permissive-v1.0.pdf").read_bytes() == b"license"
    assert manifest == extract_original_techqa.extract_pinned_files(
        archive_path, output
    )
