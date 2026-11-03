import { test as setup } from "@playwright/test"
import { ADMIN_STATE, admin, login } from "./support"

// 其他測試開始前跑一次 (playwright.config.ts 的 setup project): 超管只從畫面登入這一次,
// 之後的測試直接載入存下來的登入狀態。
setup("超管登入並保存登入狀態", async ({ page }) => {
  await login(page, admin)
  // 語系 cookie 不存: 載入這份狀態的測試各自用 locale 設定 (例如英文案例), 由 proxy 重新判斷語系。
  await page.context().clearCookies({ name: "locale" })
  await page.context().storageState({ path: ADMIN_STATE })
})
