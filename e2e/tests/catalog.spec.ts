import { expect, test, type Page } from "@playwright/test"
import { login, logout, useAdmin } from "./support"

const staff = { username: "catalog-staff", password: "catalog-staff-password" }

// 預設載入超管的登入狀態 (playwright.config.ts)。
async function createStaff(page: Page) {
  await page.goto("/admin/users")
  await page.getByRole("button", { name: "新增員工", exact: true }).click()
  const dialog = page.getByRole("dialog")
  await dialog.getByLabel("暱稱").fill("目錄員工")
  await dialog.getByLabel("帳號").fill(staff.username)
  await dialog.getByLabel(/^密碼\*?$/).fill(staff.password)
  await dialog.getByRole("button", { name: "建立", exact: true }).click()
  await expect(dialog).toBeHidden()
}

test("員工共用品牌與廠商且取消刪除不改資料", async ({ page }) => {
  await createStaff(page)
  // 直接換成員工登入, 不登出超管: 登出會撤銷超管在其他 worker 的 session。
  await login(page, staff)
  await page.goto("/brands")
  await page.getByRole("button", { name: "新增品牌", exact: true }).click()
  let dialog = page.getByRole("dialog")
  await dialog.getByLabel(/^名稱\*?$/).fill(" Phase2 Brand ")
  await dialog.getByRole("button", { name: "儲存", exact: true }).click()
  await expect(dialog).toBeHidden()
  let row = page.getByRole("row").filter({ hasText: "Phase2 Brand" })
  await expect(row.getByRole("cell", { name: "Phase2 Brand", exact: true })).toBeVisible()
  await row.getByRole("button", { name: "刪除", exact: true }).click()
  dialog = page.getByRole("dialog", { name: "刪除", exact: true })
  await dialog.getByRole("button", { name: "取消", exact: true }).click()
  await expect(row).toBeVisible()

  await page.goto("/vendors")
  await page.getByRole("button", { name: "新增廠商", exact: true }).click()
  dialog = page.getByRole("dialog")
  await dialog.getByLabel(/^名稱\*?$/).fill("Phase2 Vendor")
  await dialog.getByLabel("備註", { exact: true }).fill("Shared vendor")
  await dialog.getByRole("button", { name: "儲存", exact: true }).click()
  await expect(dialog).toBeHidden()
  row = page.getByRole("row").filter({ hasText: "Phase2 Vendor" })
  await expect(row.getByRole("cell", { name: "Shared vendor", exact: true })).toBeVisible()
  await expect(page.getByRole("columnheader", { name: "國家", exact: true })).toHaveCount(0)
  await row.getByRole("button", { name: "編輯", exact: true }).click()
  dialog = page.getByRole("dialog")
  await dialog.getByLabel("備註", { exact: true }).fill("Updated vendor")
  await dialog.getByRole("combobox", { name: "狀態", exact: true }).selectOption("false")
  await dialog.getByRole("button", { name: "儲存", exact: true }).click()
  await expect(dialog).toBeHidden()
  await expect(row.getByRole("cell", { name: "停用", exact: true })).toBeVisible()
  await logout(page)

  await useAdmin(page.context())
  await page.goto("/brands")
  row = page.getByRole("row").filter({ hasText: "Phase2 Brand" })
  await row.getByRole("button", { name: "刪除", exact: true }).click()
  dialog = page.getByRole("dialog", { name: "刪除", exact: true })
  await dialog.getByRole("button", { name: "刪除", exact: true }).click()
  await expect(row).toHaveCount(0)
  await page.goto("/vendors")
  row = page.getByRole("row").filter({ hasText: "Phase2 Vendor" })
  await expect(row.getByRole("cell", { name: "Updated vendor", exact: true })).toBeVisible()
  await row.getByRole("button", { name: "刪除", exact: true }).click()
  await page.getByRole("dialog").getByRole("button", { name: "刪除", exact: true }).click()
  await expect(row).toHaveCount(0)
})

test("廠商不需要國家且管理區不再有匯率設定", async ({ page }) => {
  await page.goto("/admin/users")
  await expect(page.getByRole("link", { name: "匯率設定", exact: true })).toHaveCount(0)
  await page.goto("/vendors")
  await page.getByRole("button", { name: "新增廠商", exact: true }).click()
  const dialog = page.getByRole("dialog")
  await expect(dialog.getByLabel("國家", { exact: true })).toHaveCount(0)
  await expect(dialog.getByLabel("幣別", { exact: true })).toHaveCount(0)
  await dialog.getByRole("button", { name: "取消", exact: true }).click()
})

test("手機更多可開關並提供兩種設定與管理區入口", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto("/brands")
  const nav = page.getByRole("navigation", { name: "手機主要導覽", exact: true })
  await expect(nav.getByRole("link", { name: "品牌", exact: true })).toBeVisible()
  await expect(nav.getByRole("link", { name: "廠商", exact: true })).toBeVisible()
  const more = nav.getByRole("button", { name: "更多", exact: true })
  await more.click()
  let dialog = page.getByRole("dialog", { name: "更多", exact: true })
  await expect(dialog.getByText("店長", { exact: true })).toBeVisible()
  await page.keyboard.press("Escape")
  await expect(dialog).toBeHidden()
  await expect(more).toBeFocused()
  await more.click()
  await dialog.getByRole("button", { name: "用戶設定", exact: true }).click()
  await expect(page).toHaveURL("/settings")
  await expect(page.getByRole("heading", { name: "用戶設定", exact: true })).toBeVisible()
  await more.click()
  await page.getByRole("dialog").getByRole("button", { name: "系統設定", exact: true }).click()
  await expect(page).toHaveURL("/settings/system")
  await expect(page.getByRole("heading", { name: "系統設定", exact: true })).toBeVisible()
  await more.click()
  dialog = page.getByRole("dialog", { name: "更多", exact: true })
  await dialog.getByRole("button", { name: "管理後台", exact: true }).click()
  await expect(page).toHaveURL("/admin/users")
})


for (const entry of [
  { path: "/brands", create: "新增品牌", error: "請輸入品牌名稱" },
  { path: "/vendors", create: "新增廠商", error: "請填寫廠商名稱" },
]) {
  test(`${entry.create}的空白名稱由應用驗證阻擋`, async ({ page }) => {
    await page.goto(entry.path)
    await page.getByRole("button", { name: entry.create, exact: true }).click()
    const dialog = page.getByRole("dialog")
    await dialog.getByRole("button", { name: "儲存", exact: true }).click()
    await expect(dialog).toBeVisible()
    await expect(dialog.getByText(entry.error, { exact: true })).toBeVisible()
  })
}
