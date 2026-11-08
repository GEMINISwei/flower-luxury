# 設計決策（ADR）

每份記錄一個「看起來可以換成更常見的做法、但刻意不換」的決定：當時的情境、選了什麼、代價是什麼。
想提議改掉其中一項之前先讀那一份，確認情境是不是真的變了。

功能**現在**怎麼運作寫在 [`features/`](../features/README.md) 與其他文件，這裡只寫**為什麼**。

## 寫法

- 照 [`_template.md`](_template.md)，檔名 `NNNN-kebab-case.md`，編號接著最後一號。一份只記一個決定。
- 寫好不改內容，只改狀態與錯字。決定被推翻時另寫一份，三處一起改（測試會擋）：
  新的寫「取代：`[NNNN](NNNN-xxx.md)`」；舊的狀態改成「被 `[NNNN](NNNN-xxx.md)` 取代（YYYY-MM-DD）」；
  索引狀態欄同步（去掉日期）。部分推翻也整份取代，並更新指向舊 ADR 的文件連結。
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
- 模板佔用目前的編號，繼承的專案從下一號接著寫，不要重新編號。

## 索引

| 編號 | 決定 | 狀態 |
|---|---|---|
| [0001](0001-revoke-sessions-by-auth-version.md) | 用 `auth_version` 撤銷 session，不做 refresh token | 採用 |
| [0002](0002-no-web-signup.md) | 網頁不開註冊，超級管理者只能用指令建立 | 被 0009 取代 |
| [0003](0003-centralized-permission-and-language.md) | `Permission` 與 `Language` 集中定義，不由模組動態組裝 | 採用 |
| [0004](0004-downtime-deploys.md) | 部署會短暫停機，api 維持單一行程 | 採用 |
| [0005](0005-in-process-rate-limit.md) | 限流計數放在行程記憶體 | 採用 |
| [0006](0006-postgres-job-queue.md) | 背景工作用 worker 容器與 PostgreSQL 佇列，不導入 Redis | 採用，已實作 |
| [0007](0007-seed-in-migrate-service.md) | 初始資料由 migrate 服務寫入，不用 Alembic 資料 migration | 採用 |
| [0008](0008-no-built-in-error-tracking.md) | 不內建錯誤追蹤與告警 | 採用 |
| [0009](0009-manager-registration-code.md) | 以共用註冊碼開放店長註冊，第一位店長由 CLI 建立 | 採用 |
| [0010](0010-make-and-bash-commands.md) | 指令介面用 Makefile 加 bash 腳本 | 採用 |
| [0011](0011-full-repo-checkout-on-hosts.md) | 部署主機上 git clone 整份 repo | 採用 |
| [0012](0012-e2e-required-in-ci.md) | Playwright E2E 是 CI 與部署的必要檢查 | 採用 |
| [0013](0013-durable-worker-ownership.md) | 背景工作以 worker 心跳與每次領取 token 保護執行權 | 採用 |
| [0014](0014-manual-collection-finalization.md) | 收件先保存，由人工完成收集與分組定稿後才加工 | 被 0015 取代 |
| [0015](0015-automatic-grouping-with-late-review.md) | 依 LINE 原始時間自動分組，遲到訊息由人員加入 | 採用 |
| [0016](0016-e2e-dev-loop-locally.md) | 開發中的 E2E 用常駐的 dev 環境，正式環境 image 由 CI 驗證 | 採用 |
| [0017](0017-e2e-failures-read-by-main-agent.md) | E2E 失敗由主 agent 自己讀，不交給子代理 | 採用 |
| [0018](0018-no-environment-reviewer-for-deploys.md) | 部署不設 environment reviewer，由發布前的確認把關 | 採用 |
| [0019](0019-agent-guardrails-by-judgment.md) | agent 防線以判斷為主，hook 只擋確認點 | 採用 |
