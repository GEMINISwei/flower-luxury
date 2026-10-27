# 店長註冊

共用註冊碼是建立店長的授權憑證，功能沿用舊系統，接線遵循新版模組架構。
採用原因見 [ADR 0009](../decisions/0009-manager-registration-code.md)。

## 啟用與使用

- 第一位店長只能由 `make db superuser` 建立，再於 `/admin/registration` 首次設定註冊碼。
- 註冊碼未設定時，公開註冊拒絕建立任何帳號。錯碼與未設定對外使用同一錯誤訊息。
- 只有店長能讀取設定狀態、設定或更換註冊碼，員工無法使用設定端點。
- `/signup` 填入帳號、暱稱、密碼、確認密碼與註冊碼。成功後建立啟用的店長，不自動登入。
- 員工由店長建立，註冊流程不接受自選角色或啟用狀態。

## 保存與限制

註冊碼設定長度為 8 至 128 個字元，保留空白原樣，不自動 trim。只保存 SHA-256 摘要，
設定查詢只回傳是否已設定，不回傳原碼或摘要。更換後只有新碼有效，既有帳號與 Session 不受影響。
公開註冊依來源 IP 限制五分鐘十次，成功也計入；限制沿用平台的單一行程記憶體機制。

資料表沿用舊版 `registration_settings`，保留 `code`、`key_hash`、`id`、`created_at` 與 `updated_at`
的名稱、型別與約束。空表就是未設定，不提供預設註冊碼，也不從環境變數或 seed 寫入。
本次 migration 只新增該表，舊資料與 Alembic revision 的搬移另案處理。

## 程式與測試

- 後端：[`service.py`](../../apps/api/modules/registration/service.py)、
  [`test_service.py`](../../apps/api/tests/modules/registration/test_service.py)、
  [`test_model.py`](../../apps/api/tests/modules/registration/test_model.py)
- 權限與限流：[`test_routes.py`](../../apps/api/tests/modules/registration/test_routes.py)
- 表單驗證：[`validation.test.ts`](../../apps/web/tests/modules/registration/validation.test.ts)
- 瀏覽器流程：[`registration.spec.ts`](../../e2e/tests/registration.spec.ts)
