# DATA-001 抽樣審核摘要

固定來源、seed 與樣本 ID 見 `data/manifests/relevance_review_sample.json`。逐筆判斷、理由及審核者記於 `reports/relevance_review.csv`。本摘要根據 2026-11-25 的 CSV 狀態編寫。

## 審核範圍與來源

共 37 筆：25 筆來源標為可回答且有參考答案、10 筆來源標為不可回答、2 筆可回答但參考答案為空的異常。`DEV_Q019`、`TRAIN_Q221`、`TRAIN_Q411` 由 Tristan 在 Codex 協助下確認；其餘 34 筆由 Codex 做 **AI 初審**。AI 初審不能冒充獨立的人工作答，也不能單獨完成 Gate A 所需的人類審核。

`relevant_yes_no` 判斷 context 是否能回應問題；`answer_supported` 判斷 context 是否包含並支持來源的參考答案。兩者分開記錄，因此答案字句出現在文件中，不代表它回答了問題。不可回答題沒有來源 context，前兩欄記 `N/A`；`impossible_label_valid` 表示 corpus 搜尋能否支持或反駁來源的不可回答標記。詞彙搜尋未找到文件，不能證明沒有答案。

| 類別 | 結果 |
|---|---|
| 25 筆有參考答案題的 context 切題性 | `yes` 21、`no` 1、`unsure` 3 |
| 25 筆有參考答案題的參考答案支持度 | `yes` 25；此欄僅表示提供的文件有支持參考答案，不能推論答案對原問題充分 |
| 10 筆不可回答題的來源標記有效性 | `no` 1、`unsure` 9 |
| 2 筆空答案異常 | context 與問題相關；因參考答案空白，支持度為 `N/A` |

## 需要複核的案例

| ID | 初審判斷與依據 |
|---|---|
| `DEV_Q176` | **不切題。** 問題問 WebSphere Extreme Scale 的「閏秒」，文件談 WebSphere Application Server 的「閏年」。參考答案雖逐字出現在文件中，仍沒有回答原問題。 |
| `DEV_Q067` | **不確定。** 文件給出 LDAP `connectTimeout` 設定，但問題描述啟動時的 group replication lock；未確認兩者為同一故障。 |
| `DEV_Q110` | **不確定。** 文件提供清除連線池命令，未直接說明資料庫伺服器套用 Microsoft 修補後 WAS 掛住的原因。 |
| `TRAIN_Q162` | **不確定。** 文件談 PI50993 修補後的 `NoClassDefFoundError`，問題描述 `VerifyError`；是否同一原因需專業複核。 |
| `TRAIN_Q196` | **不確定。** corpus 的 `swg22014367.txt` 是同一 CVE-2017-3735 公告，並有 MQ 8 的 `REMEDIATION/FIXES` 段落；但擷取後只留下「here」，沒有具體修補連結或版本，尚不足以回答具體修補方法。 |
| `DEV_Q020` | **不確定。** corpus 的 `swg24041964.txt` 提供 WAS 8.5.5.3 ODR OOM 修補候選，但文件所述觸發條件與問題不完全相同。 |
| `DEV_Q127` | **不可回答標記疑似有誤。** 問題只問在哪裡找到指定安全公告，而 corpus 的 `swg21700720.txt` 列出該公告的完整名稱與連結。外部公告全文不在 corpus，但文件已提供查找位置。 |
| `DEV_Q014`、`DEV_Q094` | **空答案異常。** 兩題來源標為可回答且有相關 context，但參考答案為空；不可將其直接用作有答案的訓練或評估樣本。 |

## Gate A 建議

這批 AI 初審已找到一筆明顯不切題 context、一筆不可回答標記反例，以及兩筆空參考答案。**暫不將來源 contexts 升格為 gold qrels，也不將來源 `is_impossible` 當成已驗證的真值。** Gate A 維持 `PENDING`；由人複核爭議案例、確認抽樣判斷後，再記錄最後決策。若錯標獲確認，依執行指南進行 `DATA-003`，建立人審 qrels 或其他有來源依據的訓練資料。
