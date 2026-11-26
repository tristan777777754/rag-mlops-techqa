import json
import os
import re
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import argparse
import pyarrow as pa
import pyarrow.parquet as pq
from huggingface_hub import hf_hub_download
from tokenizers import Tokenizer

MODEL = "sentence-transformers/all-MiniLM-L6-v2"
REVISION = "c9745ed1d9f207416be6d2e6f8de32d1f16199bf"
CHUNKER_VERSION = "techqa-minilm-200-32-v1"
MAX_BODY = 200
OVERLAP = 32
MAX_INPUT = 256

parser = argparse.ArgumentParser(description="Build DATA-002 document chunks")
parser.add_argument(
    "--input", type=Path, default=Path("data/processed/documents.parquet")
)
parser.add_argument(
    "--output", type=Path, default=Path("data/processed/chunks.parquet")
)
args = parser.parse_args()
source = args.input
output = args.output

if output.exists():
    raise FileExistsError(output)

tokenizer_path = hf_hub_download(
    repo_id=MODEL, filename="tokenizer.json", revision=REVISION
)
tokenizer = Tokenizer.from_file(tokenizer_path)
tokenizer.no_padding()
tokenizer.no_truncation()

blank_line = re.compile(r"\n[ \t]*\n")
step = re.compile(r"(?:\d+[.)]|[-*•])[ \t]+")
heading = re.compile(
    r"(?:ABSTRACT|SYMPTOMS?|CAUSE|RESOLUTION|QUESTION|ANSWER|"
    r"PROBLEM|SOLUTION|ENVIRONMENT|DIAGNOSING THE PROBLEM)[ \t]*:?[ \t]*(?:\n|$)",
    re.IGNORECASE,
)

schema = pa.schema(
    [
        ("chunk_id", pa.string()),
        ("doc_id", pa.string()),
        ("text", pa.string()),
        ("embedding_text", pa.string()),
        ("start_char", pa.int64()),
        ("end_char", pa.int64()),
        ("body_tokens", pa.int32()),
        ("embedding_tokens", pa.int32()),
        ("chunker_version", pa.string()),
    ],
    metadata={
        b"tokenizer_model": MODEL.encode(),
        b"tokenizer_revision": REVISION.encode(),
        b"tokenizer_sha256": sha256(Path(tokenizer_path).read_bytes())
        .hexdigest()
        .encode(),
        b"body_max_tokens": b"200",
        b"target_overlap_tokens": b"32",
        b"embedding_max_tokens": b"256",
        b"offsets": b"normalized parent; CRLF/CR -> LF; zero-based half-open",
    },
)


def cut_document(document):
    doc_id = document["doc_id"]
    text = document["text"].replace("\r\n", "\n").replace("\r", "\n")
    offsets = tokenizer.encode(text, add_special_tokens=False).offsets
    total = len(offsets)
    first_line = text.split("\n", 1)[0].strip()
    title = first_line if first_line.lower().startswith("title:") else ""

    def boundary(index):
        left_end = offsets[index - 1][1]
        right_start = offsets[index][0]
        gap = text[left_end:right_start]
        if not gap or not gap.isspace():
            return 0
        line_start = text.rfind("\n", 0, left_end) + 1
        if step.fullmatch(text[line_start:right_start].lstrip()):
            return 0
        if "\n" in gap and (
            heading.match(text, right_start) or step.match(text, right_start)
        ):
            return 4
        if blank_line.search(gap):
            return 3
        return 2 if text[left_end - 1] in ".!?" else 1

    start = previous_end = 0
    while start < total:
        limit = min(start + MAX_BODY, total)
        earliest = max(start + 1, previous_end + 1)
        if limit == total:
            preferred = [total]
        else:
            preferred = sorted(
                range(max(earliest, limit - 50), limit + 1),
                key=lambda index: (boundary(index), index),
                reverse=True,
            )
        candidates = dict.fromkeys(preferred + list(range(limit, earliest - 1, -1)))

        lo = offsets[start][0]
        for end in candidates:
            hi = offsets[end - 1][1]
            body = text[lo:hi]
            body_tokens = len(tokenizer.encode(body, add_special_tokens=False).ids)
            if 0 < body_tokens <= MAX_BODY:
                break
        else:
            raise ValueError(f"No valid chunk for {doc_id} at token {start}")

        embedding_text = body
        if title and not body.startswith(title):
            embedding_text = f"{title}\n\n{body}"
        embedding_tokens = len(tokenizer.encode(embedding_text).ids)
        if embedding_tokens > MAX_INPUT:
            embedding_text = body
            embedding_tokens = len(tokenizer.encode(body).ids)
        if embedding_tokens > MAX_INPUT:
            raise ValueError(f"Embedding input too long for {doc_id} at {lo}")

        chunk_key = json.dumps([CHUNKER_VERSION, doc_id, lo, hi])
        yield {
            "chunk_id": sha256(chunk_key.encode()).hexdigest(),
            "doc_id": doc_id,
            "text": body,
            "embedding_text": embedding_text,
            "start_char": lo,
            "end_char": hi,
            "body_tokens": body_tokens,
            "embedding_tokens": embedding_tokens,
            "chunker_version": CHUNKER_VERSION,
        }

        if end == total:
            return
        target = max(start + 1, end - OVERLAP)
        nearby = range(max(start + 1, target - 8), min(end - 1, target + 8) + 1)
        safe = [index for index in nearby if boundary(index) > 0]
        previous_end = end
        start = min(
            safe, key=lambda index: (abs(index - target), index), default=target
        )


documents = pq.ParquetFile(source)
document_count = chunk_count = max_body = max_input = 0
empty_documents = []
with TemporaryDirectory(dir=output.parent) as temporary:
    staged = Path(temporary) / output.name
    with pq.ParquetWriter(staged, schema, compression="zstd") as writer:
        for batch in documents.iter_batches(batch_size=128, columns=["doc_id", "text"]):
            batch_chunks = []
            for document in batch.to_pylist():
                document_count += 1
                chunks = list(cut_document(document))
                if not chunks:
                    empty_documents.append(document["doc_id"])
                    continue
                batch_chunks.extend(chunks)
                chunk_count += len(chunks)
                max_body = max(max_body, *(row["body_tokens"] for row in chunks))
                max_input = max(max_input, *(row["embedding_tokens"] for row in chunks))
            if batch_chunks:
                writer.write_table(pa.Table.from_pylist(batch_chunks, schema=schema))
            if document_count % 2048 == 0:
                print(f"Processed {document_count:,} documents", flush=True)

    if document_count != 28_481 or empty_documents:
        raise ValueError(
            f"Unexpected corpus coverage: {document_count} documents; "
            f"{len(empty_documents)} without chunks; examples: {empty_documents[:5]}"
        )
    if pq.ParquetFile(staged).metadata.num_rows != chunk_count:
        raise ValueError("Saved chunk row count does not match the generated count")
    os.link(staged, output)

print(f"Documents processed: {document_count:,}")
print(f"Chunks saved: {chunk_count:,}")
print(f"Max body tokens: {max_body}")
print(f"Max embedding tokens: {max_input}")
print(f"Saved: {output}")
