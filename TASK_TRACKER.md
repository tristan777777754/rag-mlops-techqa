# TechQA RAG MLOps — Task Tracker

> 更新日期：2026-11-24  
> **目前階段：ENV-001、REPO-001 已驗收**
> **當前唯一任務：DATA-001**。
> 指令與驗收見 [`EXECUTION_GUIDE.md`](EXECUTION_GUIDE.md)。**每次開工先讀本檔。**

## Dashboard（每次結束工作務必更新）

| 欄位 | 目前內容 |
|---|---|
| Active task | `DATA-001` |
| Status | `IN_PROGRESS` |
| Completed | `2 / 19`（以表格任務 ID 為準） |
| Current blocker | 無；PyTorch/CUDA 尚未驗證，資料稽核可先以 CPU 進行 |
| Last verified Git commit | `153794e1dcea187a0a2225e6a23d2342bc1a4510`（REPO-001 程式與文件） |
| Last passing tests | `uv run pytest -q`：5 passed；`uv run ruff check .` 與 `uv run ruff format --check .` 通過 |
| Next task after active | Gate A 決策後，依結果進行 `DATA-003` 或 `DATA-002` |
| Last session summary | 固定 revision 的 `train` 共 910 筆，其中 `is_impossible=true` 300 筆、空答案 2 筆、空 contexts 300 筆；完整稽核與版本化 raw snapshot 待執行 |

## 任務清單

> 將 `[ ]` 改為 `[x]` **必須附證據**。`GATE` 是決策點，不當作完成功能。請勿多個任務同時 `IN_PROGRESS`。

### Week 1：環境與資料稽核

- [x] **ENV-001** — 檢查 WSL2、GPU、Python、Docker；證據：`reports/environment.md`；驗收：列出實際版本與 GPU 可用/限制。Git clone 已驗證；PyTorch/CUDA 待後續補充。
- [x] **REPO-001** — 建立 Git、Python 鎖檔、README、.gitignore、pytest/ruff；證據：commits `f7cac19`、`464e3e4`、`153794e`，5 個 smoke tests 與 Ruff 檢查通過。
- [ ] **DATA-001** — 下載 pinned TechQA，產生 audit markdown/json、抽樣 relevance 審核；證據：`reports/dataset_audit.*`、dataset hash。
- [ ] **DATA-003**（若 Gate A 不過，必做）— 建 human-reviewed qrels 或合法獨立訓練來源；證據：label provenance 與 reviewer records。

### Week 2：資料合約與版本

- [ ] **DATA-002** — documents/queries/qrels/chunks、固定 split 與 leakage 測試；證據：`split_manifest.json` + tests。
- [ ] **DATA-004** — DVC 版本化 raw/processed；證據：`.dvc` metadata + `dvc status`。

### Week 3–4：三種 Baseline

- [ ] **EVAL-001** — retrieval metric unit tests（Recall/MRR/nDCG）；證據：pytest output。
- [ ] **RET-001** — BM25 baseline；證據：validation metrics。
- [ ] **RET-002** — Original embedding + dense baseline；證據：model/index manifest 和 metrics。
- [ ] **RET-003** — Hybrid baseline；證據：same-split comparison + case analysis。

### Week 5–6：訓練與實驗管理

- [ ] **TRAIN-001** — Embedding fine-tuning + smoke run；證據：training run、config、checkpoint、val 指標。
- [ ] **EVAL-002** — 相同 eval set 的 candidate report；證據：base vs fine-tuned 比較、品質/延遲 tradeoff。
- [ ] **OPS-001** — MLflow tracking、candidate registry、gate；證據：run ids、pass/fail gate demo。

### Week 7–8：部署與控制

- [ ] **INDEX-001** — model + vector index + chunker bundle 管理；證據：manifest/compatibility tests。
- [ ] **SERVE-001** — FastAPI `/v1/search` + health + Docker；證據：curl、OpenAPI、integration tests。
- [ ] **OPS-002** — CPU CI、stage/promote/rollback；證據：CI logs、rollback demo、bad release blocked。

### Week 9–10：監控、回饋與展示

- [ ] **MON-001** — Metrics、dashboard、受控負載；證據：Grafana/Prometheus 與實測結果。
- [ ] **MON-002** — Human-reviewed feedback；證據：feedback schema / review workflow。
- [ ] **CT-001** — candidate retraining、release gate、final demo + docs；證據：end-to-end reproducible demo。

## Gate Journal（在推進下一階段前填寫）

| Gate | 必須回答的問題 | Decision | Evidence |
|---|---|---|---|
| A — data labels | contexts 能作為 relevant evidence 嗎？weak/gold 分得清楚嗎？ | `PENDING` | — |
| B — evaluation | 無 leakage，baseline 在 fixed corpus + val qrels 上可重跑嗎？ | `PENDING` | — |
| C — release | model/index 相容、品質/安全 gate pass、人工批准嗎？ | `PENDING` | — |

## 每次 Session Log（新一筆加在最上面）

### 2026-11-24 — DATA-001 初次資料載入

