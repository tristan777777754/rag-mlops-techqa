# TechQA RAG MLOps

本專案規劃以 NVIDIA `nvidia/TechQA-RAG-Eval` 建立可重現的檢索與模型發布流程。預定先稽核資料與標註，再建立 BM25、向量及混合檢索基線，接著評估 embedding 微調、實驗追蹤與受控發布。

`REPO-001`、`DATA-001` 與 `DATA-003` 已完成。Gate A 不放行將 NVIDIA 來源 contexts 直接當成 gold labels；DATA-003 已對齊[原始 TechQA 人工標註](docs/ADR-001-original-techqa-labels.md)，匯出 595 筆正向文件標註，排除 15 筆有疑慮的可回答題。300 筆不可回答題只保留原始候選文件範圍，沒有當成整個 corpus 的負標籤。結果見 [DATA-003 報告](reports/data003_labels.md)；實際進度見 [TASK_TRACKER.md](TASK_TRACKER.md)，設計與順序見 [PROJECT.md](PROJECT.md) 和 [EXECUTION_GUIDE.md](EXECUTION_GUIDE.md)。

## 開發環境

已在 WSL2 Ubuntu 使用 Python 3.14.4 驗證基本環境，細節記錄於 [reports/environment.md](reports/environment.md)。

在 VS Code 的 PowerShell 終端機輸入 `wsl` 進入 Ubuntu。確認目前位於專案根目錄，再執行：

```bash
source ~/.local/bin/env
uv sync --locked
```

`uv sync --locked` 依照 `pyproject.toml` 和 `uv.lock` 建立 `.venv` 並安裝套件。若尚未安裝 uv，依照 [官方安裝文件](https://docs.astral.sh/uv/getting-started/installation/) 在 Ubuntu 安裝，再執行上述命令。

確認工具可用：

```bash
uv run python --version
uv run ruff --version
uv run pytest --version
```

之後執行專案 Python 程式時，使用 `uv run python ...` 以選用專案虛擬環境。執行目前的離線依賴匯入測試與程式碼檢查：

```bash
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

## 資料稽核

資料來源是 [NVIDIA TechQA-RAG-Eval](https://huggingface.co/datasets/nvidia/TechQA-RAG-Eval)，資料卡標示 Apache-2.0 授權，內容源自 [IBM TechQA](https://github.com/ibm/techqa)。`configs/data.yaml` 固定資料集 commit。於專案根目錄執行：

本次固定版本下載與雜湊驗證日期為 2026-11-25。資料卡寫 908 組問答，實際原始檔與載入結果均為 910 列；以實測為準。

```bash
uv run python scripts/audit_dataset.py
```

此命令下載該 commit 的 `train.json`、`corpus.zip`、資料卡與 `.gitattributes` 到 Git 排除的 `data/raw/`，計算來源檔 SHA-256，產生 [稽核報告](reports/dataset_audit.md)、`reports/dataset_audit.json`、`data/manifests/raw_snapshot.json` 與固定種子的 `data/manifests/relevance_review_sample.json`。人工審核表為 `reports/relevance_review.csv`，重跑稽核時會保留已填寫內容。包含原始問題、答案和 context 的審核包保存在 Git 排除的 `data/review/review_packets.json`。

執行指令會核對 pinned revision、來源 schema、原始 JSON 列數與 Datasets loader 列數。稽核報告將來源 contexts 視為待確認的 relevance 候選。原始檔案未納入 Git，其他機器可用相同 config 重新下載並核對 manifest 中的雜湊。

人工審核時，依 `query_id` 在本地審核包查 question、answer 和 contexts，將結果填入 `reports/relevance_review.csv`。可回答題判斷 context 是否切題及能否支持答案；不可回答題檢查標記是否合理，沒有 context 的兩個欄位填 `N/A`。每列填審核者與理由。判斷標準和待決事項見稽核報告的「人工審核樣本」。

37 筆樣本已填入逐筆初審結果，統計與爭議案例見 [審核摘要](reports/relevance_review_summary.md)。其中 34 筆為 AI 初審，不能視作新的人類 gold 標註。

## DATA-003：對齊原始人工標註

於 WSL 的 repo 根目錄執行：

```bash
uv run python -m scripts.extract_original_techqa
uv run python -m scripts.build_data003_labels
```

第一個命令取得固定版本的原始 TechQA 壓縮檔（約 2.96 GB），只抽出需要的問答、Technote 與授權檔到 Git 排除的 `data/raw/`。第二個命令核對兩份資料的版本、雜湊、題目、答案、正確文件及答案位置，產生 [595 筆正向 qrels](data/manifests/curated_upstream_qrels.csv)、[15 筆排除清單](data/manifests/data003_exclusions.csv)、[原始候選文件範圍](data/manifests/original_candidate_pools.json)與 [結果報告](reports/data003_labels.md)。重跑說明及限制見 [DATA-003 標註計畫](docs/DATA003_LABEL_PLAN.md)。

## DATA-002 題目切分

有固定版原始題目以及本地的 `data/processed/queries.parquet`、`qrels.parquet` 和已審查的 `near_duplicate_review.csv` 後，在 WSL 專案根目錄執行：

```bash
uv run python scripts/freeze_data002_split.py
```

此命令以 seed 42 分配 761 個群組，更新題目表的 `split`、`group_id` 並核對 [切分 manifest](data/manifests/split_manifest.json)。Train／val／test 為 638／136／136 題。審查 CSV 與 Parquet 為本地輸入，須備妥相同資料才能重跑。所有 split 共用搜尋語料。Training 與 negative mining 只使用 train 的題目與標註，validation 用於選型，test 留到最終評估。不可回答標記適用原始候選範圍，已知正向 qrels 的覆蓋也有限。

### 建立文件切塊

備妥本地 `data/processed/documents.parquet` 後，在 WSL 專案根目錄執行：

```bash
uv run python scripts/build_data002_chunks.py
```

`uv` 依鎖檔安裝 `tokenizers`。第一次執行會下載固定 MiniLM revision 的 `tokenizer.json`。輸出 `data/processed/chunks.parquet`，正文上限 200 tokens，目標重疊 32 tokens，embedding 輸入上限 256 tokens。腳本會保留既有輸出。
