import { randomUUID } from "node:crypto"
import { expect } from "@playwright/test"
import { SIGNED_OUT, createUser, login, logout, test } from "./support"

// 預設載入超管的登入狀態 (playwright.config.ts)。
test("店長新增員工後，列表看得到該員工", async ({ page }) => {
  const id = randomUUID().slice(0, 8)
  const nickname = `E2E 新員工 ${id}`
  await page.goto("/admin/users")

  await page.getByRole("button", { name: "新增員工" }).click()
  const dialog = page.getByRole("dialog")
  await dialog.getByLabel("暱稱").fill(nickname)
  await dialog.getByLabel("帳號").fill(`e2e-new-${id}`)
  await dialog.getByLabel("密碼").fill(`e2e-password-${id}`)
  await dialog.getByRole("button", { name: "建立", exact: true }).click()

  await expect(dialog).toBeHidden()
  // 員工列表一頁 10 筆、由舊到新; 平行跑時別的檔案也在建帳號, 用名稱篩選才不受分頁影響。
  await page.goto(`/admin/users?name=${encodeURIComponent(nickname)}`)
  // 列表在桌面寬度下沒有帳號欄, 以暱稱辨認。
  await expect(page.getByRole("cell", { name: nickname, exact: true })).toBeVisible()
})

test.describe("一般帳號", () => {
  test.use({ storageState: SIGNED_OUT })

  test("一般帳號進入管理區會被導回商品列表", async ({ page, member }) => {
    await login(page, member)

    await page.goto("/admin/users")

    await expect(page).toHaveURL("/products")
  })

  test("登出後其他已登入的裝置也會被登出", async ({ browser }) => {
    // 登出會撤銷這個帳號所有裝置的 session, 用 worker 共用的 member 會連累同一個 worker 之後的測試。
    const account = await createUser(browser, "logout")
    // 兩個 context 不共用 cookie, 等於兩台裝置。
    const deviceA = await browser.newContext({ storageState: SIGNED_OUT })
    const deviceB = await browser.newContext({ storageState: SIGNED_OUT })
    const pageA = await deviceA.newPage()
    const pageB = await deviceB.newPage()
    await login(pageA, account)
    await login(pageB, account)

    await logout(pageA)

    // B 的 cookie 還在, 擋下它的是後端的 auth_version 比對。
    await pageB.goto("/settings")
    await expect(pageB).toHaveURL(/\/login/)

    await deviceA.close()
    await deviceB.close()
  })
})
