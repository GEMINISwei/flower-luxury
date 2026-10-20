# 變更紀錄

版本對應 `apps/api/app/config.py` 的 `APP_VERSION`。格式參考 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.1.0/)。

## [Unreleased]

- 檢查流程的 Ruff 不再使用快取，避免模組增刪後沿用過期的 import 分類判定。

- 新增共用品牌與商品管理、登入保護的商品照片（含 HEIC）、已售出鎖定與必填原因的退回歷程，以及店長後台的人民幣兌新臺幣匯率設定。

- 新增僅開發環境可用的 `make start lan`，輸出區網網址供手機測試；一般 `make start` 恢復只限本機。

- 新增共用註冊碼的店長公開註冊與後台註冊碼設定；帳號顯示店長／員工，員工由店長建立，移除角色與權限編輯畫面。

- 移植舊版奶油白、香檳金與墨棕視覺主題，更新登入頁及桌面／平板／手機外殼，加入首頁導覽與小花標誌。

## [0.0.0]

- 專案初始化：FastAPI + Next.js 全端模板，含認證、使用者與角色權限、中英雙語、Alembic migration。
