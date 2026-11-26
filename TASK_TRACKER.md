# TechQA RAG MLOps — Task Tracker

> 更新日期：2026-11-26
> **目前階段：ENV-001、REPO-001、DATA-001、DATA-003、DATA-002 已完成；Gate A 對 NVIDIA 來源 contexts 直接作 gold 的使用不放行**
> **下一項任務：DATA-004**。
> 指令與驗收見 [`EXECUTION_GUIDE.md`](EXECUTION_GUIDE.md)。**每次開工先讀本檔。**

## Dashboard（每次結束工作務必更新）

| 欄位 | 目前內容 |
|---|---|
| Active task | 無 |
| Status | `DATA-002 DONE`；`DATA-004 TODO` |
| Completed | `5 / 19`（以表格任務 ID 為準） |
| Current blocker | 無；595 筆已知正向文件的覆蓋限制繼續適用 |
| Last verified Git commit | 以 `git log -1` 為準；DATA-003 程式與報告見下方 session log |
| Last passing tests | `uv run pytest -q`：18 passed；`uv run ruff check .`、`uv run ruff format --check .`、`uv lock --check` 通過 |
| Next task after active | `DATA-004`，以 DVC 版本化原始資料與正式產物 |
| Last session summary | DATA-002 完成三張資料表及 195,348 個文件切塊的重建比對 |

## 任務清單

> 將 `[ ]` 改為 `[x]` **必須附證據**。`GATE` 是決策點，不當作完成功能。請勿多個任務同時 `IN_PROGRESS`。

### Week 1：環境與資料稽核

- [x] **ENV-001** — 檢查 WSL2、GPU、Python、Docker；證據：`reports/environment.md`；驗收：列出實際版本與 GPU 可用/限制。Git clone 已驗證；PyTorch/CUDA 待後續補充。
- [x] **REPO-001** — 建立 Git、Python 鎖檔、README、.gitignore、pytest/ruff；證據：commits `f7cac19`、`464e3e4`、`153794e`，5 個 smoke tests 與 Ruff 檢查通過。
- [x] **DATA-001** — 下載 pinned TechQA，產生 audit markdown/json、抽樣 relevance 審核；證據：`reports/dataset_audit.md`、`reports/dataset_audit.json`、`data/manifests/raw_snapshot.json`、`reports/relevance_review.csv`、`reports/relevance_review_summary.md`、12 個測試通過、commits `24ebee2` 與 `49620ee`。34 筆為 AI 初審；來源標籤是否可作 gold 由 Gate A 另行判定。
- [x] **DATA-003**（`DONE`）— 對齊原始 TechQA 人工標註，建立可追溯的正向文件 qrels；證據：`data/manifests/original_techqa_snapshot.json`、`data/manifests/curated_upstream_qrels.csv`、`data/manifests/data003_exclusions.csv`、`data/manifests/original_candidate_pools.json`、`reports/data003_labels.md`、`docs/ADR-001-original-techqa-labels.md`。原始資料沒有逐列審核者身分；本地 34 筆 AI 初審只作保守排除。詳見 `docs/DATA003_LABEL_PLAN.md`。

### Week 2：資料合約與版本

- [x] **DATA-002**（`DONE`）— documents/queries/qrels/chunks 重建一致，題目切分已凍結；證據見 [切分 manifest](data/manifests/split_manifest.json)、[分組測試](tests/test_freeze_data002_split.py)及下方驗收紀錄。
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
| A — data labels | contexts 能作為 relevant evidence 嗎？weak/gold 分得清楚嗎？ | `NO_GO_SOURCE_AS_GOLD` | `reports/relevance_review.csv`、`reports/relevance_review_summary.md`：1 筆明顯不切題、3 筆不確定、2 筆空答案及 34 筆 AI 初審；不能把 NVIDIA contexts 直接當 gold。`DATA-003` 另從原始 TechQA 人工標註核對並匯出 595 筆已知正向文件 qrels，來源與限制見 `reports/data003_labels.md`。 |
| B — evaluation | 無 leakage，baseline 在 fixed corpus + val qrels 上可重跑嗎？ | `PENDING` | — |
| C — release | model/index 相容、品質/安全 gate pass、人工批准嗎？ | `PENDING` | — |

