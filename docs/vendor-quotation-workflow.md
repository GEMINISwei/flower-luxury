# 廠商、詢價與成交

所有登入者共用廠商與商品詢價。結帳批次不屬於此次系統功能。

廠商包含名稱、國家、備註、啟用狀態。國家僅臺灣 (TW) 與中國 (CN)，分別固定使用
TWD 與 CNY，不開放調整幣別。名稱去除首尾空白且不分大小寫去重。曾建立詢價的廠商
不能變更國家，即使詢價後來刪除也一樣；有歷史引用時刪除改為停用。停用廠商不可建立
新詢價，既有詢價仍可處理。

同商品、同廠商最多一筆詢價，重新報價修改既有紀錄。金額必須大於零，TWD 必須是整數，
CNY 最多兩位小數。每筆詢價保存國家、幣別、原幣金額、匯率及臺幣金額。TWD 匯率為 1，
CNY 新詢價取當時設定的匯率，未設定時拒絕新增。修改金額或備註沿用原匯率，只有獨立的
「套用最新匯率」操作會更新匯率並重新計算。以 Decimal 計算、ROUND_HALF_UP 四捨五入至
整數臺幣，輸入與結果限制在資料庫及前端能精確表達的範圍。前端不自行計算成交換匯。

取消直接切換已售出。未收購與在庫均可選定詢價「確認成交」，確認畫面顯示廠商、原幣金額、
匯率、臺幣成交額、目前成本與利潤。後端檢查確認時的詢價版本及成本，資料過期則要求重新
載入確認。成交保存當時的廠商名稱、國家、幣別、原幣金額、匯率、臺幣金額、成本、利潤、
操作者與時間，並同步變更商品狀態與寫入歷程，全部成功或全部回滾。利潤為臺幣成交額減
當時成本，允許負數，畫面顯示虧損金額。

已售出鎖定商品、照片與所有詢價寫入。原因必填的退回恢復編輯，取消目前成交選擇，保留
詢價與歷次成交快照。未曾成交的詢價可刪除；曾成交者永遠保留，退回後可修改原詢價，
再次成交另存歷史，不增加同廠商的詢價筆數。既有已售出商品不假造成交資料，仍可退回。

## 驗收條件

| 條件 | 測試名稱 |
|---|---|
| 廠商名稱去重、排序與國家驗證 | `test_vendor_names_are_unique_and_sorted`、`test_vendor_form_validates_country_and_name` |
| 曾有詢價後鎖國家，有引用只能停用 | `test_quoted_vendor_country_is_locked_and_delete_disables` |
| 同商品同廠商僅一筆，停用不可新增 | `test_quote_is_unique_per_vendor_and_rejects_inactive_vendor` |
| 報價為正數，TWD 整數、CNY 兩位小數與有限值 | `test_quote_amount_validation_follows_country` |
| 國家決定幣別，Decimal 計算並四捨五入 | `test_quote_uses_country_currency_and_half_up_rounding` |
| CNY 未設匯率拒絕，金額範圍安全 | `test_cny_quote_requires_rate_and_rejects_unsafe_amount` |
| 金額與備註修改保留原匯率，獨立刷新才更新 | `test_quote_edit_preserves_rate_until_explicit_refresh` |
| 直接售出拒絕，必須確認商品自己的詢價 | `test_direct_sale_is_rejected_and_quote_must_belong_to_product` |
| 成交鎖定所有寫入，快照保留當時成本與廠商 | `test_sale_snapshots_profit_and_locks_all_mutations` |
| 成交、狀態、歷程全部成功或回滾 | `test_sale_history_failure_rolls_back_entire_sale` |
| 過期報價版本與成本不可成交 | `test_sale_rejects_stale_quote_or_cost` |
| 同商品併發成交僅成功一次 | `test_concurrent_sales_create_one_current_sale` |
| 同商品同廠商併發詢價僅建立一筆 | `test_concurrent_quotes_keep_one_vendor_quote` |
| 退回及再次成交保留歷史，已成交詢價不可刪除 | `test_return_and_resale_preserve_snapshots_and_quote` |
| 未成交詢價可刪除，廠商國家保持鎖定 | `test_unused_quote_can_be_deleted_without_unlocking_country` |
| 所有新端點須登入，員工可操作，注入無效 | `test_trading_routes_require_login`、`test_staff_can_use_trading_routes`、`test_quote_ignores_injected_currency_and_rate` |
| UI 不提供直接售出，依鎖定／成交歷史提供操作 | `詢價操作遵守售出鎖定與成交引用保護`、既有 `售出只允許退回，其他狀態提供正確前進及退回目標` |
| 中英表單驗證及報價精度 | `廠商表單提供中英文驗證`、`詢價依國家驗證正數與小數位數` |
| 新增詢價不重複選用廠商，成交預覽明示虧損 | `詢價表單排除已報價與停用廠商`、`成交確認依臺幣金額與成本顯示利潤或虧損` |
| 接線與中英文、桌面手機可操作 | 既有 architecture、routes、route-adapters 測試與瀏覽器人工驗收 |

測試先於實作建立，完成後鎖定。舊測試直接售出的預設需經使用者同意後改成詢價成交；
鎖定、退回、歷程與回滾的保證持續驗證。

## 驗證紀錄

2026-10-20：

- 先建立規格與測試，確認後端缺少 vendors／quotes／sales 與前端缺少驗證／能力模組的預期紅燈。
- 使用者同意更新既有直接售出測試：兩種直接售出的轉換改為拒絕，售出鎖定與歷程改由詢價成交建立，
  一般狀態回滾改測未收購到在庫，另以新測試驗證整筆成交與退回的回滾。原鎖定、退回、歷程斷言保留。
- 使用者同意補能力判斷與服務拒絕路徑測試，並整理新增測試的分行與 import，不修改既定驗收條件。
- `make db migration "add vendors quotations and sale snapshots"` 產生三張表，已檢查外鍵、金額約束、
  同廠商唯一與目前成交部分唯一索引。既有商品沒有欄位變更，也不捏造舊成交。
- `make gen-types` 已更新 OpenAPI 與 TypeScript 型別。
- `make check` 通過：後端 495 項、前端 345 項。標準檢查略過後端 70 項資料庫測試。
  shared 獨立驗證後端 112 項、前端 188 項通過；後端 24 項資料庫測試依規格略過。
- `make check integration` 通過：564 項，1 項略過為 registry 測試沒有違規權限參數可測。
  `alembic check` 確認 model 與 migration 一致。Production build 保留 `ƒ Proxy (Middleware)`。
- 瀏覽器驗收：員工建立臺灣／中國廠商、詢價國家鎖定、同廠商選項排除、人民幣兩位小數與臺幣整數驗證、
  修改沿用原匯率、明確刷新匯率、負利潤確認、售出鎖定、退回及再成交、成本與廠商改名後舊快照保留。
- 1440px、900px、390px、320px 的代表畫面與中英文均可操作，無橫向溢出。
  瀏覽器發現 Node 與瀏覽器 ICU 的時間空白差異，統一空白後重新載入確認無 hydration 錯誤。
- 站內確認視窗與驗收見 [站內確認視窗](in-app-confirmations.md)。
- 實作提交的遠端 PR #7 `check`、`integration`、`images` 全部通過。
