# LINE 商品收集

LINE 收件後端會自動發現群組，將已啟用群組在指令批次內的圖片與逐則文字送入商品暫存。
店長於 `/admin/line-groups` 啟停群組資格、手動結束批次與查看異常；所有登入者於 `/product-drafts` 整理與逐筆審核。

## LINE 後台設定

1. 在 [LINE Official Account Manager](https://manager.line.biz/) 建立或選擇官方帳號，於設定啟用 Messaging API，
   選擇對應的 Provider。操作入口見 [LINE 官方入門文件](https://developers.line.biz/en/docs/messaging-api/getting-started/)。
2. 到 [LINE Developers Console](https://developers.line.biz/console/) 選擇該 Messaging API channel。
   在 **Basic settings** 取得 **Channel secret**；在 **Messaging API** 發行 **Channel access token (long-lived)**。
   兩者均屬祕密，不貼進 PR、聊天、截圖或版本控制。
3. 在部署目錄 `.env` 同時填入 `LINE_CHANNEL_SECRET` 與 `LINE_CHANNEL_ACCESS_TOKEN`。
   兩者都留空時功能停用；僅設定其中一個時 API 啟動會拒絕。變更後執行 `make start` 重建服務設定，
   `make services restart` 不會重新注入 `.env`。
4. 準備可被 LINE 存取、憑證有效的公開 HTTPS 網址，主機 reverse proxy 導向本專案的 nginx。
   Webhook URL 為 `https://你的網域/api/line/webhook`。主機須覆寫 `X-Real-IP` 與 `X-Forwarded-Proto`，
   詳見[主機 reverse proxy](../operations.md#主機的-reverse-proxy)。不用公開整個 `/api/`。
5. 在 channel 的 **Messaging API** 頁設定 Webhook URL，按 **Verify**，再開啟 **Use webhook**
   與 **Webhook redelivery**。Verify 發送的空事件陣列也會驗證簽章，成功回應 `200`。
6. 開啟 **Allow bot to join group chats**，把官方帳號邀請進目標群組，在群組傳一則訊息。
   系統從入群／訊息事件取得群組 ID，背景查詢名稱；使用者不必找 ID。
   LINE 的群組限制見[官方群組文件](https://developers.line.biz/en/docs/messaging-api/group-chats/)。
7. 店長在 `/admin/line-groups` 依群組名稱啟用收集資格，再於群組傳送 `/start` 開始收集、`/end` 結束整批。
   群組任何成員均能下指令，同群組多人共用一批；啟用前與收集區間外的訊息不補收。
   先以測試群組完成實際驗收，再啟用真正的商品來源。

本機 `localhost` 不能直接供 LINE 呼叫；開發驗收需另外準備公開 HTTPS 測試入口。
本功能只接收群組訊息，不收私訊、舊式 room、相簿或記事本。精確指令會回覆開始／停止／已在目前狀態的結果。
指令去除頭尾空白後須整則符合 `/start` 或 `/end`，指令不保存為商品原文；重複指令不重開或建立空批次。
不設定自動逾時，忘記 `/end` 時可由店長於後台結束；重啟會保留收集狀態。
如官方帳號仍有自動回應或歡迎訊息，可於 Official Account Manager 依團隊需要關閉。

## 收件與群組狀態

- Webhook 以原始 bytes 驗證 HMAC-SHA256，通過才解析內容及碰資料庫。
  API 限制 Webhook 為 1 MiB，nginx 維持全站 16 MB 上限；只公開這一條精確 POST 路徑，
  金鑰、簽章與 body 不記錄在 log。
- 新發現的群組預設停用。停用時只保存識別與名稱，不保存商品原文或排入圖片下載。
  群組名稱查詢失敗仍保留群組識別，可用 ID 辨認；不會因此自動啟用。
- 群組列表及啟用／停用 API 只供店長呼叫，網址為 `/api/line/groups`。
  管理 API 不經 nginx 對外公開，由 Server Component／Server Action 接線。
  `/api/line/sources` 只回傳來源鍵與名稱，所有登入者可供暫存群組篩選使用，不含管理狀態。
- 啟用時記下 UTC 邊界，時間早於啟用的延遲事件不補收。群組停用或 Bot 退群後停止新收件，
  已收進暫存的資料仍保留。退群會撤銷啟用狀態；重新邀請後要由店長再次啟用。
- 同一封 Webhook 的各群組依固定順序鎖定，同群組依原始傳送時間處理；跨 Webhook 的延遲事件依
  [商品暫存規則](product-drafts.md#收集與分組)補入原商品或留下異常提示，不重切已成立的商品。
  `/end` 後才送達、但原始時間在區間內的事件仍可補入；群組停用或 Bot 退群則停止所有新收件。
- 指令狀態與回覆工作同一交易提交，worker 在提交後送出回覆；回覆失敗不回滾批次，後台提示未送達。
  reply token 僅在獨立暫存表保存最多 50 秒的有效窗口，工作 payload 只有內部識別；正常完成或失敗即刪除，
  worker 停止時實際清除延後至恢復。過期不傳送，另有到期清理工作；不使用 push 補送。
  LINE reply token 單次使用，程序中斷後即使重跑亦不會重複成功送出；回覆失敗不安排一般延遲重試。
  回覆文案提供中英文，Webhook 使用系統預設中文。
- 原文、分組、去重摘要及圖片工作在同一個交易保存，提交成功才回覆 LINE。
  請開啟 LINE 重送；LINE 的投遞與重送本身不保證永不漏訊息，見
  [Webhook 官方說明](https://developers.line.biz/en/docs/messaging-api/receiving-messages/)。

## 圖片、撤回與保留期限

- `line-collector` 在背景向 LINE 下載原圖，不在 Webhook 等圖片。單張最多 15 MiB，
  依實際內容驗證 JPEG、PNG、WebP、HEIC，沿用商品暫存的原圖保存及檔案清理。
  請及時處理，LINE 的內容下載有保存期限，不是永久的備份來源。
- 下載與名稱查詢最多嘗試三次，由工作佇列安排間隔。下載最終失敗會把照片標成 failed，
  保留原有分組；無論下載是否成功，已放棄／撤回的訊息不能被背景工作重新建立。
  程序強制中止時依佇列持有期限恢復，詳見[背景工作](../extending/background-jobs.md)。
- 撤回事件即使在群組停用後仍處理。暫存內的該則原文與照片關聯立即移除，
  實體圖片由背景清理工作刪除；先收到撤回、後收到原訊息時，也不重新收集。
- 已審核的商品不自動刪除或更改，群組回傳 `review_product_id` 供群組設定頁提示人工確認；訊息移到其他暫存再審核，也追蹤實際建立的商品。
- 事件與訊息防重送摘要保存 30 天，由背景工作到期刪除。只保存 SHA-256、處理關聯與期限，
  不另外保存原始 Webhook、傳送者或文字；指令回覆的短期 reply token 例外如上；下載用外部訊息 ID 在工作結束後清掉。
  過期後不保證辨認舊重送或撤回；既有備份依備份策略淘汰。

## 排查

| 情況 | 檢查 |
|---|---|
| Verify 回應 503 | 兩項 LINE 金鑰是否都設定，且 `make start` 已更新 API 容器 |
| Verify 回應 401 | Channel secret 是否屬於同一個 channel，代理是否改寫 body |
| 找不到群組 | Bot 是否已加入、Use webhook 是否開啟、HTTPS 是否能從外部連入 |
| 名稱暫時空白 | Access token 是否有效，Bot 是否仍在群組；查看 `make services logs line-collector` |
| 收不到商品 | 群組是否啟用並已 /start、訊息是否在批次區間內且先有圖片，及收集程序是否 healthy |
| 圖片 failed | 權杖／LINE 連線、圖片格式與大小、LINE 內容保存期限及 uploads 磁碟 |

Log 僅提供工作識別與錯誤類別，不輸出 LINE 錯誤內容或金鑰。

## 切換既有資料

此版 migration 保留商品暫存、原文、圖片與歷史待歸類資料，回填第一張圖片的原始時間（沒有圖片則使用暫存建立時間）。
原本收集中暫存會結束收集並增加版本；所有群組在新流程等待 `/start`，不從既有訊息推測開批次。

## 程式與測試

- 收件與群組 API：[`router.py`](../../apps/api/modules/line_collection/router.py)
- 交易與群組規則：[`service.py`](../../apps/api/modules/line_collection/service.py)
- 下載與重試：[`jobs.py`](../../apps/api/modules/line_collection/jobs.py)
- 收件、併發、撤回與回滾：[`test_integration.py`](../../apps/api/tests/modules/line_collection/test_integration.py)
- 簽章與設定：[`test_rules.py`](../../apps/api/tests/modules/line_collection/test_rules.py)
- nginx 實際入口：[`line-webhook.spec.ts`](../../e2e/tests/line-webhook.spec.ts)

- 批次指令與延遲事件：[`test_batches.py`](../../apps/api/tests/modules/line_collection/test_batches.py)

- 指令回覆生命週期：[`test_reply_jobs.py`](../../apps/api/tests/modules/line_collection/test_reply_jobs.py)