## 每次 Session Log（新一筆加在最上面）

### 2026-11-26 — DATA-002 重建驗收完成

- **Rebuild:** 使用者在 WSL 執行 `uv run python scripts/build_data002_tables.py --output-dir data/processed/rebuild_tables`，再以重建的 `documents.parquet` 作為 `scripts/build_data002_chunks.py` 的輸入，將切塊寫入同一重建目錄。
- **Validation:** 使用者提供的比對輸出顯示，28,481 份文件、910 道題目與 595 筆正向 qrels 的內容和欄位型別一致。195,348 個 chunks 通過 Arrow `equals(check_metadata=True)`，內容、順序與 metadata 一致。
- **Provenance:** 資料來源為 `nvidia/TechQA-RAG-Eval` revision `0b5bbc84b7f07d6d09d063130e90b716d8d4a32a`。凍結切分使用 seed 42，train／val／test 為 638／136／136 題。切分 manifest SHA-256 為 `74b87dc927c77cc7af1c454a16a5211fe37e850058e35a3a51a293b42c9a4ed5`。
- **Status change:** DATA-002 `IN_PROGRESS → DONE`。下一項為 DATA-004，DVC 追蹤正式產物時排除重建驗收副本 `data/processed/rebuild_tables/`。

### 2026-11-26 — DATA-002 文件切塊

- **Evidence:** 在 WSL 以 `uv run python scripts/build_data002_chunks.py` 處理 28,481 份文件，輸出 `data/processed/chunks.parquet`，共 195,348 塊。最大正文與 embedding 輸入分別為 200 與 256 tokens。MiniLM tokenizer 的固定 revision 與 SHA-256 存於 Parquet metadata。
- **Validation:** 讀回並驗證全部 chunk ID 唯一、正文與母文件 offset 一致，且涵蓋全部文件。18 個測試、Ruff 與鎖檔檢查通過。
- **Next:** DATA-002 維持進行中，待將前段正規化流程收進正式入口並完成整體驗收。

### 2026-11-26 — DATA-002 題目切分凍結

- **Evidence:** `scripts/freeze_data002_split.py` 更新本地 `queries.parquet` 並產生 `data/manifests/split_manifest.json`，SHA-256 為 `74b87dc927c77cc7af1c454a16a5211fe37e850058e35a3a51a293b42c9a4ed5`。以 seed 42 分配 761 組。Train／val／test 具正向 qrel 的題數為 417／89／89，不可回答題數為 210／45／45。
- **Validation:** WSL 重跑切分雜湊相同，反轉輸入順序結果相同，同組未跨 split。 `uv run pytest -q` 為 18 passed，Ruff lint／format 和 `uv lock --check` 通過。
- **Next:** DATA-002 維持進行中，待建 `chunks.parquet` 與整體驗收。

### 2026-11-25 — DATA-003 原始人工標註對齊完成