- **Goal:** 用固定 revision 載入資料集並確認實際列數與來源 schema。
- **Changed files:** 使用者新增 `scripts/inspect_dataset.py`；本次更新 `README.md`、`TASK_TRACKER.md`。
- **Commands executed and actual results:** 使用者在 WSL Ubuntu 執行 `uv run python scripts/inspect_dataset.py`。Hugging Face 下載 `README.md` 與 `train.json` 至本機快取，產生 `train` split，共 910 筆。欄位為 `id`、`question`、`answer`、`is_impossible`、`contexts`。`contexts` 的 feature 為含 `filename`、`text` 兩個字串欄位的 List。使用者加上三項計數後重新執行，得到 `is_impossible=true` 300 筆、答案為空值或去除空白後為空字串 2 筆、`contexts` 為空值或空清單 300 筆。
- **Evidence:** 使用者提供的終端機輸出、`configs/data.yaml` 中固定的 revision `0b5bbc84b7f07d6d09d063130e90b716d8d4a32a`、`scripts/inspect_dataset.py`。
- **Blocker / risks:** 三個計數尚未做逐筆交叉比對，不能僅憑總數相同就認定不可回答題都沒有 contexts。其他 null、重複與 context 統計、版本化 raw snapshot、人工 relevance 審核仍待完成。Hub 提示未認證請求可能受較低速率限制，本次下載已成功。
- **Status change:** `IN_PROGRESS` 維持；DATA-001 尚未驗收。
- **Next single task:** 繼續 DATA-001 的資料品質統計與稽核報告。

### 2026-11-24 — DATA-001（進行中）

- **Goal:** 先固定 TechQA 資料集來源版本。
- **Changed files:** `configs/data.yaml`、`EXECUTION_GUIDE.md`、`TASK_TRACKER.md`。
- **Commands executed and actual results:** 在已安裝的 `huggingface-hub 2.4.0` 檢查 `HfApi.dataset_info` 簽名，確認不接受 `repo_type`；呼叫 `HfApi().dataset_info("nvidia/TechQA-RAG-Eval").sha`，回傳 `0b5bbc84b7f07d6d09d063130e90b716d8d4a32a`。
- **Evidence:** Hub API 查詢結果與 `configs/data.yaml`；修正執行指南的 API 範例。
- **Blocker / risks:** 尚未下載 pinned snapshot、核對實際列數或執行人工 relevance 審核。
- **Status change:** `TODO → IN_PROGRESS`；DATA-001 尚未驗收。
- **Next single task:** 繼續 DATA-001 的資料下載與稽核。

### 2026-11-24 — REPO-001

- **Goal:** 建立可重跑的 Python 依賴環境、專案入口與離線 smoke test。
- **Changed files:** `pyproject.toml`、`uv.lock`、`README.md`、`.gitignore`、`tests/test_smoke.py`、`TASK_TRACKER.md`。
- **Commands executed and actual results:** `uv lock --check` 解析 32 個套件；`uv sync --locked` 檢查 29 個已安裝套件；`uv run pytest -q` 為 5 passed；`uv run ruff check .` 為 All checks passed；`uv run ruff format --check .` 為 7 files already formatted；`git diff --cached --check` 通過。
- **Evidence:** commits `f7cac19`（依賴與鎖檔）、`464e3e4`（README）、`153794e`（.gitignore、README 測試命令、smoke test）；本次工具輸出。
- **Blocker / risks:** PyTorch/CUDA 尚未驗證；專案位於 Windows OneDrive 掛載路徑。DVC 任務需調整目前對 `data/raw/` 和 `data/processed/` 的排除規則。
- **Status change:** `TODO → DONE`；active task 移至 `DATA-001`（`TODO`）。
- **Next single task:** `DATA-001`。

### 2026-11-24 — ENV-001

- **Goal:** 驗證 Windows/WSL2、GPU、Python、Git、Docker 與 Compose。
- **Changed files:** `reports/environment.md`、`TASK_TRACKER.md`。
- **Commands executed and actual results:** 使用者於 Ubuntu 執行 `uname -a`、`python3 --version`、`git --version`、`nvidia-smi`、`docker version`、`docker compose version`。WSL2 可見 RTX 3060 Ti；Docker Client/Server 連通。`import torch` 回傳 `ModuleNotFoundError`。在新 clone 執行 `git remote -v`、`git status --short --branch`、`git rev-parse --show-toplevel`，確認 `origin`、`main` 與 repo 路徑。
- **Evidence:** `reports/environment.md`；本次對話提供的終端機輸出。
- **Blocker / risks:** PyTorch/CUDA 未驗證；repo 目前位於 Windows OneDrive 桌面。
- **Status change:** `TODO → DONE`；active task 移至 `REPO-001`（`TODO`）。
- **Next single task:** `REPO-001`。

### YYYY-MM-DD — <Task ID>

- **Goal:**
- **Changed files:**
- **Commands executed and actual results:**
- **Evidence:**
- **Blocker / risks:**
- **Status change:** `TODO → IN_PROGRESS / DONE / BLOCKED`
- **Next single task:**

## 新想法停車場（不插隊）

- `[P1]` Reranker fine-tuning（必要時）
- `[P1]` Generator + grounded RAG answer
- `[P2]` Kubernetes/Helm/雲端部署
- `[P2]` LangGraph multi-agent review/control layer

## Codex 使用方式

請閱讀根目錄的 `PROJECT.md`、`EXECUTION_GUIDE.md`、`AGENTS.md`、`TASK_TRACKER.md`，**只做 Dashboard 的 Active task**。結尾更新本文件，列出真實測試結果、改動檔案及下一個 task；不能假設腳本已存在或宣稱沒有執行的測試通過。
