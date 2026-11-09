import { expect } from "@playwright/test"
import { test } from "./support"

test.use({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true })

test("觸控裝置開啟表單不自動聚焦且輸入字級至少 16px", async ({ page }) => {
  await page.goto("/admin/users")
  await page.getByRole("button", { name: "新增員工", exact: true }).click()
  const dialog = page.getByRole("dialog")
  const controls = dialog.locator("input:not([type=hidden]), select")
  await expect(controls.first()).toBeVisible()
  const states = await controls.evaluateAll((elements) => elements.map((element) => ({
    focused: element === document.activeElement,
    fontSize: Number.parseFloat(getComputedStyle(element).fontSize),
  })))
  expect(states.length).toBeGreaterThan(0)
  for (const state of states) {
    expect(state.focused).toBe(false)
    expect(state.fontSize).toBeGreaterThanOrEqual(16)
  }
})
