# 帳號與註冊

系統提供兩種固定身分：店長與員工。店長使用共用註冊碼自行註冊，立即啟用；員工由店長在使用者管理建立。
內部沿用角色機制，店長持有 `super_admin` 的 `*` 權限，員工預設沒有管理權限。
畫面不提供角色指派或權限編輯。店長可編輯員工暱稱、停用／啟用員工及重設員工密碼。
既有的店長帳號保護維持：不能停用店長，也不能在後台重設店長密碼。

共用註冊碼由店長在後台設定或更換，資料庫只保存 SHA-256 摘要，API 不回傳原碼或摘要。
新碼儲存後後續註冊須使用新碼。初始未設定時不接受公開註冊，第一位店長以 `make db superuser` 建立。
註冊成功回登入頁，不自動簽發登入憑證。註冊依 IP 限制五分鐘內最多十次，成功也計入。

## 驗收條件

| 條件 | 測試名稱 |
|---|---|
| 正確註冊碼只將帳號、暱稱與密碼交給店長建立流程 | `test_signup_valid_key_creates_manager` |
| 未設定註冊碼或碼錯誤不建立帳號 | `test_signup_invalid_or_unset_key_rejects_creation` |
| 重複帳號回 409，不建立第二筆 | `test_signup_duplicate_username_returns_409` |
| 設定 API 僅回傳是否已設定 | `test_settings_response_does_not_expose_key` |
| 原碼不儲存；更換後只接受新碼 | `test_rotation_persists_hash_and_invalidates_old_key` |
| 真實註冊帳號立即啟用、有店長權限、密碼雜湊且可登入 | `test_signup_creates_active_manager_who_can_login` |
| 未登入與員工不能查看或修改註冊碼設定 | `test_settings_routes_reject_non_managers` |
| 公開註冊須通過註冊碼驗證 | `test_signup_route_requires_valid_registration_key` |
| 同來源成功註冊也受限流限制 | `test_signup_rate_limit_counts_successes` |
| 註冊表單中英驗證欄位與確認密碼 | `註冊資料缺漏與密碼不符會顯示對應語系錯誤` |
| 註冊碼設定驗證長度 | `註冊碼須為 8 至 128 個字元` |
| 使用者顯示固定店長／員工身分 | `依管理權限顯示店長或員工` |
| 員工不能管理其他帳號 | 既有 `test_user_admin_routes_reject_non_super_admin` |
| 保留帳號停用、改密碼、店長保護 | 既有 users service、routes、password revocation 測試 |

## 驗證紀錄

開發完成後更新於 PR，包含紅燈階段、`make gen-types`、migration、`make check` 與 `make check integration`。
