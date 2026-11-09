# 0005. 常駐 worker 共用平台環境，每個工作保留獨立交易

狀態：採用（2026-11-09）

## 背景

[starter/0013](../starter/0013-cross-module-references-by-id.md) 要求非 HTTP 入口透過 `platform_scope()`
取得 session 與事件訂閱表。本專案已有常駐 worker，領取、執行、心跳、重試各有自己的交易；
把整個程序包在預設的交易中，會讓消費迴圈繼承不該共用的 session。

## 決定

- CLI 沿用 `platform_scope()` 預設的單次交易。
- collector 使用 `platform_scope(transactional=False)`，由平台統一管理引擎與事件訂閱表。
- worker 框架繼續為每個工作單元開獨立的 `session_scope()`；事件處理函式共用目前工作的交易。
- 不更動持久工作佇列的心跳、持有權、提交後通知與外部副作用規則。

## 後果

常駐程序與單次 CLI 都取得相同的平台能力，平行工作不共用 session；程序結束仍由平台釋放引擎。
這是來源決定在既有 worker 的實作延伸，沒有推翻來源的跨模組與交易原則。
