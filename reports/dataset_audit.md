# DATA-001 資料稽核

來源為 NVIDIA `nvidia/TechQA-RAG-Eval`，revision `0b5bbc84b7f07d6d09d063130e90b716d8d4a32a`。
資料卡標示授權為 `apache-2.0`。來源標註與 context 關聯尚待人工審核。
固定版本資料卡記載 908 組問答；本次原始 `train.json` 與 Datasets loader 均為 910 列。以下統計以原始檔實測為準。

## 來源與完整性

原始 `train.json` SHA-256 為 `69d97231509482ed6bd5ec1c4bc0607acb82a88d11169eb8383592d0ca8b93c7`。
`corpus.zip` SHA-256 為 `c06aa287dcc1abf8db6b49b8495df095db73342d729f6451ac330785245d10be`。
其餘來源檔的大小與雜湊見 `data/manifests/raw_snapshot.json`。原始檔保存在 `data/raw/`，由 Git 排除。

## 資料列統計

| 指標 | 實測結果 |
|---|---:|
| `train` 列數 | 910 |
| 唯一 ID | 910 |
| 重複 ID 額外筆數 | 0 |
| `is_impossible=true` | 300 |
| `is_impossible=false` | 610 |
| 空問題 | 0 |
| 空答案 | 2 |
| 空 contexts | 300 |
| 正規化問題文字重複群組 | 29 |
| 近似問題候選配對 | 39 |
| context 出現次數 | 610 |
| 唯一 context 檔名 | 496 |
| 唯一 context 文字 SHA-256 | 496 |
| 多題共用的 context 版本 | 88 |

空答案 ID 為 `DEV_Q014`, `DEV_Q094`。
問題正規化採 Unicode casefold、移除多餘空白。近似問題候選使用不同問題文字的 token set Jaccard >= 0.9，屬於待人工確認的候選。

來源欄位及巢狀型別由 pinned snapshot 的 Datasets loader 驗證。實際 features 如下。
前兩筆的遮罩欄位樹記於 JSON 報告的 `first_two_masked_field_trees`，僅保留型別、長度與雜湊。

`{'id': Value('string'), 'question': Value('string'), 'answer': Value('string'), 'is_impossible': Value('bool'), 'contexts': List({'filename': Value('string'), 'text': Value('string')})}`

| 欄位 | null 筆數 |
|---|---:|
| `answer` | 0 |
| `contexts` | 0 |
| `id` | 0 |
| `is_impossible` | 0 |
| `question` | 0 |

## 文件與 context

| 長度分布 | 最小 | 中位數 | p95 | 最大 |
|---|---:|---:|---:|---:|
| 每題 context 數 | 0 | 1.0 | 1 | 1 |
| context 文字字元數 | 318 | 2880.5 | 16518 | 178392 |
| corpus 文件 bytes | 183 | 3188 | 7942 | 178392 |

`corpus.zip` 有 28481 個檔案，解壓後總計 104882784 bytes，唯一檔名 28481 個。
496 / 496 個來源 context 版本在 corpus 中找到同名檔案；496 / 496 個內容 SHA-256 也相符。
無法以 UTF-8 解碼的 corpus 檔案有 0 個；來源 context 文字含替代字元的出現次數有 0 次。
同一 context 版本最多出現在 9 筆查詢。檔名重複出現的明細及所有 context 指紋見 JSON 報告。
字元數超過 50,000 的不同 context 版本共有 5 個。

## 重複問題與標註風險

29 組問題文字相同，其中 20 組 contexts 相同，9 組 `is_impossible` 標記不同。
下表保存每組來源 ID 與欄位相等結果。字串相等不代表答案正確，也不建立正式 relevance label。

| 來源 ID | contexts 相同 | 答案字串相同 | `is_impossible` 相同 |
|---|---|---|---|
| `DEV_Q298`, `TRAIN_Q138` | False | False | False |
| `TRAIN_Q358`, `TRAIN_Q398` | True | True | True |
| `DEV_Q300`, `TRAIN_Q228` | True | False | True |
| `DEV_Q165`, `TRAIN_Q160` | False | False | False |
| `DEV_Q082`, `TRAIN_Q238` | False | False | False |
| `DEV_Q156`, `TRAIN_Q047` | True | False | True |
| `DEV_Q129`, `TRAIN_Q206` | True | False | True |
| `DEV_Q180`, `TRAIN_Q559` | True | False | True |
| `DEV_Q179`, `TRAIN_Q076` | True | True | True |
| `TRAIN_Q455`, `TRAIN_Q593` | True | False | True |
| `TRAIN_Q024`, `TRAIN_Q505` | True | True | True |
| `DEV_Q094`, `TRAIN_Q285` | True | False | True |
| `DEV_Q160`, `TRAIN_Q107` | True | False | True |
| `DEV_Q189`, `TRAIN_Q210` | False | False | False |
| `DEV_Q014`, `TRAIN_Q299` | True | False | True |
| `DEV_Q290`, `TRAIN_Q189` | True | False | True |
| `DEV_Q228`, `TRAIN_Q333` | False | False | False |
| `DEV_Q276`, `TRAIN_Q248` | False | False | False |
| `DEV_Q225`, `TRAIN_Q042` | True | False | True |
| `DEV_Q038`, `TRAIN_Q067` | True | False | True |
| `DEV_Q240`, `TRAIN_Q286` | True | True | True |
| `TRAIN_Q373`, `TRAIN_Q516` | True | True | True |
| `DEV_Q029`, `TRAIN_Q489` | True | False | True |
| `DEV_Q195`, `TRAIN_Q156` | False | False | False |
| `DEV_Q155`, `TRAIN_Q056` | True | False | True |
| `DEV_Q164`, `DEV_Q215` | True | True | True |
| `TRAIN_Q402`, `TRAIN_Q551` | False | False | False |
| `DEV_Q303`, `TRAIN_Q507` | True | False | True |
| `TRAIN_Q022`, `TRAIN_Q340` | False | False | False |

