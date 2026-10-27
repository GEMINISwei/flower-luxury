# 詢價、成交與退回

所有登入者共用詢價與成交資料，員工可操作。沿用舊版的兩狀態流程：商品先是未收購，必須透過詢價確認成交
才成為已出售；退回後回到未收購，保留歷史成交與操作歷程。資料搬移另案處理。

## 詢價與匯率

- 同一商品與廠商最多一筆詢價。新增只能選啟用廠商，國家決定幣別：臺灣為 TWD，中國為 CNY。
- 原幣報價必須大於零且不超過 9999999999.99，人民幣最多兩位小數，臺幣只能是整數。
- 臺幣使用固定匯率 1，不需要設定系統匯率。人民幣需先由店長設定匯率，再將原幣乘匯率、四捨五入至整數臺幣。
  換算後臺幣不超過 JavaScript 安全整數範圍。
- 詢價保存幣別、當時匯率、換算臺幣與版本，瀏覽器不能指定計算結果。修改報價保留原匯率，
  只有明確確認「套用最新匯率」才重新讀取系統匯率；兩種操作都增加版本。
- 建立詢價與廠商的 `country_locked` 永久標記同一交易完成。國家鎖定後，即使未成交詢價全部刪除也不解除。
  缺少匯率或建立失敗時不留下詢價或鎖定標記。
- 未被成交引用的詢價可刪除，曾用於成交的詢價永久保留。廠商改名不改寫已保存的成交名稱。

## 成交與退回

- 成交請求攜帶報價 ID、看到的報價版本與商品成本。後端鎖定商品後重新讀取資料，版本或成本已變更即拒絕，
  確認畫面可重新載入最新資料；不能使用其他商品的報價，也不能直接改狀態為已出售。
  商品成本儲存後先取得最新詳情再關閉編輯，後續成交使用更新後的成本。
- 成交保存廠商名稱、國家、幣別、原幣、匯率、臺幣、成本、利潤、操作者及時間快照。利潤為成交臺幣減成本，
  允許虧損，確認前明確提示。
- 成交快照、商品售出狀態與歷程一起成功或回滾。所有商品寫入鎖同一列，部分唯一索引另外保證每商品最多一筆有效成交。
- 已出售商品不可編輯／刪除、寫入照片或變更詢價，但仍可讀取資料、照片及下載原圖。
- 退回必填非空白原因，同一交易取消有效成交、記錄退回人與時間、改回未收購並新增歷程；
  任一寫入失敗都維持原有效成交及售出狀態。
- 退回後可修改商品與原詢價，再建立新的成交。過去的金額、匯率、成本、利潤與退回原因不被新成交覆寫。
- 商品軟刪除後，詢價與成交列表也不可讀；資料仍保留引用關係。

## 與新版架構的整合

`product_quotes` 與 `product_sales` 的欄位、精度、約束與索引沿用舊版，新增 migration 不改寫前幾階段。
ORM 查詢留在 model，詢價、成交與商品服務對外回傳 Pydantic model，寫入欄位逐一列出。
跨模組的廠商與匯率能力只經 public entry，前端使用既有型別化 API 與 UI kit，不改寫認證、Session、照片上傳或部署機制。

## 程式與測試

- 詢價與匯率：[`quotes.py`](../../apps/api/modules/products/quotes.py)、
  [`test_quotes.py`](../../apps/api/tests/modules/products/test_quotes.py)
- 成交與快照：[`sales.py`](../../apps/api/modules/products/sales.py)、
  [`test_trading_service.py`](../../apps/api/tests/modules/products/test_trading_service.py)
- 金額規則：[`test_quote_rules.py`](../../apps/api/tests/modules/products/test_quote_rules.py)
- 前端分支與中英驗證：[`quote-validation.test.ts`](../../apps/web/tests/modules/products/quote-validation.test.ts)
- 詢價與匯率瀏覽器流程：[`product-trading.spec.ts`](../../e2e/tests/product-trading.spec.ts)
- 員工建檔、照片與成交退回完整流程：[`product-lifecycle.spec.ts`](../../e2e/tests/product-lifecycle.spec.ts)