- **Goal:** 取得可追溯、可重建的原始 TechQA 文件級正向標註，並核對 NVIDIA 版本，保守排除異常列。
- **Changed files:** 新增 `.gitattributes`、`scripts/extract_original_techqa.py`、`scripts/build_data003_labels.py`、`tests/test_data003_labels.py`、`docs/ADR-001-original-techqa-labels.md`、`data/manifests/original_techqa_snapshot.json`、`data/manifests/curated_upstream_qrels.csv`、`data/manifests/data003_exclusions.csv`、`data/manifests/original_candidate_pools.json`、`reports/data003_labels.md`、`reports/data003_labels.json`；更新 `docs/DATA003_LABEL_PLAN.md`、`reports/relevance_review.csv`、`reports/relevance_review_summary.md`、`README.md`、`TASK_TRACKER.md`。
- **Commands executed and actual results:** 原始壓縮檔與 NVIDIA 固定版本均通過 SHA-256 核對；910 題的來源欄位一致，610 題可回答題的正確文件文字一致。11 題答案位置異常、4 題本地初審有疑慮，共排除 15 題，匯出 595 筆正向 qrels。重跑標註產物 SHA-256 完全一致，並以 `.gitattributes` 固定 Git 文字產物的 LF 換行。`uv run pytest -q` 為 17 passed；`uv run ruff check .`、`uv run ruff format --check .`、`uv lock --check`、`git diff --check` 均通過。
- **Evidence:** `reports/data003_labels.md` 和 `.json` 記錄來源版本、雜湊、逐類計數及限制；`data/manifests/data003_exclusions.csv` 記錄 15 題排除原因。原始檔在 Git 排除的 `data/raw/`。
- **Blocker / risks:** 原始資料未釋出逐列審核者資訊。595 筆僅為已知正向文件，沒有完整負標籤或本專案固定 split；300 題不可回答只適用原始候選文件範圍。不可用這些標籤直接宣稱完整 corpus 的 gold-based 評估。
- **Status change:** DATA-003 `IN_PROGRESS → DONE`；完成數 `3 / 19 → 4 / 19`。Gate A 對 NVIDIA contexts 直接作 gold 的 `NO_GO_SOURCE_AS_GOLD` 決策不變。
- **Next single task:** `DATA-002` 建立正式資料合約與文件、問題、qrels、chunks 的固定分組切分及洩漏測試。

### 2026-11-25 — Gate A 保守決策與 DATA-003 啟動

- **Goal:** 保留來源標籤的弱標籤屬性，開始建立可追溯的人工確認 qrels。
- **Changed files:** 更新 `TASK_TRACKER.md`、`README.md`；新增 `docs/DATA003_LABEL_PLAN.md`。
- **Commands executed and actual results:** 核對 DATA-001 審核摘要與執行指南。25 筆有參考答案題中 1 筆 context 明顯不切題、3 筆不確定；另有 2 筆可回答但答案空白。34 筆為 AI 初審，無法當成獨立人類驗證集。本次只更新工作文件，未執行新的資料處理程式或測試。
- **Evidence:** `reports/relevance_review.csv`、`reports/relevance_review_summary.md`；使用者於本次對話指定開始 `DATA-003`。
- **Blocker / risks:** 尚無足夠人類確認的 qrels，不能對 TechQA 聲稱有效的 gold-based retrieval 指標；不確定的題目需排除或複核。
- **Status change:** Gate A 記 `NO_GO_SOURCE_AS_GOLD`；`DATA-003` 設為 `IN_PROGRESS`，完成數仍為 `3 / 19`。
- **Next single task:** 建立每筆候選標註的來源、審核者、判斷與狀態欄位，再由人逐筆確認可採用的 qrels。

### 2026-11-25 — DATA-001 完成狀態校正

- **Goal:** 依使用者完成確認，將已交付的 DATA-001 稽核狀態記為完成。
- **Changed files:** 更新 `TASK_TRACKER.md`、`README.md`。
- **Commands executed and actual results:** 核對稽核報告、原始檔雜湊、37 筆逐筆審核表與摘要，先前 `uv run pytest -q` 為 12 passed；DATA-002 的正規化檔與 split manifest 尚未建立。
- **Evidence:** 稽核與審核交付見 DATA-001 任務列；使用者於本次對話明確確認「DATA 001 做好了」。
- **Blocker / risks:** 34 筆由 AI 初審，不能宣稱已有獨立人類 gold labels。Gate A 仍為 `PENDING`，不得直接將來源 contexts 當 gold qrels。
- **Status change:** DATA-001 `IN_PROGRESS → DONE`；完成數 `2 / 19 → 3 / 19`。Gate A 狀態不變。
- **Next single task:** 做 Gate A 書面決策，決定先進 `DATA-003` 或直接進 `DATA-002`。

### 2026-11-25 — DATA-001 抽樣 AI 初審

