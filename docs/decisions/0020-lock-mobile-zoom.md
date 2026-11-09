# 0020. 手機上限制畫面縮放

狀態：採用（2026-11-09）

## 背景

主流無障礙建議是保留使用者縮放畫面的能力，讓需要較大文字的人可以放大閱讀。
本專案在手機上以固定頁首、底部導覽與對話框操作商品及員工資料，意外縮放會讓操作區位移，
使用者還得自行縮回原來的比例，因此選擇偏向原生 App 的操作方式。

## 決定

- viewport 設 `maximum-scale=1`、`user-scalable=no`（`apps/web/app/layout.tsx`）。
- 根元素設 `touch-action: manipulation`，避免雙擊放大（`apps/web/shared/ui/styles/base.css`）。
- 保留既有輸入欄位至少 16px 的字級保底（`--fs-input-mobile`），以及觸控裝置不自動聚焦輸入欄位的規則。
  iOS Safari 分頁會忽略 viewport 的部分縮放限制，仍需避免點輸入框時自動放大。

不以 JS 攔截 `gesturestart` 或 `touchmove` 強制禁止 iOS Safari 分頁的雙指縮放，避免誤擋捲動與依賴瀏覽器細節。

## 後果

- 支援 viewport 限制的瀏覽器會減少意外縮放，固定導覽與對話框的操作較穩定。
- iOS Safari 分頁仍可能允許雙指縮放；自動化測試驗證 viewport 與計算後的 CSS，手勢效果需實機確認。
- 需要放大畫面的使用者會受到限制，也可能影響無障礙檢測結果；本專案接受這項代價。
- 若使用者需要縮放閱讀或專案需符合無障礙規範，應重新評估並移除 viewport 的 `maximum-scale` 與
  `user-scalable`；`touch-action` 與輸入字級保底可以保留。
