# 0007. 後端覆蓋率在 `make check integration` 內合併判定，不另設 job

狀態：採用（2026-11-10）

取代：[0006](0006-combined-backend-coverage.md)

## 背景

0006 要擋的是「只看單元測試的覆蓋率」：存取資料庫的程式碼一律算成沒測到，純單元只有 71.30%，
過不了原本 74% 的門檻。當時的做法是 `api-test` 與 `api-integration` 各自產生覆蓋率資料，
再由獨立的 `api-coverage` job 下載兩份合併判定。

之後模板也改成合併單元與 integration 後判定，只是做法不同：在 `make check integration` 裡先平行跑
不需要資料庫的測試、再依序跑 integration，兩段累加後當場檢查門檻。兩邊要擋的事已經一致，
差的只剩機制；保留自己的機制，每次從模板移植 `scripts/check.sh`、`ci.yml` 與相關測試都會衝突。

## 決定

- 照模板的做法：`make check integration`（CI 的 `api-integration`）跑全部後端測試，合併覆蓋率後檢查
  `pyproject.toml` 的 `fail_under`，之後才跑 `alembic check`。`api-test` 不算覆蓋率。
- 拿掉 `api-coverage` job 與 `make check api-coverage`，`ci-gate` 不再等它。
- 門檻數字不跟模板，沿用本專案原本的值，之後依合併後的實測值另外決定。

## 後果

不需要資料庫的後端測試在 CI 上跑兩次（`api-test` 一次、`api-integration` 再一次），
`api-integration` 多出的時間大約是 `api-test` 本身跑一次的時間；換到的是本機 `make check integration` 就能重現覆蓋率判定、
少一段 artifact 傳遞，以及之後從模板移植檢查流程時不再衝突。
CI 的時間成為瓶頸時，再回頭考慮把合併拆到另一個 job。
