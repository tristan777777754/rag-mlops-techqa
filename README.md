# TechQA RAG MLOps

本專案規劃以 NVIDIA `nvidia/TechQA-RAG-Eval` 建立可重現的檢索與模型發布流程。預定先稽核資料與標註，再建立 BM25、向量及混合檢索基線，接著評估 embedding 微調、實驗追蹤與受控發布。

`REPO-001` 專案環境建置已完成，下一項任務是 `DATA-001` 資料稽核。資料下載、檢索基線、模型訓練與服務尚未實作。實際進度請看 [TASK_TRACKER.md](TASK_TRACKER.md)，設計與執行順序請看 [PROJECT.md](PROJECT.md) 和 [EXECUTION_GUIDE.md](EXECUTION_GUIDE.md)。

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

資料稽核命令會在 `DATA-001` 實作後加入。