- **Goal:** 依問題、參考答案、來源 context 與 corpus 候選文件逐筆審核 37 筆固定抽樣。
- **Changed files:** 更新 `reports/relevance_review.csv`、`README.md`、`TASK_TRACKER.md`；新增 `reports/relevance_review_summary.md`。本地檢索輔助程式保存在 Git 排除的 `data/review/`。
- **Commands executed and actual results:** 對照 25 筆可回答題的提供文件，並對 10 筆不可回答題在 28,481 個 corpus 文件中做詞彙候選搜尋。25 筆有參考答案題的 context 切題性為 21 `yes`、1 `no`、3 `unsure`；10 筆不可回答題的標記有效性為 1 `no`、9 `unsure`；另 2 筆空答案題 context 相關但無答案可核對。重跑 `uv run python scripts/audit_dataset.py` 成功，審核 CSV 的 Git blob hash 前後同為 `2b83b70ad7f42625493f367cf92875da609241cf`，37 列及必填審核欄位均通過檢查。
- **Evidence:** `reports/relevance_review.csv` 保留每筆判斷、理由與審核者；`reports/relevance_review_summary.md` 記錄重大案例。前三筆由 Tristan 在 Codex 協助下確認，其餘 34 筆明記為 AI 初審。
- **Blocker / risks:** `DEV_Q176` 文件與問題不切題；`DEV_Q127` 雖標為不可回答，corpus 卻提供指定公告的查找連結。`TRAIN_Q196` 有修補候選但連結擷取不完整，維持不確定。AI 初審不能取代人類複核，也不能因此把來源標記當 gold label。
- **Status change:** `IN_PROGRESS` 維持，Gate A `PENDING`。
- **Next single task:** 人類複核爭議案例及樣本判斷，決定 Gate A；若錯標獲確認，進入 `DATA-003`。

### 2026-11-25 — DATA-001 固定來源與完整稽核

- **Goal:** 完成可重跑的資料、corpus 稽核與人工 relevance 抽樣準備。
- **Changed files:** 新增 `scripts/audit_dataset.py`、`tests/test_audit_dataset.py`、`data/manifests/raw_snapshot.json`、`data/manifests/relevance_review_sample.json`、`reports/dataset_audit.json`、`reports/relevance_review.csv`；更新 `reports/dataset_audit.md`、`README.md`、`.gitignore`、`pyproject.toml`、`scripts/inspect_dataset.py`（格式化）、`TASK_TRACKER.md`。
- **Commands executed and actual results:** `uv run python scripts/audit_dataset.py` 取得固定 revision `0b5bbc84b7f07d6d09d063130e90b716d8d4a32a`，驗證 `train.json` 910 列、`corpus.zip` 28,481 個檔案、496 個來源 context 版本與 corpus 同名同內容；重跑後結果一致。
- **Evidence:** 原始檔 SHA-256 與檔案大小見 `data/manifests/raw_snapshot.json`；資料品質統計見 `reports/dataset_audit.md` 和 `.json`；固定 seed 的 25 筆可回答、10 筆不可回答及 2 筆空答案異常見 `data/manifests/relevance_review_sample.json`；`reports/relevance_review.csv` 尚未填寫。
- **Blocker / risks:** 資料卡寫 908 組問答，實際 raw JSON 與 loader 都是 910 列。29 組重複問題與 2 筆可回答但空答案需審慎處理。未有人工作答，不能宣稱 context 是 gold evidence 或通過 Gate A。
- **Status change:** `IN_PROGRESS` 維持；待人工審核與 Gate A 決策。
- **Next single task:** 由人依本地 `data/review/review_packets.json` 填寫 37 筆 `reports/relevance_review.csv`，彙整支持比例與錯誤案例，再決定 Gate A。

### 2026-11-25 — DATA-001 重複群組欄位比對

- **Goal:** 檢查 29 組相同問題文字的 contexts、答案字串與不可回答標記是否一致。
- **Changed files:** 使用者更新 `scripts/inspect_dataset.py`；本次更新 `reports/dataset_audit.md`、`TASK_TRACKER.md`。
- **Commands executed and actual results:** 使用者回報 29 組逐組比較結果。20 組的 contexts 清單與 `is_impossible` 相同，其中 6 組答案字串相同、14 組不同；另 9 組 contexts、答案字串與 `is_impossible` 都不同。答案經首尾空白處理後比較，尚未審核語義是否相同。
- **Evidence:** 使用者提供的 29 行比較輸出；`reports/dataset_audit.md` 保存每組 ID 與三欄比較結果。
- **Blocker / risks:** 同一問題文字可能配上不同 context 與可回答性標記。資料切分與評估政策需考慮這些群組，答案差異原因仍待審核。
- **Status change:** `IN_PROGRESS` 維持；DATA-001 尚未驗收。
- **Next single task:** 檢查 9 組標記不同的來源記錄及 context 數量。

