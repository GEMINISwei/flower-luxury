# 商品照片

所有登入者共用商品照片。支援選檔、手機拍照、建立前預覽、照片檢視、主圖、刪除及原圖下載。
照片與資料庫的實際搬移另案處理；交易流程見[詢價、成交與退回](product-trading.md)。

## 行為與限制

- 支援 JPEG、PNG、WebP、HEIC，後端以內容判斷格式。每批總量最多 15 MiB，不能有空檔案，沒有張數上限。
  前端選檔時與送出前均檢查，後端讀到超限即停止，整批檢查成功才處理圖片。
- 原始 bytes 完整保留，顯示圖另存為 2560×2560 無損 WebP。依 EXIF 修正方向、等比縮放及透明補邊，
  保留原有透明度，顯示圖不帶 EXIF；不裁切或移除照片背景。
- 儲存位置固定為 `/app/uploads/products/`。資料庫只保存 `products/` 開頭的相對路徑，
  原圖與顯示圖使用同一隨機編號，原始名稱只用於下載，不用於決定儲存路徑。
- 第一張照片自動成為主圖；畫面只對其他照片提供設主圖與刪除操作。API 若刪除主圖，會改選剩餘照片中的第一張。
- 已出售商品可看照片、下載原圖，不能新增、設主圖或刪除。商品軟刪除後，照片列表、顯示圖與原圖均不可讀。
- 新增商品時先儲存欄位，再上傳照片；照片失敗後保留已建立的商品編號，鎖定已存欄位，可移除或補傳照片，
  重試不重複建立商品。編輯既有商品的照片由照片視窗管理。
- 原圖與顯示圖成對寫入，寫入失敗會刪除半成品；外層資料庫交易回滾會清掉新檔。
  刪除照片先更新資料庫，根交易成功後才清檔，回滾時保留原檔。
- 舊照片沒有原圖資訊時仍能顯示，下載入口不提供。`original_storage_key`、`original_filename`、
  `original_media_type` 需同時有值或同時為空，沿用舊版欄位與完整性約束。

## 與新版基礎建設的整合

照片仍屬於 products 模組。ORM 查詢在 `model.py`，照片服務回傳建構好的 Pydantic model；
路由在圖片處理前使用既有 `release_connection()` 釋放只讀連線，寫入時重新取得連線並鎖定商品。

上傳從模組的具名 Server Action 進入，使用 `shared/api` 的 `apiUpload()`。端點、路徑參數與成功回應由
OpenAPI 推導，只允許宣告 multipart 的 POST；共用原有的認證、語系、請求追蹤、真實 IP、401 清理與導向、
欄位錯誤解析與成功刷新。FormData 保留 File 與重複欄位，Content-Type 的 boundary 交給 fetch 產生。
共用 helper 維持 server-only，不是可直接呼叫的通用 Server Action。

開發與正式 nginx 只另外開放照片的 `file`／`download` 讀取路徑，由後端驗證 Session；
其餘 API 仍不直接對瀏覽器開放。照片回應固定 `Cache-Control: private, no-store` 及 `Vary: Cookie`，
下載另帶原始名稱、媒體類型與 attachment 標頭。16MB 的全站請求上限維持不變。

## 程式與測試

- 照片與交易：[`photos.py`](../../apps/api/modules/products/photos.py)、
  [`test_photo_originals.py`](../../apps/api/tests/modules/products/test_photo_originals.py)
- 圖片轉換：[`images.py`](../../apps/api/modules/products/images.py)、
  [`test_display_images.py`](../../apps/api/tests/modules/products/test_display_images.py)
- 共用上傳：[`upload.server.test.ts`](../../apps/web/tests/shared/api/upload.server.test.ts)
- 新增與補傳：[`creation.test.ts`](../../apps/web/tests/modules/products/creation.test.ts)
- 瀏覽器流程：[`product-photos.spec.ts`](../../e2e/tests/product-photos.spec.ts)
