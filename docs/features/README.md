# 系統功能

功能怎麼運作、為什麼這樣設計，一個主題一份。要執行的指令與救援步驟在 [`operations.md`](../operations.md)，
要加新功能見 [`extending.md`](../extending.md)。

只寫讀程式碼推不出來的事：刻意的限制、沒做的功能、跨模組的行為與它的代價。欄位與畫面上有什麼，
程式碼與測試已經寫了，不在這裡重複。新增一份時照 [`_template.md`](_template.md) 的段落，並在下面加一行。

## 平台功能

模板內建，繼承的專案通常不用改。

| 文件 | 什麼時候讀 |
|---|---|
| [帳號、角色與密碼](accounts-roles.md) | 動到建立帳號、角色指派、權限檢查、後台入口、密碼重設 |
| [Session](session.md) | 動到登入、登出、token、`auth_version`、`EXPIRE_HOURS` |
| [限流](rate-limit.md) | 動到登入或改密碼的次數限制、用戶端 IP 的取得 |
| [語系](i18n.md) | 動到 `locale` cookie、`Accept-Language`、後端錯誤訊息的語言 |

## 業務功能

| 文件 | 什麼時候讀 |
|---|---|
| [店長註冊](registration.md) | 初始店長建立、共用註冊碼、公開註冊與限流 |
| [品牌、廠商與匯率](catalog-foundations.md) | 共用資料、刪除／停用、國家鎖定、匯率精度與舊版欄位 |
| [共用介面與導覽](interface.md) | 主題、手機更多、確認視窗與固定日期格式 |
| [商品核心](products.md) | 建檔、SKU、篩選分頁、狀態歷程、售出唯讀與軟刪除 |