### 2026-11-25 — DATA-001 空答案配對 context 比對

- **Goal:** 比對兩組空答案配對的 context 來源與內容指紋。
- **Changed files:** 使用者更新 `scripts/inspect_dataset.py`；本次更新 `reports/dataset_audit.md`、`TASK_TRACKER.md`。
- **Commands executed and actual results:** 使用者回報 `TRAIN_Q285` 與 `DEV_Q094` 均指向 `swg21638268.txt`，context 文字 SHA-256 均為 `3050b46301647fd661df65fb9719c524b6e0214f65e4d656ee410936bd03440e`；`TRAIN_Q299` 與 `DEV_Q014` 均指向 `swg21138332.txt`，SHA-256 均為 `ecad2a4b2bf1565824719657565af1a68e53931d6b2f7115453ce73116f0b965`。每組問題文字亦相同，但 DEV 前綴記錄的答案為空。
- **Evidence:** 使用者提供的 `context source` 輸出與 `reports/dataset_audit.md` 中的配對表。
- **Blocker / risks:** 其餘重複群組的 context 與答案關係、空答案成因及標註政策仍待核對。資料切分時需考慮這兩組相同問題與 context 的關係。
- **Status change:** `IN_PROGRESS` 維持；DATA-001 尚未驗收。
- **Next single task:** 彙總所有重複問題群組的 context 與答案差異。

### 2026-11-25 — DATA-001 空答案配對欄位檢查

- **Goal:** 補齊空問題數與兩組空答案配對的基本欄位統計。
- **Changed files:** 使用者更新 `scripts/inspect_dataset.py`；本次更新 `reports/dataset_audit.md`、`TASK_TRACKER.md`。
- **Commands executed and actual results:** 使用者執行 `uv run python scripts/inspect_dataset.py`，回報 `empty questions: 0`、`duplicate question groups: 29`。`TRAIN_Q285`、`TRAIN_Q299` 的答案分別有 172、433 個字元，配對的 `DEV_Q094`、`DEV_Q014` 答案均為 0 字元。四筆的 `is_impossible` 都是 `False`，每筆有 1 個 context。
- **Evidence:** 使用者提供的完整終端機輸出與 `reports/dataset_audit.md` 的更新表格。
- **Blocker / risks:** 尚未比較四筆的 context 檔名與內容，來源答案缺失原因仍待核對。其他欄位 null、context 分布、版本化 raw snapshot 與人工 relevance 審核仍待完成。
- **Status change:** `IN_PROGRESS` 維持；DATA-001 尚未驗收。
- **Next single task:** 比對兩組空答案配對的 context 來源與內容雜湊。

### 2026-11-25 — DATA-001 重複問題群組

- **Goal:** 保存正規化問題文字相同的來源 ID 群組，供後續資料切分檢查。
- **Changed files:** 使用者更新 `scripts/inspect_dataset.py`；本次新增 `reports/dataset_audit.md` 並更新 `TASK_TRACKER.md`。
- **Commands executed and actual results:** 使用者依正規化問題文字分組，提供 29 行群組輸出，每組有兩個不同 ID。依字面前綴整理，TRAIN / DEV 22 組、TRAIN / TRAIN 6 組、DEV / DEV 1 組。兩筆空答案 `DEV_Q014`、`DEV_Q094` 分別與 `TRAIN_Q299`、`TRAIN_Q285` 位於同一問題群組。
- **Evidence:** 使用者提供的 29 組 ID、`scripts/inspect_dataset.py` 中的分組程式、`reports/dataset_audit.md` 的完整清單。
- **Blocker / risks:** 尚未收到 `empty questions` 與 `duplicate question groups` 兩行總數輸出；目前清單有 29 組。ID 前綴的原始切分語義、群組答案與 contexts 的關係、近似重複問題及共享文件仍待核對。
- **Status change:** `IN_PROGRESS` 維持；DATA-001 尚未驗收。
- **Next single task:** 檢查重複群組中答案與 contexts 的對應關係，繼續 DATA-001 稽核。

