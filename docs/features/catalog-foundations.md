# 品牌與廠商

共用業務資料的基礎模組。商品核心見[商品核心](products.md)，照片見[商品照片](product-photos.md)，
逐筆匯率與成交見[詢價、成交與退回](product-trading.md)，舊資料搬移另案處理。

## 行為與限制

- 品牌與廠商由所有登入者共用，員工可以新增、編輯與刪除，沒有店家或使用者資料隔離。
- 名稱去除首尾空白、不分大小寫去重，列表按名稱排序。品牌未引用時可刪除，有引用時改為停用。
- 停用品牌不能供新的引用使用，既有引用可保留原品牌；引用規則不依賴商品模組，包含保留的軟刪除引用。
- 廠商只設定名稱、備註與啟用狀態，不設定國家或幣別。`has_quotes` 永久保存曾建立正式詢價的事實，
  曾有詢價的廠商刪除時改為停用，即使最後一筆未成交詢價已刪除也不解除。
- 不再提供全域匯率設定；每筆報價自行帶入匯率，未指定時為 1。匯率最多六位小數，
  修改報價不改寫過去成交的金額與匯率，詳細限制見[詢價、成交與退回](product-trading.md)。
- 升級時先把舊暫存報價依原廠商國家補入匯率：臺灣為 1，中國為當時系統設定值。
  中國廠商仍有暫存報價但未設定系統匯率時，migration 會停止，須先設定後再升級。
  舊廠商的國家欄位與全域匯率表於補值後移除，既有正式報價與成交快照不變。

## 為什麼

報價與匯率屬於每筆詢價的條件，廠商名稱不再決定換算方式。停用與永久引用記錄保留歷史識別，
避免刪除曾有業務往來的廠商。金額與匯率精度由後端契約驗證，畫面輸入與審核轉入使用同一份規則。

## 程式與測試

- 品牌：[`service.py`](../../apps/api/modules/brands/service.py)、
  [`test_model.py`](../../apps/api/tests/modules/brands/test_model.py)
- 廠商：[`service.py`](../../apps/api/modules/vendors/service.py)、
  [`test_model.py`](../../apps/api/tests/modules/vendors/test_model.py)
- 舊暫存匯率轉換：[`test_quote_rate_migration.py`](../../apps/api/tests/modules/product_drafts/test_quote_rate_migration.py)
- 瀏覽器流程：[`catalog.spec.ts`](../../e2e/tests/catalog.spec.ts)
