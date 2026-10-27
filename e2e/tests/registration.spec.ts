import { expect, test, type Page } from "@playwright/test"
import { admin, login, logout } from "./support"

const firstKey = "e2e-first-manager-key"
const secondKey = "e2e-second-manager-key"
const registered = { username: "registered-manager", password: "registered-password" }
const staff = { username: "registration-staff", password: "registration-staff-password" }

async function signup(page: Page, username: string, key: string) {
  await page.goto("/signup")
  await page.getByLabel(/^暱稱\*?$/).fill("註冊店長")
  await page.getByLabel(/^帳號\*?$/).fill(username)
  await page.getByLabel(/^密碼\*?$/).fill(registered.password)
  await page.getByLabel(/^確認密碼\*?$/).fill(registered.password)
  await page.getByLabel(/^註冊碼\*?$/).fill(key)
  await page.getByRole("button", { name: "註冊店長", exact: true }).click()
}

test("註冊碼控制店長註冊且換碼立即生效", async ({ page, context }) => {
  await signup(page, registered.username, firstKey)
  await expect(page.getByRole("alert").filter({ hasText: "註冊碼錯誤或尚未設定" }))
    .toContainText("註冊碼錯誤或尚未設定")

  await login(page, admin)
  await page.goto("/admin/registration")
  await expect(page.getByText("尚未設定，公開註冊目前無法使用")).toBeVisible()
  await page.getByLabel("新的註冊碼").fill(firstKey)
  await page.getByRole("button", { name: "儲存註冊碼", exact: true }).click()
  await expect(page.getByRole("status")).toContainText("註冊碼已更新")
  await expect(page.getByLabel("新的註冊碼")).toHaveValue("")
  await logout(page)

  await signup(page, registered.username, firstKey)
  await expect(page.getByRole("status")).toContainText("店長帳號已建立")
  expect((await context.cookies()).some((cookie) => cookie.name === "access_token")).toBe(false)
  await login(page, registered)
  await page.goto("/admin/registration")
  await expect(page.getByText("已設定註冊碼", { exact: true })).toBeVisible()
  await page.getByLabel("新的註冊碼").fill(secondKey)
  await page.getByRole("button", { name: "儲存註冊碼", exact: true }).click()
  await expect(page.getByRole("status")).toContainText("註冊碼已更新")
  await logout(page)

  await signup(page, "rotated-manager", firstKey)
  await expect(page.getByRole("alert").filter({ hasText: "註冊碼錯誤或尚未設定" }))
    .toContainText("註冊碼錯誤或尚未設定")
  await signup(page, "rotated-manager", secondKey)
  await expect(page.getByRole("status")).toContainText("店長帳號已建立")
})

test("員工不能進入註冊碼設定且店長新增員工不提供角色指派", async ({ page }) => {
  await login(page, admin)
  await page.goto("/admin/users")
  await expect(page.getByRole("link", { name: "角色", exact: true })).toHaveCount(0)
  await page.getByRole("button", { name: "新增員工", exact: true }).click()
  const dialog = page.getByRole("dialog")
  await expect(dialog.getByRole("combobox")).toHaveCount(0)
  await dialog.getByLabel("暱稱").fill("註冊測試員工")
  await dialog.getByLabel("帳號").fill(staff.username)
  await dialog.getByLabel(/^密碼\*?$/).fill(staff.password)
  await dialog.getByRole("button", { name: "建立", exact: true }).click()
  await expect(dialog).toBeHidden()
  const row = page.getByRole("row").filter({ hasText: "註冊測試員工" })
  await expect(row.getByRole("cell", { name: "員工", exact: true })).toBeVisible()
  await logout(page)
  await login(page, staff)
  await page.goto("/admin/registration")
  await expect(page).toHaveURL("/")
  await expect(page.getByRole("link", { name: "註冊碼設定", exact: true })).toHaveCount(0)
})
