# ADR-001：使用原始 TechQA 人工標註建立文件 qrels

- **狀態：** Accepted，2026-11-25
- **範圍：** DATA-003 的標註來源；不決定 DATA-002 的 train/validation/test 切分。

## 背景

NVIDIA RAG 版本的 `contexts` 只留下對應的文件文字，未附原始標註者、候選文件清單或答案位置。DATA-001 本地抽樣有 34 筆 AI 初審，不能冒充新的人類 gold 標註。使用來源 `contexts` 直接當 gold 的 Gate A 決策是 `NO_GO_SOURCE_AS_GOLD`。

[原始 TechQA 論文](https://aclanthology.org/2020.acl-main.117.pdf)第 3.2–3.5 節記載兩位標註者獨立標註與人工裁決，原始問答檔包含正確文件 ID、候選文件 ID 和答案字元範圍。原始資料包從固定的 [PrimeQA/TechQA](https://huggingface.co/datasets/PrimeQA/TechQA) revision 取得；壓縮檔內 README 記載 CDLA-Permissive-1.0。NVIDIA 版本資料卡標示 Apache-2.0；兩份資料的授權紀錄分別保存，沒有把鏡像的授權說法套在原始包上。

## 決策

1. 原始人類標註作為 **upstream human annotation**，與本專案新的人類複核分開命名。原始檔未提供逐列審核者姓名或日期，報告明寫這個限制。
2. 僅在原始與 NVIDIA 的題號、問題、答案、可回答標記、正確文件 ID、文件文字、答案字元範圍，以及 NVIDIA corpus 檔案雜湊全部對齊時，輸出正向文件 qrel。對本地初審為 `no` 或 `unsure` 的題目保守排除，不能將 AI 判斷升格為 gold。
3. `ANSWERABLE=N` 僅描述原始每題的 `DOC_IDS` 候選清單。保留候選清單，沒有答案的題目不產生整個 corpus 的負 qrel。
4. 使用 595 筆核對後的正向文件 qrels 作為後續 **known-label** 檢索評估基礎；15 筆例外另列原因。DATA-002 需依重複問題及文件關係重新分組並固定 split。

## 已驗證結果與限制

- 910 筆原始與 NVIDIA 問答欄位對齊；610 筆可回答題的正確文件文字完全相同。
- 11 筆答案範圍不吻合原始文件，其中 2 筆參考答案空白；另有 4 筆本地初審 `no` 或 `unsure`，共排除 15 筆。
- 原始 300 筆不可回答題的候選文件清單已保存；其中一題列 49 份，其餘列 50 份。NVIDIA corpus 少了原始候選文件 `swg21407330`，無正向 qrel 指向該檔。
- 595 筆是原始人工標註經來源對齊後的 **已知正向文件**，未證明所有其他文件均不相關，也不是 chunk 層級標註。任何 Recall/MRR 結果必須註明已知標註範圍。
