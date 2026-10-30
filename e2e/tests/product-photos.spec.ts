import { expect, test, type Page } from "@playwright/test"
import { admin, login, logout } from "./support"

const png = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAABAAAAAICAIAAAB/FOjAAAAAFklEQVR4nGP8z0AaYCJRPcOoBgYiAACTUAEPHJZO1QAAAABJRU5ErkJggg==", "base64")
const photo = (name: string) => ({ name, mimeType: "image/png", buffer: png })

async function prepareProduct(page: Page, name: string) {
  await login(page, admin)
  await page.goto("/brands")
  await page.getByRole("button", { name: "新增品牌", exact: true }).click()
  const dialog = page.getByRole("dialog")
  await dialog.getByLabel(/^名稱\*?$/).fill(name)
  await dialog.getByRole("button", { name: "儲存", exact: true }).click()
  await expect(dialog).toBeHidden()
  await page.goto("/products/new")
  await page.getByLabel(/^名稱\*?$/).fill(name)
  await page.getByRole("combobox", { name: /^品牌\*?$/ }).selectOption({ label: name })
  await page.getByRole("combobox", { name: /^分類\*?$/ }).selectOption("包包")
  await page.getByLabel(/^成本（新臺幣）\*?$/).fill("100")
}

test("商品照片支援選檔拍照主圖刪除與登入保護的原圖下載", async ({ page }) => {
  await prepareProduct(page, "Phase4 Photos")
  await page.getByLabel("上傳", { exact: true }).setInputFiles(photo("front.png"))
  await page.getByLabel("直接拍照", { exact: true }).setInputFiles(photo("camera.png"))
  await expect(page.getByRole("img", { name: "front.png", exact: true })).toBeVisible()
  await expect(page.getByRole("img", { name: "camera.png", exact: true })).toBeVisible()
  await page.getByRole("button", { name: "儲存", exact: true }).click()
  await expect(page).toHaveURL(/\/products\/[0-9a-f-]+$/)
  await page.setViewportSize({ width: 390, height: 844 })
  await page.getByRole("button", { name: "查看商品照片", exact: true }).click()
  const gallery = page.getByRole("dialog", { name: "商品照片", exact: true })
  const images = gallery.getByRole("img", { name: /預覽商品照片/ })
  await expect(images).toHaveCount(2)
  await expect(images.first()).toHaveJSProperty("naturalWidth", 640)
  const first = await images.first().getAttribute("src")
  const download = await gallery.getByRole("link", { name: "下載原圖", exact: true }).first().getAttribute("href")
  expect(download).toBeTruthy()
  const response = await page.request.get(download!)
  expect(response.status()).toBe(200)
  expect(response.headers()["content-type"]).toBe("image/png")
  expect(response.headers()["cache-control"]).toBe("private, no-store")
  expect(response.headers()["vary"]).toBe("Cookie")
  expect(response.headers()["content-disposition"]).toContain("attachment;")
  expect(await response.body()).toEqual(png)
  await gallery.getByRole("button", { name: "設為主圖", exact: true }).click()
  await expect(images.first()).not.toHaveAttribute("src", first!)
  await gallery.getByRole("button", { name: "刪除", exact: true }).click()
  let confirm = page.getByRole("dialog", { name: "刪除", exact: true })
  await confirm.getByRole("button", { name: "取消", exact: true }).click()
  await expect(images).toHaveCount(2)
  await gallery.getByRole("button", { name: "刪除", exact: true }).click()
  confirm = page.getByRole("dialog", { name: "刪除", exact: true })
  await confirm.getByRole("button", { name: "刪除", exact: true }).click()
  await expect(images).toHaveCount(1)
  await gallery.getByRole("button", { name: "關閉", exact: true }).click()
  expect((await page.request.get("/api/products/?limit=20")).status()).toBe(404)
  await page.setViewportSize({ width: 1280, height: 900 })
  await logout(page)
  expect((await page.request.get(download!)).status()).toBe(401)
})

