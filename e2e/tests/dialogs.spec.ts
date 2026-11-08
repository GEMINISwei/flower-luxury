import { expect } from "@playwright/test"
import { test } from "./support"

test("對話框 Tab 循環且 Escape 還原新增按鈕焦點", async ({ page }) => {
  await page.goto("/admin/users")
  const trigger = page.getByRole("button", { name: "新增員工", exact: true })
  await trigger.click()
  const dialog = page.getByRole("dialog")
  await expect(dialog.getByLabel(/^暱稱/)).toBeFocused()
  const first = dialog.getByRole("button", { name: "關閉", exact: true })
  const last = dialog.getByRole("button", { name: "建立", exact: true })
  await last.focus()
  await page.keyboard.press("Tab")
  await expect(first).toBeFocused()
  await page.keyboard.press("Shift+Tab")
  await expect(last).toBeFocused()
  await page.keyboard.press("Escape")
  await expect(dialog).toBeHidden()
  await expect(trigger).toBeFocused()
})

test("帳號選單支援方向鍵與 Escape 焦點還原", async ({ page }) => {
  await page.goto("/products")
  const trigger = page.getByRole("button", { name: "帳號選單", exact: true })
  await trigger.click()
  const first = page.getByRole("menuitem", { name: "用戶設定", exact: true })
  await expect(first).toBeFocused()
  await page.keyboard.press("ArrowUp")
  await expect(page.getByRole("menuitem", { name: "登出", exact: true })).toBeFocused()
  await page.keyboard.press("ArrowDown")
  await expect(first).toBeFocused()
  await page.keyboard.press("Escape")
  await expect(page.getByRole("menu")).toBeHidden()
  await expect(trigger).toBeFocused()
})

test.describe("英文欄位驗證", () => {
  test.use({ locale: "en-US" })
  test("英文新增員工錯誤依應用語系顯示在各自欄位", async ({ page }) => {
    await page.goto("/admin/users")
    await page.getByRole("button", { name: "New staff member", exact: true }).click()
    const dialog = page.getByRole("dialog")
    await dialog.getByRole("button", { name: "Create", exact: true }).click()
    for (const label of [/^Display name/, /^Username/, /^Password/]) {
      await expect(dialog.getByLabel(label)).toHaveAttribute("aria-invalid", "true")
    }
    await expect(dialog.getByText("Username is required", { exact: true })).toBeVisible()
    await expect(dialog.getByText("Display name is required", { exact: true })).toBeVisible()
  })
})