### 2026-11-25 — DATA-001 問題文字重複計數

- **Goal:** 檢查不同來源 ID 是否對應重複的問題文字。
- **Changed files:** 使用者更新 `scripts/inspect_dataset.py`；本次更新 `TASK_TRACKER.md`。
- **Commands executed and actual results:** 使用者以 `casefold()`、`split()` 和空白重新連接來正規化 910 筆 `question`，再計算 `len(questions) - len(set(questions))`，回報 `duplicate question entries: 29`。此數字表示正規化後超出不同文字數量的筆數，尚未列出重複群組。
- **Evidence:** 使用者提供的終端機輸出、`scripts/inspect_dataset.py` 中的正規化與計數、固定資料集 revision `0b5bbc84b7f07d6d09d063130e90b716d8d4a32a`。
- **Blocker / risks:** 尚未確認 29 筆是否包含空問題、涉及幾組重複文字、對應哪些來源 ID 或 context。資料切分前需釐清這些重複關係。
- **Status change:** `IN_PROGRESS` 維持；DATA-001 尚未驗收。
- **Next single task:** 列出重複問題群組的來源 ID，繼續 DATA-001 稽核。

### 2026-11-25 — DATA-001 空答案與 ID 檢查

- **Goal:** 找出 2 筆空答案的來源 ID 與可回答性標記，並檢查來源 ID 唯一性。
- **Changed files:** 使用者更新 `scripts/inspect_dataset.py`；本次更新 `TASK_TRACKER.md`。
- **Commands executed and actual results:** 使用者重新執行檢查腳本，回報 `DEV_Q014`、`DEV_Q094` 的 `answer` 為空值或空白字串，兩筆的 `is_impossible` 都是 `False`。接著用 `len(ids) - len(set(ids))` 檢查 910 筆來源 ID，回報 `duplicate ID entries: 0`。
- **Evidence:** 使用者提供的終端機輸出、`scripts/inspect_dataset.py` 中的空答案 ID 檢查、固定資料集 revision `0b5bbc84b7f07d6d09d063130e90b716d8d4a32a`。
- **Blocker / risks:** 兩筆資料的標記與空答案並存，原因與後續處理方式待人工核對。問題文字重複、其他資料品質統計、版本化 raw snapshot 與人工 relevance 審核仍待完成。
- **Status change:** `IN_PROGRESS` 維持；DATA-001 尚未驗收。
- **Next single task:** 繼續 DATA-001 的資料品質稽核。

### 2026-11-25 — DATA-001 不可回答題交叉比對

- **Goal:** 確認 `is_impossible=true` 與空 contexts 的 300 筆是否為同一批資料。
- **Changed files:** 使用者更新 `scripts/inspect_dataset.py`；本次更新 `TASK_TRACKER.md`。
- **Commands executed and actual results:** 使用者重新執行檢查腳本，回報 `impossible and empty contexts: 300`、`answerable but empty contexts: 0`。結合先前實測的 `impossible: 300` 與 `empty contexts: 300`，確認在此固定 snapshot 中，空 contexts 恰好對應所有標為不可回答的題目。
- **Evidence:** 使用者提供的終端機輸出、`scripts/inspect_dataset.py` 中的兩項交叉計數、`configs/data.yaml` 中的固定 revision。
- **Blocker / risks:** `is_impossible` 是來源標記，尚未審核其語義與答案支持情形；其他 null、重複、context 統計及版本化 raw snapshot 仍待完成。
- **Status change:** `IN_PROGRESS` 維持；DATA-001 尚未驗收。
- **Next single task:** 繼續 DATA-001 的資料品質稽核。

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
