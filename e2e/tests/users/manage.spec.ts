import { randomUUID } from "node:crypto"
import { expect } from "@playwright/test"
import { SIGNED_OUT, createUser, login, test } from "../support"

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




test("停用再啟用帳號後，舊登入仍失效且可重新登入", async ({ browser, page }) => {
  const account = await createUser(browser, "reactivate")
  const device = await browser.newContext({ storageState: SIGNED_OUT })
  try {
    const memberPage = await device.newPage()
    await login(memberPage, account)
    await page.goto(`/admin/users?name=${encodeURIComponent(account.nickname)}`)
    const row = page.getByRole("row").filter({ hasText: account.nickname })

    for (const status of ["disabled", "active"]) {
      await row.getByRole("button", { name: "操作選單" }).click()
      await page.getByRole("menuitem", { name: "編輯", exact: true }).click()
      const dialog = page.getByRole("dialog")
      await dialog.getByLabel("狀態").selectOption(status)
      await dialog.getByRole("button", { name: "儲存", exact: true }).click()
      await expect(dialog).toBeHidden()
      await expect(row.getByText(status === "disabled" ? "已停用" : "啟用中", { exact: true }))
        .toBeVisible()
    }

    // 啟用之後才使用舊 cookie, 才能區分撤銷 session 與單純拒絕停用中的帳號.
    await memberPage.goto("/settings")
    await expect(memberPage).toHaveURL(/\/login/)
    await login(memberPage, account)
    await memberPage.goto("/settings")
    await expect(memberPage).toHaveURL("/settings")
  } finally {
    await device.close()
  }
})


test("新增與編輯使用者及重設密碼的錯誤顯示在欄位", async ({ page, browser }) => {
  const account = await createUser(browser, "field-errors")
  await page.goto(`/admin/users?name=${encodeURIComponent(account.nickname)}`)
  await page.getByRole("button", { name: "新增員工", exact: true }).click()
  let dialog = page.getByRole("dialog")
  await dialog.getByRole("button", { name: "建立", exact: true }).click()
  for (const label of [/^暱稱/, /^帳號/, /^密碼/]) {
    await expect(dialog.getByLabel(label)).toHaveAttribute("aria-invalid", "true")
  }
  await dialog.getByLabel(/^暱稱/).fill("測試")
  await dialog.getByLabel(/^帳號/).fill("not-submitted")
  await dialog.getByLabel(/^密碼/).fill("short")
  await dialog.getByRole("button", { name: "建立", exact: true }).click()
  await expect(dialog.getByLabel(/^密碼/)).toHaveAttribute("aria-invalid", "true")
  await dialog.getByRole("button", { name: "取消", exact: true }).click()

  const row = page.getByRole("row").filter({ hasText: account.nickname })
  await row.getByRole("button", { name: "操作選單" }).click()
  await page.getByRole("menuitem", { name: "編輯", exact: true }).click()
  dialog = page.getByRole("dialog")
  await dialog.getByLabel(/^暱稱/).fill(" ")
  await dialog.getByRole("button", { name: "儲存", exact: true }).click()
  await expect(dialog.getByLabel(/^暱稱/)).toHaveAttribute("aria-invalid", "true")
  await dialog.getByRole("button", { name: "取消", exact: true }).click()

  await row.getByRole("button", { name: "操作選單" }).click()
  await page.getByRole("menuitem", { name: "重設密碼", exact: true }).click()
  dialog = page.getByRole("dialog")
  await dialog.getByLabel(/^新密碼/).fill("short")
  await dialog.getByRole("button", { name: "重設密碼", exact: true }).click()
  await expect(dialog.getByLabel(/^新密碼/)).toHaveAttribute("aria-invalid", "true")
})

test("新增使用者與重設密碼的密碼欄位標成新密碼", async ({ page, browser }) => {
  const account = await createUser(browser, "autocomplete")
  await page.goto(`/admin/users?name=${encodeURIComponent(account.nickname)}`)
  await page.getByRole("button", { name: "新增員工", exact: true }).click()
  let dialog = page.getByRole("dialog")
  await expect(dialog.getByLabel(/^密碼/)).toHaveAttribute("autocomplete", "new-password")
  await dialog.getByRole("button", { name: "取消", exact: true }).click()
  await page.getByRole("row").filter({ hasText: account.nickname })
    .getByRole("button", { name: "操作選單" }).click()
  await page.getByRole("menuitem", { name: "重設密碼", exact: true }).click()
  dialog = page.getByRole("dialog")
  await expect(dialog.getByLabel(/^新密碼/)).toHaveAttribute("autocomplete", "new-password")
})
