import { expect, test, type BrowserContext, type Page } from "@playwright/test"
import { admin, login } from "./support"

test.describe.configure({ mode: "serial" })
const prefix = "Remember Item"
const brand = "Remember Brand"
let sessionCookies: Awaited<ReturnType<BrowserContext["cookies"]>> = []

async function openFilters(page: Page) {
  await page.locator("header").getByRole("button", { name: "操作選單", exact: true }).click()
  await page.getByRole("menuitem", { name: "篩選", exact: true }).click()
  return page.getByRole("dialog", { name: "搜尋", exact: true })
}

async function seedProducts(page: Page) {
  await page.goto("/brands")
  await page.getByRole("button", { name: "新增品牌", exact: true }).click()
  const dialog = page.getByRole("dialog")
  await dialog.getByLabel(/^名稱\*?$/).fill(brand)
  await dialog.getByRole("button", { name: "儲存", exact: true }).click()
  await expect(dialog).toBeHidden()
  for (let index = 0; index < 23; index++) {
    await page.goto("/products/new")
    await page.getByLabel(/^名稱\*?$/).fill(`${prefix} ${index}`)
    await page.getByRole("combobox", { name: /^品牌\*?$/ }).selectOption({ label: brand })
    await page.getByRole("combobox", { name: /^分類\*?$/ }).selectOption("包包")
    await page.getByLabel("顏色", { exact: true }).fill("black")
    await page.getByLabel("年份", { exact: true }).fill("2026")
    await page.getByLabel(/^成本（新臺幣）\*?$/).fill("3000")
    await page.getByRole("button", { name: "儲存", exact: true }).click()
    await expect(page).toHaveURL(/\/products\/[0-9a-f-]+$/)
  }
}

test("商品篩選在重整與同裝置重新開啟後保留且可清除", async ({ page, browser }) => {
  test.setTimeout(180_000)
  await login(page, admin)
  sessionCookies = await page.context().cookies()
  await seedProducts(page)
  await page.goto("/products")
  let dialog = await openFilters(page)
  await dialog.getByLabel("名稱、SKU 或序號", { exact: true }).fill(prefix)
  await dialog.getByRole("combobox", { name: "品牌", exact: true }).selectOption({ label: brand })
  await dialog.getByRole("combobox", { name: "分類", exact: true }).selectOption("包包")
  await dialog.getByRole("combobox", { name: "狀態", exact: true }).selectOption("not_acquired")
  await dialog.getByLabel("顏色", { exact: true }).fill("black")
  await dialog.getByLabel("年份", { exact: true }).fill("2026")
  await dialog.getByRole("button", { name: "篩選", exact: true }).click()
  await expect(page).toHaveURL(/keyword=Remember/)
  const filteredUrl = page.url()
  await page.reload()
  await expect(page).toHaveURL(filteredUrl)
  dialog = await openFilters(page)
  await expect(dialog.getByLabel("名稱、SKU 或序號", { exact: true })).toHaveValue(prefix)
  await expect(dialog.getByLabel("年份", { exact: true })).toHaveValue("2026")
  await dialog.getByRole("button", { name: "關閉", exact: true }).click()
  const reopened = await browser.newContext({ storageState: await page.context().storageState(),
    locale: "zh-TW" })
  try {
    const next = await reopened.newPage()
    await next.goto(new URL("/products", filteredUrl).href)
    await expect(next).toHaveURL(filteredUrl)
    await next.goto(new URL("/products?keyword=explicit", filteredUrl).href)
    dialog = await openFilters(next)
    await expect(dialog.getByLabel("名稱、SKU 或序號", { exact: true })).toHaveValue("explicit")
    await dialog.getByRole("button", { name: "重置", exact: true }).click()
    await dialog.getByRole("button", { name: "篩選", exact: true }).click()
    await expect(next).toHaveURL(new URL("/products", filteredUrl).href)
    await next.goto(new URL("/vendors", filteredUrl).href)
    await next.goto(new URL("/products", filteredUrl).href)
    dialog = await openFilters(next)
    await expect(dialog.getByLabel("名稱、SKU 或序號", { exact: true })).toHaveValue("")
  } finally { await reopened.close() }
})

test("手機從續載商品詳情返回時恢復條件與位置，支援上一頁及詳情重整", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.context().addCookies(sessionCookies)
  await page.goto(`/products?keyword=${encodeURIComponent(prefix)}`)
  const links = page.getByRole("link").filter({ hasText: prefix })
  await expect(links).toHaveCount(20)
  await links.last().scrollIntoViewIfNeeded()
  await page.getByRole("main").evaluate(() => window.scrollTo(0, document.body.scrollHeight))
  await expect(links).toHaveCount(23)
  const target = links.last()
  const detailHref = await target.getAttribute("href")
  const restored = links.and(page.locator(`[href="${detailHref}"]`))
  const row = page.getByRole("row").filter({ has: restored })
  await target.scrollIntoViewIfNeeded()
  const offset = await row.evaluate((element) => element.getBoundingClientRect().top)
  await target.click()
  await expect(page).toHaveURL(/\/products\/[0-9a-f-]+$/)
  await page.goBack()
  await expect(links).toHaveCount(23)
  await expect(restored).toBeInViewport()
  await expect.poll(async () => Math.abs(await row
    .evaluate((element) => element.getBoundingClientRect().top) - offset)).toBeLessThan(5)
  await restored.click()
  await expect(page).toHaveURL(/\/products\/[0-9a-f-]+$/)
  await page.reload()
  await page.getByRole("link", { name: "返回商品列表", exact: true }).click()
  await expect(page).toHaveURL(/keyword=Remember/)
  await expect(links).toHaveCount(23)
  await expect(restored).toBeInViewport()
})

test("桌面商品詳情返回時保留篩選及原分頁", async ({ page }) => {
  await page.context().addCookies(sessionCookies)
  await page.goto(`/products?keyword=${encodeURIComponent(prefix)}`)
  await page.getByRole("link", { name: /下一頁/ }).click()
  await expect(page).toHaveURL(/seq=2/)
  const listUrl = page.url()
  await page.getByRole("link").filter({ hasText: prefix }).last().click()
  await page.getByRole("link", { name: "返回商品列表", exact: true }).click()
  await expect(page).toHaveURL(listUrl)
  await expect(page.getByRole("link").filter({ hasText: prefix })).toHaveCount(3)
})

test("手機表單輸入文字至少十六像素且允許手動縮放", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto("/login")
  const account = page.getByLabel("帳號", { exact: true })
  await expect(account).toBeVisible()
  expect(await account.evaluate((input) => parseFloat(getComputedStyle(input).fontSize)))
    .toBeGreaterThanOrEqual(16)
  await page.context().addCookies(sessionCookies)
  await page.goto("/products/new")
  for (const control of [page.getByLabel(/^名稱\*?$/),
    page.getByRole("combobox", { name: /^品牌\*?$/ }),
    page.getByLabel("備註", { exact: true })]) {
    expect(await control.evaluate((input) => parseFloat(getComputedStyle(input).fontSize)))
      .toBeGreaterThanOrEqual(16)
  }
  const viewport = await page.locator('meta[name="viewport"]').getAttribute("content")
  expect(viewport).not.toMatch(/user-scalable\s*=\s*(no|0)|maximum-scale\s*=\s*1(?:\D|$)/)
})
