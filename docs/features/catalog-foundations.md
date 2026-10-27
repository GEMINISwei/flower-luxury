# 品牌、廠商與匯率

共用業務資料的基礎模組，沿用舊版規則與資料欄位。商品核心見[商品核心](products.md)，
照片見[商品照片](product-photos.md)，詢價、成交及舊資料搬移屬於後續階段。

## 行為與限制

- 品牌與廠商由所有登入者共用，員工可以新增、編輯與刪除，沒有店家或使用者資料隔離。
- 名稱去除首尾空白、不分大小寫去重，列表按名稱排序。品牌未引用時可刪除，有引用時改為停用。
- 停用品牌不能供新的引用使用，既有引用可保留原品牌；引用規則不依賴商品模組，包含保留的軟刪除引用。
- 廠商國家只支援臺灣／中國，分別決定 TWD／CNY。`country_locked` 保留曾建立詢價的永久鎖定語意，
  鎖定後不能改國家，刪除會改為停用。建立詢價並鎖定國家的流程尚待詢價階段移入。
- 匯率設定只開放店長，代表 1 CNY 換算的 TWD 金額，沒有預設匯率。API 與資料庫最多六位小數，
  設定畫面顯示及儲存四捨五入至兩位。保留最後操作者與時間，之後不回寫歷史詢價與成交。
- `brands`、`vendors`、`exchange_rate_settings` 的表名、欄位、型別、唯一索引與約束沿用舊版。
  本次 migration 不帶入舊資料，不更動既有帳號及註冊設定的 migration。

## 為什麼

停用與永久鎖定保留引用歷史，避免後續修改名稱、國家或刪除業務資料時，讓既有交易的意義改變。
品牌的使用狀態從外鍵引用推導，不反向依賴商品模組；現階段以一般引用驗證，完整商品流程另行驗收。

金額的精度留在後端契約，設定頁的兩位小數只是這個業務功能的操作規則。畫面統一以臺北時間顯示，
固定組合日期數字，避免伺服器與瀏覽器 ICU 的分隔符差異造成 hydration 不一致。

## 程式與測試

- 品牌：[`service.py`](../../apps/api/modules/brands/service.py)、
  [`test_model.py`](../../apps/api/tests/modules/brands/test_model.py)
- 廠商：[`service.py`](../../apps/api/modules/vendors/service.py)、
  [`test_model.py`](../../apps/api/tests/modules/vendors/test_model.py)
- 匯率：[`test_rates.py`](../../apps/api/tests/modules/exchange_rates/test_rates.py)、
  [`format.test.ts`](../../apps/web/tests/modules/exchange_rates/format.test.ts)
- 瀏覽器流程：[`catalog.spec.ts`](../../e2e/tests/catalog.spec.ts)
