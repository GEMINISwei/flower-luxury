# 原圖保存與手機更多選單驗收條件

## 照片

- 支援 JPEG、PNG、WebP、HEIC，原始位元組完整保存，下載取得相同內容與原始檔名 → `test_upload_preserves_original_and_pairs_display`、`test_original_download_requires_login_and_uses_attachment`。
- WebP 顯示圖固定 2560 × 2560、等比例縮放（允許放大小圖）、置中補透明、不裁切或去背，使用無損壓縮 → `test_display_photo_fits_canvas_without_cropping_or_background_removal`、`test_display_photo_respects_exif_orientation`。
- 原圖與顯示圖在同一照片資料列，以相同識別碼及不同目錄配對；原圖也是 WebP 時不覆寫 → `test_upload_preserves_original_and_pairs_display`。
- 無效整批上傳、寫檔失敗與交易回滾不留下檔案；刪除照片同時清理兩份 → `test_invalid_batch_creates_no_files`、`test_write_failure_cleans_both_files`、`test_photo_rollback_removes_both_files`、`test_delete_photo_removes_both_files`。
- 舊照片繼續顯示，不假造原圖下載；已刪除商品的原圖也不可下載 → `test_legacy_photo_has_no_original_download`、`test_deleted_product_original_is_not_accessible`。
- 原圖下載採登入驗證、禁止快取，開發與正式 nginx 都轉接下載路徑 → `test_original_download_requires_login_and_uses_attachment`、`test_photo_download_proxy_is_available_in_both_templates`。
- 原圖類型依真實內容決定，下載檔名不帶路徑或控制字元；整批讀取驗證容量與內容 → `test_original_format_uses_content_instead_of_filename`、`test_original_download_filename_removes_paths_and_control_characters`、`test_read_batch_checks_total_size_before_converting`、`test_read_batch_rejects_invalid_content_even_with_supported_filename`。

## 手機導覽

- 最多前三個模組入口加「更多」，溢出項目移入彈窗，保持順序與權限 → `手機導覽最多三個模組入口，其餘移入更多`、`手機導覽沿用區域與權限篩選`。
- 溢出頁面與帳號頁面可正確標示「更多」 → `更多涵蓋溢出模組與帳號頁面`。
- 從底部開啟彈窗，Header 顯示頭像、暱稱、角色；可點背景、關閉鍵或 Escape 關閉，焦點限制在彈窗並於關閉後還原 → `底部彈窗可關閉並還原焦點`、`底部彈窗限制焦點並鎖定背景捲動`。
- 沿用既有色彩與設計變數，桌面導覽不變 → `make check` 與手機／桌面人工畫面驗證。

## 相容策略

既有 `storage_key` 保留為顯示圖路徑，新增原圖路徑、原始檔名與 MIME 欄位；舊資料不回填假原圖。