test("照片失敗保留商品並可移除後補傳而不重複建檔", async ({ page }) => {
  await prepareProduct(page, "Phase4 Retry")
  await page.getByLabel("上傳", { exact: true }).setInputFiles({
    name: "invalid.png", mimeType: "image/png", buffer: Buffer.from("invalid image"),
  })
  await page.getByRole("button", { name: "儲存", exact: true }).click()
  await expect(page.getByRole("alert").filter({ hasText: "請選擇有效的 JPEG、PNG、WebP 或 HEIC 照片" })).toBeVisible()
  await expect(page.getByLabel(/^名稱\*?$/)).toBeDisabled()
  const detail = await page.getByRole("link", { name: "商品詳情", exact: true }).getAttribute("href")
  expect(detail).toMatch(/^\/products\/[0-9a-f-]+$/)
  await page.getByRole("button", { name: "移除照片", exact: true }).click()
  await page.getByLabel("上傳", { exact: true }).setInputFiles(photo("retry.png"))
  await page.getByRole("button", { name: "繼續儲存照片", exact: true }).click()
  await expect(page).toHaveURL(detail!)
  await page.goto("/products?keyword=Phase4%20Retry")
  await expect(page.getByRole("link").filter({ hasText: "Phase4 Retry" })).toHaveCount(1)
})

test("商品照片依顯示尺寸載入且點擊開啟原始解析度全圖", async ({ page }) => {
  const name = "Sized Preview Bag"
  await prepareProduct(page, name)
  const encoded = await page.evaluate(() => {
    const canvas = document.createElement("canvas")
    canvas.width = 3000; canvas.height = 1800
    const drawing = canvas.getContext("2d")!
    drawing.fillStyle = "#1764c9"
    drawing.fillRect(0, 0, canvas.width, canvas.height)
    return canvas.toDataURL("image/png").split(",")[1]
  })
  await page.getByLabel("上傳", { exact: true }).setInputFiles({
    name: "large.png", mimeType: "image/png", buffer: Buffer.from(encoded, "base64"),
  })
  const requests: string[] = []
  page.on("request", (request) => {
    if (/\/api\/products\/photos\/[^/]+\/file/.test(request.url())) requests.push(request.url())
  })
  await page.getByRole("button", { name: "儲存", exact: true }).click()
  await expect(page).toHaveURL(/\/products\/[0-9a-f-]+$/)
  const overview = page.getByRole("img", { name, exact: true })
  await expect(overview).toHaveJSProperty("naturalWidth", 320)
  await expect(overview).toHaveAttribute("src", /\/file\?size=320$/)
  await page.getByRole("button", { name: "查看商品照片", exact: true }).click()
  const gallery = page.getByRole("dialog", { name: "商品照片", exact: true })
  const preview = gallery.getByRole("img", { name: /預覽商品照片/ })
  await expect(preview).toHaveJSProperty("naturalWidth", 640)
  const previewUrl = await preview.getAttribute("src")
  expect(previewUrl).toMatch(/\/file\?size=640$/)
  expect(requests.every((url) => new URL(url).searchParams.has("size"))).toBe(true)
  const opening = page.waitForEvent("popup")
  await gallery.getByRole("link", { name: /預覽商品照片/ }).click()
  const full = await opening
  await expect(full.getByRole("img")).toHaveJSProperty("naturalWidth", 3000)
  await expect(full.getByRole("img")).toHaveJSProperty("naturalHeight", 1800)
  const fullUrl = full.url()
  expect(new URL(fullUrl).search).toBe("")
  expect((await page.request.get(fullUrl)).headers()["content-type"]).toBe("image/webp")
  await full.close()
  await gallery.getByRole("button", { name: "關閉", exact: true }).click()
  const thumbnail = page.waitForResponse((response) => response.url().includes("/file?size=128"))
  await page.goto(`/products?keyword=${encodeURIComponent(name)}`)
  expect((await thumbnail).status()).toBe(200)
  await logout(page)
  expect((await page.request.get(previewUrl!)).status()).toBe(401)
  expect((await page.request.get(fullUrl)).status()).toBe(401)
})
