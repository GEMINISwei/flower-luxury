# 背景工作

背景工作使用獨立的 `line-collector` 容器，與 API 共用 image、PostgreSQL 及 uploads volume，
不另外引入 Redis（[ADR 0006](../decisions/0006-postgres-job-queue.md)）。
目前已註冊商品暫存清理、到期摘要、LINE 圖片下載與群組名稱查詢任務。
LINE 功能兩項金鑰都留空即可停用，群組預設不收集，見 [LINE 商品收集](../features/line-collection.md)。

## 宣告與排入任務

各模組在自己的 `manifest.py` 宣告 `TaskSpec`，組裝層從 `ENABLED_MODULES` 收集。
任務名稱需唯一，停用模組後不再領取它的工作；未知任務保留在佇列，避免被其他程序誤刪。

```python
from shared.jobs.contracts import Job, TaskSpec
from shared.jobs.queue import enqueue_job


async def download_photo(job: Job) -> None:
    photo_id = str(job.payload["photo_id"])
    # 依 photo_id 讀取模組資料, 下載與存檔要能安全重跑。


DOWNLOAD_PHOTO = TaskSpec(
    name="example.download_photo", handler=download_photo,
    max_attempts=3, timeout_seconds=60,
)

# MODULE = ModuleManifest(..., tasks=(DOWNLOAD_PHOTO,))
# 在現有業務 transaction 內呼叫:
# await enqueue_job(DOWNLOAD_PHOTO.name, {"photo_id": photo_id})
```

`enqueue_job()` 使用目前的 session，不自行 commit；業務資料與工作一起成功或回滾。
payload 優先只存業務識別碼，不複製完整原文、圖片 bytes 或憑證；需要的內容由模組持有並決定保存期限。
延後執行可傳 `available_at`，時間使用 `shared.time.utc_now()` 的 naive UTC。

## 執行與失敗

- 以 `FOR UPDATE SKIP LOCKED` 領取，領取交易先提交，外部下載期間不持有領取列鎖。
- 每次領取更換 lease token、增加嘗試次數；持有期限為任務 timeout 加 30 秒清理餘裕。
- 框架替每個 handler 開自己的 `session_scope()`。handler 成功與工作刪除在同一個交易完成；
  失敗、取消或失去持有權時回滾業務寫入。
- 逾時會取消 handler。SIGTERM 停止領取並取消目前工作，等待清理後退出。
- 失敗以 30、60、120 秒等間隔重試，最多 900 秒；到達 `max_attempts` 後標成 `failed`。
  程序被強制中止時，期限到後可重新領取；最後一次領取逾期則標成失敗。
- 成功即刪除工作與 payload；失敗保留工作供排查，不保存 exception 字串。
  log 只記工作 ID、任務名稱與錯誤類別。

持有權檢查保護資料庫提交，不能讓外部 API 或檔案系統操作自動變成一次執行。
handler 仍須能重跑、正確回應取消，檔案失敗清理與業務刪除競爭由模組負責。
做慢速下載前若已讀取資料庫，可用 `release_connection()` 歸還只讀連線；已寫入時不能歸還。

## 維運

```bash
make services                       # 查看 line-collector 的狀態
make services logs line-collector    # 追蹤背景程序紀錄
```

`make start` 會一起啟動容器，worker 只執行任務，不跑 migration 或 seed。
每五秒成功探測 PostgreSQL 後更新 heartbeat，30 秒內未更新視為 unhealthy；程序遇到資料庫錯誤會退出，
由容器 restart policy 重新啟動。開發環境掛載來源程式，但改過任務程式需重新啟動程序才會載入。

備份、還原及 migration 的停止與恢復規則見[維運文件](../operations.md#背景收集程序)。
LINE Developers Console、Webhook、邀請 Bot 入群及群組啟用步驟見
[LINE 商品收集](../features/line-collection.md#line-後台設定)。
