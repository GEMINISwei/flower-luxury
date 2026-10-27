# 變更紀錄

版本對應 `apps/api/app/config.py` 的 `APP_VERSION`。格式參考 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.1.0/)。

## [Unreleased]

- 移植店長／員工介面與共用註冊碼：第一位店長由 CLI 建立，店長設定註冊碼後可公開註冊；保留新版認證、Session 與資料庫連線保護，角色 API 保留且不提供角色編輯畫面。

## [0.0.0]

- 專案初始化：FastAPI + Next.js 全端模板，含認證、使用者與角色權限、中英雙語、Alembic migration。
