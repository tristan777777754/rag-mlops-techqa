# DATA-003 原始人工標註對齊報告

原始資料為 [PrimeQA/TechQA](https://huggingface.co/datasets/PrimeQA/TechQA) revision `60437bc79ab217679682217598a3693cab78365b`；NVIDIA RAG 版本為 [TechQA-RAG-Eval](https://huggingface.co/datasets/nvidia/TechQA-RAG-Eval) revision `0b5bbc84b7f07d6d09d063130e90b716d8d4a32a`。兩份原始檔的 SHA-256 見各自的 `data/manifests/*snapshot.json`。原始壓縮檔內 README 記載 CDLA-Permissive-1.0，NVIDIA 資料卡記載 Apache-2.0；兩個來源的授權資料分別保留。

## 標註來源與判斷範圍

[原始 TechQA 論文第 3.2–3.5 節](https://aclanthology.org/2020.acl-main.117.pdf)記載：問題與文件由人工標註，通過篩選的題目由兩人獨立標註，再人工裁決。原始檔保存 `QUESTION_ID`、`ANSWERABLE`、`DOCUMENT`、`DOC_IDS`、`ANSWER` 與答案字元範圍；沒有釋出逐列審核者身分或日期。因此匯出標為 `original_techqa_human_annotated`，不冒稱本專案逐列重新人工驗證。

原始 `ANSWERABLE=N` 表示原始每題約 50 份 `DOC_IDS` 候選文件中未找到答案，**不代表**完整 28,481 份 NVIDIA corpus 都沒有答案。因此本輪只匯出正向、文件層級 qrels；不可回答題另保留原始候選清單，不產生全 corpus 負標籤。後續檢索指標只能稱作對已知相關文件的 Recall/MRR，不能假裝所有相關文件已列盡。

## 實測結果

| 指標 | 筆數 |
|---|---:|
| 原始與 NVIDIA 題號、問題、答案、可回答標記對齊 | 910 |
| 原始可回答題，正確文件與 NVIDIA context 對齊 | 610 |
| 答案字元範圍與文件文字不一致 | 11 |
| 因本地 AI 初審 `no` 或 `unsure` 暫排除 | 4 |
| 匯出可追溯正向 qrels | 595 |
| 其中另有本地使用者協助確認 | 3 |
| 原始候選範圍內不可回答題 | 300 |
| 原始候選文件唯一 ID | 28461 |
| 原始候選文件未收錄於 NVIDIA corpus | 1 |

11 筆答案範圍異常包含 2 筆空參考答案；原因會重疊計數，總排除為 15 筆。原始候選文件未收錄於 NVIDIA corpus 的 ID 為 `swg21407330`，沒有正向 qrel 指向它。候選清單為 49 份的題號為 `DEV_Q177`，其餘為 50 份。

## 排除明細

| query_id | 原始文件 ID | 原因代碼 |
|---|---|---|
| `DEV_Q014` | `swg21138332` | `empty_reference_answer|answer_span_mismatch` |
| `DEV_Q029` | `swg21496354` | `answer_span_mismatch` |
| `DEV_Q038` | `swg21451229` | `answer_span_mismatch` |
| `DEV_Q067` | `swg21615427` | `local_review_unsure` |
| `DEV_Q094` | `swg21638268` | `empty_reference_answer|answer_span_mismatch` |
| `DEV_Q110` | `swg21220832` | `local_review_unsure` |
| `DEV_Q129` | `swg21962588` | `answer_span_mismatch` |
| `DEV_Q156` | `swg21998655` | `answer_span_mismatch` |
| `DEV_Q160` | `swg21163875` | `answer_span_mismatch` |
| `DEV_Q176` | `swg21578744` | `local_review_no` |
| `DEV_Q180` | `swg21964873` | `answer_span_mismatch` |
| `DEV_Q291` | `swg21639640` | `answer_span_mismatch` |
| `DEV_Q300` | `swg21438047` | `answer_span_mismatch` |
| `DEV_Q303` | `swg21690658` | `answer_span_mismatch` |
| `TRAIN_Q162` | `swg24041394` | `local_review_unsure` |

## 產物與使用限制

`data/manifests/curated_upstream_qrels.csv` 是來源人工標註再經版本、文件文字與答案範圍核對後的正向文件標註。`data/manifests/data003_exclusions.csv` 留存排除理由，`data/manifests/original_candidate_pools.json` 留存原始評估範圍。`reports/data003_labels.json` 保存計數、來源版本與各產物雜湊。完整原始檔留在 Git 排除的 `data/raw/`。

這些 qrels 尚未做本專案的 train/validation/test 分組。DATA-002 必須依重複問題與共用文件分組，避免交叉洩漏；不應沿用原始 TRAIN/DEV 字樣直接當本專案切分。AI 初審只用來保守排除爭議列，未升格為人類 gold 標籤。
