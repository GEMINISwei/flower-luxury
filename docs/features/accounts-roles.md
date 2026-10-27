# 帳號、角色與密碼

本專案使用店長／員工兩種身分，底層沿用模板的角色與權限機制。註冊的授權決策見
[ADR 0009](../decisions/0009-manager-registration-code.md)，註冊碼規則見[店長註冊](registration.md)。

## 帳號

第一位店長由維運人員使用 `make db superuser` 建立（見
[`operations.md`](../operations.md#建立超級管理者)）。尚未設定註冊碼時不能從網頁註冊；
設定後，持有有效碼者可自行註冊店長。維運指令仍可重複使用，供新增店長與失聯救援。

員工由店長在使用者管理建立，不指派角色。店長可修改員工暱稱、啟用／停用與重設密碼。
店長與員工都可以在個人設定修改自己的暱稱、密碼與語系。

## 角色與權限

店長使用 `super_admin` 系統角色（權限 `*`），員工沒有角色。畫面不提供角色指派或角色權限編輯；
原有角色 API 作為內部管理基礎保留。一般建立／編輯使用者的 API 仍不能指派店長角色。

系統角色由 seed 維護，不能經 API 修改名稱、啟用狀態或權限。店長建立邏輯由 users 模組擁有，
CLI 與驗證註冊碼後的 registration 模組共用，不改寫模板的認證或 Session 機制。

### 後台只開放給超級管理者

店長是本專案對超級管理者的顯示名稱。管理區 layout 與 API 仍要求 `Permission.ALL`；
一般角色的權限不能開啟後台。所有登入者共用業務資料，沒有多店或使用者資料隔離。

即使是店長也不能停用自己或任何店長、經一般角色指派提升為店長、在後台重設店長密碼、
把 `*` 放入一般角色，或修改系統角色。

## 密碼

- 記得目前密碼時，在個人設定自行更換；目前裝置保留登入，其他裝置失效。
- 員工忘記密碼時，由店長在後台重設，員工所有裝置失效。
- 店長忘記密碼時，由維運人員以 `make db superuser` 另建店長。沒有 email 密碼重設功能。

密碼運算沿用新版連線釋放與併發保護，Session 撤銷見 [Session](session.md#撤銷)。

## 程式與測試

- CLI：[`superuser.py`](../../apps/api/modules/users/superuser.py)、
  [`test_superuser.py`](../../apps/api/tests/modules/users/test_superuser.py)
- 共用店長建帳：[`manager.py`](../../apps/api/modules/users/manager.py)
- 系統角色與 seed：[`model.py`](../../apps/api/modules/roles/model.py)
- 後台保護：[`service.py`](../../apps/api/modules/users/service.py)、
  [`test_service.py`](../../apps/api/tests/modules/users/test_service.py)
