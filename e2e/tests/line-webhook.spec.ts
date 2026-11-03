import { expect, test } from "@playwright/test"
import { SIGNED_OUT } from "./support"

// 驗證的是未登入的外部呼叫, 不載入預設的超管登入狀態。
test.use({ storageState: SIGNED_OUT })

test("LINE Webhook 可經 nginx 呼叫且群組管理 API 不對外公開", async ({ request }) => {
  const webhook = await request.post("/api/line/webhook", { data: { events: [] } })
  expect([401, 503]).toContain(webhook.status())
  expect(webhook.headers()["x-request-id"]).toBeTruthy()
  const groups = await request.get("/api/line/groups", { maxRedirects: 0 })
  expect([307, 404]).toContain(groups.status())
})
