# DATA-003：建立可信的檢索標註

**狀態：規劃中，尚未產生 gold qrels。** 來源為固定的 `nvidia/TechQA-RAG-Eval` revision `0b5bbc84b7f07d6d09d063130e90b716d8d4a32a`。Gate A 已決定不直接把來源 `contexts` 當 gold label；本任務先走「人類確認小型 qrels」路徑。若無法取得足夠可信的確認結果，再評估另有授權且具清楚標註來源的資料集。

## 這個任務要產生什麼

`qrels` 是「某個問題與某份文件是否相關」的逐對紀錄。DATA-001 的 `reports/relevance_review.csv` 是 **審核草稿**：37 筆中 34 筆是 AI 初審，不能自動升格為 `human_verified`。DATA-003 需要將確認過的判斷獨立保存，留下來源、審核者與判斷理由。之後 DATA-002 才把來源文件映射成正式 `doc_id`、固定資料切分與 `qrels.parquet`。

## 預定的標註紀錄

每一列對應一個 `(query_id, source_filename, source_text_sha256)`，至少記：

| 欄位 | 用途 |
|---|---|
| `dataset_revision`, `raw_train_sha256` | 固定問題與文件的來源版本 |
| `query_id`, `source_filename`, `source_text_sha256` | 可重建的問題與文件對應；正式 `doc_id` 由 DATA-002 產生 |
| `relevance` | `1` 相關、`0` 不相關；不確定先不寫入正式 qrels |
| `label_source`, `review_status` | 區分 `source_context`、`ai_suggested`、`human_verified` 及草稿／已確認 |
| `reviewer`, `review_reason`, `reviewed_at` | 誰在何時依什麼證據確認 |

不可回答題沒有來源 context，須另行記錄題目層級的 `is_impossible` 審核；不能虛構 `(query_id, doc_id, relevance=0)` 代表整個 corpus 都不相關。某份文件沒被抽到，也不能直接算負例。

## 執行順序

1. 從現有 37 筆審核草稿開始。先複核 `DEV_Q176`、`DEV_Q067`、`DEV_Q110`、`TRAIN_Q162`、`DEV_Q127`、`TRAIN_Q196`，保留無法確認的 `unsure`。
2. 對明確的問題與文件配對記錄文件中的支持片段、審核者與判斷理由。技術細節無法判斷時保留草稿，找具領域知識的人複核，或改用具獨立標註的資料來源。
3. 寫小型匯入程式與測試，驗證來源 SHA、ID、文件內容指紋、重複鍵及標註狀態。只有 `human_verified` 且判斷明確的列可輸出到 gold qrels；AI 初審與來源 context 可另存為弱標籤。
4. 產生標註數量、爭議案例與排除理由的報告。完成後交給 DATA-002 建正式資料表與固定 split；測試集不可由 AI 初審或未確認的弱標籤冒充 gold。

**驗收依據：** 可追溯的人工確認紀錄、來源版本與文件指紋、明確的排除清單、驗證測試，以及清楚區分 gold 與 weak labels 的匯出結果。尚未完成這些項目前，DATA-003 保持 `IN_PROGRESS`。
