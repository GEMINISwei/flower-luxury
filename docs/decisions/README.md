# 設計決策（ADR）

這個專案自己的設計決定。模板帶來的決定在 [`starter/`](../starter/README.md)，那一區不改；
這裡記專案在那之上做的決定，包括推翻模板的哪一份。

每份記錄一個「看起來可以換成更常見的做法、但刻意不換」的決定：當時的情境、選了什麼、代價是什麼。
想提議改掉其中一項之前先讀那一份，確認情境是不是真的變了。

功能**現在**怎麼運作寫在 [`features/`](../features/README.md) 與其他文件，這裡只寫**為什麼**。

## 寫法

- 照 [`_template.md`](_template.md)，檔名 `NNNN-kebab-case.md`，編號從 0001 接著最後一號。一份只記一個決定。
- 寫好不改內容，只改狀態與錯字。決定被推翻時另寫一份，三處一起改（測試會擋）：
  新的寫「取代：`[NNNN](NNNN-xxx.md)`」；舊的狀態改成「被 `[NNNN](NNNN-xxx.md)` 取代（YYYY-MM-DD）」；
  索引狀態欄同步（去掉日期）。部分推翻也整份取代，並更新指向舊 ADR 的文件連結。
- **推翻模板的決定**：寫「取代：`[starter/NNNN](../starter/NNNN-xxx.md)`」，
  `starter/` 那一份不動，改在下面的〈推翻的模板決定〉加一列（測試會擋），並更新指向它的文件連結。
- 例外是討論後**維持原決定**的紀錄（例如 `project-review` skill 的反對結論），讓下次審視知道討論過什麼。
  以最近的 `v*` tag 為界，和 [migration](../extending/migrations.md#發版之前可以整理) 一樣：
  - **還沒有任何 tag**：直接改寫那份的「背景」或「後果」，把結論併進去，不留討論紀錄。
  - **有 tag 之後**：在最後的 `## 後續討論` 往下追加一筆，前面的段落不動。格式：

  ```markdown
  ## 後續討論

  ### YYYY-MM-DD <在哪裡提出，例如專案審視>
  - 提出：<項目與一句摘要>
  - 結論：維持原決定
  - 理由：<兩三句>
  ```

  討論的是模板的決定時，`starter/` 那一份一樣不動，在這裡另寫一份「維持 `starter/NNNN`」的 ADR。

## 索引

| 編號 | 決定 | 狀態 |
|---|---|---|
| [0001](0001-manager-registration-code.md) | 以共用註冊碼開放店長註冊，第一位店長由 CLI 建立 | 採用 |
| [0002](0002-durable-worker-ownership.md) | 背景工作以 worker 心跳與每次領取 token 保護執行權 | 採用 |
| [0003](0003-manual-collection-finalization.md) | 收件先保存，由人工完成收集與分組定稿後才加工 | 被 0004 取代 |
| [0004](0004-automatic-grouping-with-late-review.md) | 依 LINE 原始時間自動分組，收集結束後的遲到訊息交由人員加入 | 採用 |
| [0005](0005-worker-platform-scope.md) | 常駐 worker 共用平台環境，每個工作保留獨立交易 | 採用 |

## 推翻的模板決定

| 模板的決定 | 取代它的 ADR |
|---|---|
| [starter/0002](../starter/0002-no-web-signup.md) | [0001](0001-manager-registration-code.md) |

## 舊 ADR 對照

來源基礎決定已歸入 `starter/`；舊內容與日期可從 Git 歷史追溯。專案決策保留取代鏈。

| 原編號 | 現行依據 |
|---|---|
| 0001 | [docs/starter/0001-revoke-sessions-by-auth-version.md](../starter/0001-revoke-sessions-by-auth-version.md) |
| 0002 | [docs/starter/0002-no-web-signup.md](../starter/0002-no-web-signup.md) |
| 0003 | [docs/starter/0003-centralized-permission-and-language.md](../starter/0003-centralized-permission-and-language.md) |
| 0004 | [docs/starter/0004-single-api-process.md](../starter/0004-single-api-process.md) |
| 0005 | [docs/starter/0004-single-api-process.md](../starter/0004-single-api-process.md) |
| 0006 | [docs/starter/0005-postgres-job-queue.md](../starter/0005-postgres-job-queue.md) |
| 0007 | [docs/starter/0006-seed-in-migrate-service.md](../starter/0006-seed-in-migrate-service.md) |
| 0008 | [docs/starter/0007-no-built-in-error-tracking.md](../starter/0007-no-built-in-error-tracking.md) |
| 0009 | [docs/decisions/0001-manager-registration-code.md](0001-manager-registration-code.md) |
| 0010 | [docs/development.md](../development.md) |
| 0011 | [docs/starter/0008-full-repo-checkout-on-hosts.md](../starter/0008-full-repo-checkout-on-hosts.md) |
| 0012 | [docs/starter/0009-e2e-strategy.md](../starter/0009-e2e-strategy.md) |
| 0013 | [docs/decisions/0002-durable-worker-ownership.md](0002-durable-worker-ownership.md) |
| 0014 | [docs/decisions/0003-manual-collection-finalization.md](0003-manual-collection-finalization.md) |
| 0015 | [docs/decisions/0004-automatic-grouping-with-late-review.md](0004-automatic-grouping-with-late-review.md) |
| 0016 | [docs/starter/0009-e2e-strategy.md](../starter/0009-e2e-strategy.md) |
| 0017 | [docs/testing.md](../testing.md) |
| 0018 | [docs/starter/0010-no-environment-reviewer-for-deploys.md](../starter/0010-no-environment-reviewer-for-deploys.md) |
| 0019 | [docs/starter/0011-agent-guardrails-by-judgment.md](../starter/0011-agent-guardrails-by-judgment.md) |
| 0020 | [docs/starter/0012-lock-mobile-zoom.md](../starter/0012-lock-mobile-zoom.md) |
