# 商品核心

本階段提供商品建檔、編輯、搜尋分頁、詳情、建立歷程與軟刪除，沿用舊版業務規則。
照片、詢價、成交與退回另階段移植；不顯示尚未啟用的操作，也不搬移舊資料。

## 行為與限制

- 所有登入者共用商品，員工可操作。名稱、品牌、分類與非負整數新臺幣成本必填；序號可重複。
- SKU 使用 `LX`、臺北日期 `YYYYMMDD` 及五碼大寫英數，建立後固定，不接受瀏覽器指定。
- 新增固定為未收購；分類保留舊版中文資料值。照片尚未移入，仍保留 `main_photo_id` 欄位。
- 已停用品牌不能用於新商品或改選品牌，既有商品可保留自己的原品牌。商品即使軟刪除仍保留引用，
  刪除品牌時改為停用，避免失去歷史關係。
- 商品建檔與建立歷程必須同一交易成功或失敗；歷程保存操作者 ID、當時帳號與事件時間。
- 列表可依名稱／SKU／序號、品牌、分類、狀態、顏色與年份篩選。桌面使用游標分頁，手機觸底才續載，
  失敗保留原商品與游標，明確重試後才再送出請求，篩選改變時重建列表。
- 已出售狀態保留在資料與契約中，但商品核心不提供售出入口。已出售商品不可編輯或刪除。
- 刪除採軟刪除，列表、詳情及歷程不再可讀，成功後直接由 Server Action 返回商品列表。
- 詳情的流向依時間呈現，保留既有歷程與原因；缺少建立事件時以建立日期顯示起點，不寫回資料庫。

## 為什麼

退回必須一起取消有效成交，不能先移入只有商品狀態變更的半套流程。因此本階段保留售出唯讀保護，
照片、詢價、成交與退回區塊均不顯示，後續連同交易原子性一起驗收。

資料表 `products` 與 `product_status_history` 保留舊欄位、型別、索引與約束。新 migration 直接採用
舊版最後的兩狀態規則，不重演在庫狀態的歷史轉換；舊資料與 Alembic revision 的搬移另案處理。

首頁與管理區返回改為 `/products`，接線由組裝層擁有。auth 仍沿用通用登入流程，共用層不寫入業務路徑，
不改寫新版的認證、Session、密碼併發保護或部署機制。

## 程式與測試

- 商品與歷程：[`service.py`](../../apps/api/modules/products/service.py)、
  [`test_model.py`](../../apps/api/tests/modules/products/test_model.py)
- 欄位與 SKU：[`test_schema.py`](../../apps/api/tests/modules/products/test_schema.py)、
  [`test_rules.py`](../../apps/api/tests/modules/products/test_rules.py)
- 表單與畫面分支：[`capabilities.test.ts`](../../apps/web/tests/modules/products/capabilities.test.ts)
- 手機續載：[`useMobileProducts.test.tsx`](../../apps/web/tests/modules/products/ui/useMobileProducts.test.tsx)
- 瀏覽器流程：[`products.spec.ts`](../../e2e/tests/products.spec.ts)
