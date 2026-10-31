# 共用介面與導覽

移植既有視覺主題與桌面／手機操作，沿用新版的 manifest、路由保護、runtime 設定與 UI kit 邊界。

## 行為與限制

- 外觀以奶油白、香檳金與墨棕為主，由 `app/theme.css` 覆寫設計變數；PWA 啟動畫面的顏色同步更新。
- 桌面導覽依啟用模組與權限產生，新增匯率設定不改變管理區的既有入口：使用者管理仍為第一個管理頁。
- 手機最多保留三個模組入口，其餘進入「更多」，權限與順序沿用同一份導覽清單。
- 「更多」以底部彈窗顯示暱稱、身分、可用模組與帳號操作，支援 Escape、焦點循環、關閉後焦點還原，
  開啟時鎖定背景捲動。用戶設定、系統設定與管理區入口依目前身分提供。
- 用戶設定 `/settings` 提供個人資料與更改密碼；系統設定 `/settings/system` 提供語系與系統版本。
  桌面帳號選單與手機「更多」共用這兩個入口。
- 刪除等操作需明確確認，取消、關閉與 Escape 不執行操作；送出期間防止重複確認。
- 登入與管理區返回使用者區均進入 `/products`，根路徑由組裝層導向商品列表。

## 為什麼

共用視窗與日期格式放在 shared；手機導覽的模組與權限組裝留在 config，避免 shared 反向依賴業務模組。
主題保留既有品牌樣式，認證、Session、路由保護及部署流程繼續使用新版基礎建設。

## 程式與測試

- 導覽：[`navigation.ts`](../../apps/web/config/shell/navigation.ts)、
  [`mobile-navigation.test.ts`](../../apps/web/tests/config/shell/mobile-navigation.test.ts)
- 底部彈窗：[`BottomSheet.tsx`](../../apps/web/shared/ui/BottomSheet.tsx)、
  [`bottom-sheet.test.tsx`](../../apps/web/tests/shared/ui/bottom-sheet.test.tsx)
- 確認視窗：[`confirm-dialog.test.tsx`](../../apps/web/tests/shared/ui/confirm-dialog.test.tsx)
- 日期格式：[`date-time.test.ts`](../../apps/web/tests/shared/i18n/date-time.test.ts)
- 瀏覽器流程：[`catalog.spec.ts`](../../e2e/tests/catalog.spec.ts)