## 近似問題候選

以下比較採不同正規化文字的 token 集合 Jaccard。分數是自動候選指標，需人工判讀；ID 群組內可能含完全相同文字的多筆記錄。

| ID 群組 A | ID 群組 B | Jaccard |
|---|---|---:|
| `DEV_Q260` | `TRAIN_Q162` | 1.0 |
| `TRAIN_Q322` | `TRAIN_Q152` | 1.0 |
| `DEV_Q004` | `TRAIN_Q303` | 0.9041 |
| `TRAIN_Q072` | `DEV_Q171` | 0.9737 |
| `DEV_Q264` | `DEV_Q146` | 0.975 |
| `TRAIN_Q021` | `TRAIN_Q148` | 0.9024 |
| `TRAIN_Q021` | `DEV_Q037` | 0.9 |
| `TRAIN_Q148` | `TRAIN_Q015` | 0.9756 |
| `TRAIN_Q148` | `DEV_Q066` | 0.9048 |
| `TRAIN_Q148` | `TRAIN_Q291` | 0.9286 |
| `TRAIN_Q335` | `DEV_Q222` | 0.913 |
| `TRAIN_Q335` | `TRAIN_Q291` | 0.9091 |
| `TRAIN_Q257` | `DEV_Q222` | 0.9348 |
| `DEV_Q222` | `TRAIN_Q291` | 0.9091 |
| `DEV_Q037` | `TRAIN_Q291` | 0.9268 |
| `TRAIN_Q015` | `DEV_Q066` | 0.9268 |
| `TRAIN_Q015` | `TRAIN_Q291` | 0.9512 |
| `TRAIN_Q302` | `DEV_Q098` | 0.9231 |
| `DEV_Q072` | `TRAIN_Q265` | 0.9032 |
| `DEV_Q063` | `TRAIN_Q258` | 0.9855 |
| `TRAIN_Q597` | `TRAIN_Q330` | 0.92 |
| `TRAIN_Q597` | `TRAIN_Q393` | 0.9167 |
| `TRAIN_Q330` | `TRAIN_Q393` | 0.9167 |
| `DEV_Q094`, `TRAIN_Q285` | `DEV_Q039` | 0.9167 |
| `DEV_Q257` | `TRAIN_Q278` | 0.9459 |
| `TRAIN_Q280` | `TRAIN_Q388` | 0.9394 |
| `TRAIN_Q101` | `TRAIN_Q060` | 0.9444 |
| `DEV_Q288` | `DEV_Q291` | 0.9688 |
| `TRAIN_Q203` | `DEV_Q033` | 0.9444 |
| `TRAIN_Q064` | `TRAIN_Q510` | 0.913 |
| `DEV_Q055` | `DEV_Q262` | 0.9024 |
| `TRAIN_Q490` | `TRAIN_Q029` | 0.9559 |
| `TRAIN_Q413` | `TRAIN_Q338` | 0.9718 |
| `TRAIN_Q112` | `TRAIN_Q342` | 0.9651 |
| `DEV_Q112` | `DEV_Q206` | 0.9268 |
| `TRAIN_Q247` | `DEV_Q261` | 0.9333 |
| `DEV_Q040` | `TRAIN_Q134` | 0.9833 |
| `TRAIN_Q227` | `TRAIN_Q564` | 0.9 |
| `DEV_Q176` | `DEV_Q175` | 1.0 |

## 人工審核樣本

固定 seed `20261125`。抽樣 25 筆有答案且標為可回答、10 筆標為不可回答，另納入 2 筆空答案異常。
樣本選取與來源 ID 見 `data/manifests/relevance_review_sample.json`。人工審核結果填於 `reports/relevance_review.csv`；包含原始文字的本地審核包保存在 `data/review/review_packets.json`。重跑稽核腳本會保留已填寫的審核表。目前狀態為待人工審核。
審核時依 `query_id` 對照本地審核包的 question、answer、contexts。可回答題填 `relevant_yes_no`（context 是否切題）與 `answer_supported`（context 是否足以支持答案）；不可回答題因無來源 context，前兩欄填 `N/A`，檢查 `impossible_label_valid`。空答案異常需在 `reason` 說明。每列填 `reviewer` 與判斷理由；不確定時填 `unsure` 並說明。

## 尚待決策

來源 context 僅作 relevance 候選。人工審核完成後，記錄支持比例、錯誤案例與 Gate A 決策。資料切分需把相同或近似問題及共用文件關係納入檢查。資料集未提供經驗證的語言標籤，本輪未推斷完整語言分布。
