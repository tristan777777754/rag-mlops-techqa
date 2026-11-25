# DATA-003：可信檢索標註

**狀態：DONE。** 本任務使用原始 TechQA 已由人類標註的文件 ID 與答案位置，對齊目前固定的 NVIDIA RAG 版本，再保守排除不一致或本地初審有疑慮的資料。完整實測見 `reports/data003_labels.md`，設計決策見 `docs/ADR-001-original-techqa-labels.md`。

## 為什麼使用原始標註

DATA-001 的 37 筆本地審核中，有 34 筆是 AI 初審，不能稱為新的人類 gold labels。原始 TechQA 論文記錄了人工標註與裁決流程；原始問答檔保留每題的正確文件 `DOCUMENT`、候選文件 `DOC_IDS` 和答案字元位置。原始壓縮檔與 NVIDIA 版本均固定 revision 並記錄 SHA-256。程式驗證 910 筆題號、問題、答案、可回答標記及正向文件對齊，對 610 筆可回答題逐字核對文件文字。

## 交付

| 檔案 | 用途 |
|---|---|
| `data/manifests/original_techqa_snapshot.json` | 原始壓縮檔及抽出檔案的版本、大小、SHA-256 與來源授權紀錄 |
| `data/manifests/curated_upstream_qrels.csv` | 595 筆來源人工標註、經文件與答案範圍核對的正向文件 qrels |
| `data/manifests/data003_exclusions.csv` | 15 筆未採用的可回答題及排除原因 |
| `data/manifests/original_candidate_pools.json` | 910 題原始候選文件範圍，供解讀不可回答標記 |
| `reports/data003_labels.md`、`.json` | 統計、來源說明、限制與產物雜湊 |

每筆 qrel 有 `query_id`、原始文件 ID、來源檔名、文件內容 SHA-256、答案範圍、`label_source` 和本地審核狀態。`label_source=original_techqa_human_annotated` 表示原始資料的人類標註；原始檔未提供逐列審核者姓名或日期，故未捏造。`local_review_status` 區分使用者協助確認、AI 初審與未抽樣；AI 初審只用來排除有疑慮的列，沒有升格為人類標註。

300 筆 `ANSWERABLE=N` 只表示原始候選文件中沒有找到答案；本任務沒有將其轉為完整 corpus 的負標籤。輸出的正向 qrels 是文件層級且可能不完整，之後只能評估「已知相關文件」的檢索表現。

## 重跑

在 repo 根目錄的 WSL 環境執行：

```bash
uv run python -m scripts.extract_original_techqa
uv run python -m scripts.build_data003_labels
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

第一個命令會下載約 2.96 GB 的固定原始壓縮檔到 Hugging Face 快取，只把本任務需要的問答、Technote 與授權檔抽至 Git 排除的 `data/raw/`。第二個命令驗證兩份來源檔雜湊與內容對應，再重建 CSV、JSON 及報告。DATA-002 接著需要建立正式 `doc_id`、固定 split 與防洩漏測試；不可直接把原始 TRAIN/DEV 前綴當本專案的 train/test 切分。
