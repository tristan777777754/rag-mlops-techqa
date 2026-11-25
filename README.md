# TechQA RAG MLOps

本專案規劃以 NVIDIA `nvidia/TechQA-RAG-Eval` 建立可重現的檢索與模型發布流程。預定先稽核資料與標註，再建立 BM25、向量及混合檢索基線，接著評估 embedding 微調、實驗追蹤與受控發布。

`REPO-001` 專案環境建置與 `DATA-001` 資料稽核已完成。固定版本的原始資料、corpus、稽核報告及 37 筆抽樣審核紀錄已保存；其中 34 筆為 AI 初審。來源標籤能否用於可信評估，仍待 Gate A 決策。實際進度請看 [TASK_TRACKER.md](TASK_TRACKER.md)，設計與執行順序請看 [PROJECT.md](PROJECT.md) 和 [EXECUTION_GUIDE.md](EXECUTION_GUIDE.md)。

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

執行指令會核對 pinned revision、來源 schema、原始 JSON 列數與 Datasets loader 列數。人工審核欄位目前留空；稽核報告將來源 contexts 視為待確認的 relevance 候選。原始檔案未納入 Git，其他機器可用相同 config 重新下載並核對 manifest 中的雜湊。

人工審核時，依 `query_id` 在本地審核包查 question、answer 和 contexts，將結果填入 `reports/relevance_review.csv`。可回答題判斷 context 是否切題及能否支持答案；不可回答題檢查標記是否合理，沒有 context 的兩個欄位填 `N/A`。每列填審核者與理由。判斷標準和待決事項見稽核報告的「人工審核樣本」。

37 筆樣本已填入逐筆初審結果，統計與爭議案例見 [審核摘要](reports/relevance_review_summary.md)。其中 34 筆為 AI 初審，仍需人類複核後才能決定 Gate A。
