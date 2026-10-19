# 品牌、商品與匯率

所有登入者共用資料, 可管理品牌、商品、成本、照片與狀態。只有註冊碼、匯率設定與使用者管理限店長,
放在後台。本階段不移植結帳批次、不建立廠商詢價與最終出貨廠商, 不搬移舊資料。

商品保留名稱、品牌、分類、型號、序號、顏色、年份、成本與備註。名稱、品牌、分類、成本必填,
成本為非負整數新臺幣。分類沿用鞋子、配飾、皮件、包包、帽子、衣服、其他。序號可重複。
SKU 為 LX + 臺北日期 YYYYMMDD + 五碼英數, 系統建立且不可修改。刪除後不提供還原。

新增固定未收購; 未收購可到在庫或已售出, 在庫可到已售出。退回走獨立操作:
在庫可退到未收購, 已售出可退到在庫或未收購。原因必填。已售出禁止欄位、照片、主圖、刪除及一般
狀態變更, 只能退回。退回後恢復編輯。歷程保留操作者 ID、當時帳號、時間、原因與前後狀態。
未來退回不刪除詢價, 清除目前成交選擇時也必須保存歷史值。

品牌名稱固定升冪排序, 去除首尾空白且不分大小寫去重。有商品引用的品牌刪除改為停用;
停用品牌不能用於新增或改選, 既有商品可以保留原品牌。

照片不限張數, 每次上傳原始檔合計不得超過 15 MiB (15 × 1024 × 1024 bytes)。支援 JPEG、PNG、
WebP、HEIC, 由後端解碼驗證並產生 WebP 顯示檔, 不信任副檔名或 MIME。第一張自動主圖,
刪除主圖時由剩餘第一張遞補。圖片端點逐次驗證登入, 不提供公開快取。無效的整批上傳不新增照片。

匯率只開放 CNY, 定義為 1 CNY = 指定小數 TWD, 必須為有限正數, 最多六位小數。
未設定時不假造預設值。設定記錄最後操作者與時間。未來詢價必須保存當次匯率, 不回寫歷史金額。

## 驗收條件

| 條件 | 測試名稱 |
|---|---|
| 正向與退回轉換符合規格, 原因必填 | `test_status_transitions_follow_workflow`、`test_return_requires_reason` |
| 不接受狀態與 SKU 注入, 必填欄位與成本檢查 | `test_product_form_rejects_invalid_fields`、`test_create_ignores_injected_workflow_fields` |
| 售出拒絕所有修改, 退回後可編輯 | `test_sold_product_rejects_all_mutations_until_return` |
| 狀態與歷程一起成功或回滾 | `test_status_history_failure_rolls_back_status` |
| 歷程保存操作者、原因、時間與直接售出及退回 | `test_status_history_preserves_actor_and_reason` |
| 列表正確篩選、分頁與重複序號 | `test_products_filter_page_and_allow_duplicate_serials` |
| 刪除後無法再取得且不提供還原 | `test_delete_product_hides_detail_and_photos` |
| 品牌去重、排序與停用引用保護 | `test_brand_names_are_unique_and_sorted`、`test_referenced_brand_is_disabled_and_existing_product_can_keep_it` |
| 圖片驗證真實內容, 支援 HEIC, 不限制張數 | `test_image_formats_decode_to_webp`、`test_invalid_image_rejected`、`test_more_than_ten_photos_and_main_replacement` |
| 前後端限制單次總容量, 整批無效不新增 | `test_photo_batch_limit_and_atomic_validation`、`照片總容量上限為 15 MiB 且不限制張數` |
| 圖片僅登入可讀, 員工可操作業務端點 | `test_catalog_routes_require_login`、`test_staff_can_use_catalog_routes`、`test_photo_file_requires_login_and_disables_caching` |
| 匯率僅店長可設定, 只接受有效正小數 | `test_exchange_routes_reject_non_managers`、`test_exchange_rate_validates_decimal` |
| 匯率精確保存且不建立多份設定 | `test_exchange_rate_upsert_keeps_decimal_and_actor` |
| 畫面依售出狀態鎖定且顯示正確轉換選項 | `售出只允許退回，其他狀態提供正確前進及退回目標` |
| 中英文表單驗證 | `商品必填與成本驗證提供中英文錯誤`、`匯率只接受六位內的正小數` |
| 新模組接線、三種寬度及中英文可操作 | 既有 architecture、routes、route-adapters 測試與瀏覽器人工驗收 |

先建立本表所有自動測試後才實作, 實作期間測試鎖定。驗證結果完成後補記。
