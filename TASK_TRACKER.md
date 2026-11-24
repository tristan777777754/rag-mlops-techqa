# TechQA RAG MLOps — Task Tracker

> 更新日期：2026-11-24  
> **目前階段：ENV-001 已驗收**
> **當前唯一任務：REPO-001**；完成後進行 `DATA-001`。
> 指令與驗收見 [`EXECUTION_GUIDE.md`](EXECUTION_GUIDE.md)。**每次開工先讀本檔。**

## Dashboard（每次結束工作務必更新）

| 欄位 | 目前內容 |
|---|---|
| Active task | `REPO-001` |
| Status | `TODO` |
| Completed | `1 / 19`（以表格任務 ID 為準） |
| Current blocker | 無；PyTorch/CUDA 待建立 Python 環境後驗證 |
| Last verified Git commit | `159a9fc1c5bf4e8d5d1f54fe16176c3cdffad7ac`（本地 clone） |
| Last passing tests | 尚無 |
| Next task after active | `DATA-001` |
| Last session summary | ENV-001 已完成環境與 Git clone 驗證，詳見 `reports/environment.md`；下一步 REPO-001 |

## 任務清單

> 將 `[ ]` 改為 `[x]` **必須附證據**。`GATE` 是決策點，不當作完成功能。請勿多個任務同時 `IN_PROGRESS`。

### Week 1：環境與資料稽核

- [x] **ENV-001** — 檢查 WSL2、GPU、Python、Docker；證據：`reports/environment.md`；驗收：列出實際版本與 GPU 可用/限制。Git clone 已驗證；PyTorch/CUDA 待後續補充。
- [ ] **REPO-001** — 建立 Git、Python 鎖檔、README、.gitignore、pytest/ruff；證據：first commit、lint/unit smoke test。
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
