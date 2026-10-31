import { readFile } from "node:fs/promises"
import { createHash } from "node:crypto"
import { fileURLToPath } from "node:url"
import { expect, test, type Page } from "@playwright/test"
import { admin } from "./support"

// 英文案例只覆寫本檔語系, 既有中文案例維持原設定.
test.use({ locale: "en-US" })

async function login(page: Page, account: { username: string; password: string }) {
  await page.goto("/login")
  await page.getByRole("textbox", { name: "Username", exact: true }).fill(account.username)
  await page.getByLabel("Password", { exact: true }).fill(account.password)
  await page.getByRole("button", { name: "Sign in", exact: true }).click()
  await expect(page).toHaveURL("/products")
}

async function logout(page: Page) {
  await page.getByRole("button", { name: "Account menu", exact: true }).click()
  await page.getByRole("menuitem", { name: "Sign out", exact: true }).click()
  await expect(page).toHaveURL(/\/login/)
}

const staff = { username: "english-lifecycle-staff", password: "english-lifecycle-staff-password" }
const productName = "English Lifecycle Bag"
const brandName = "English Lifecycle Brand"
const vendorName = "English Lifecycle Vendor"
const returnReason = "Returned for staff renegotiation"
const filenames = ["lifecycle-front.png", "lifecycle-back.png"]
const png = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAABAAAAAICAIAAAB/FOjAAAAAFklEQVR4nGP8z0AaYCJRPcOoBgYiAACTUAEPHJZO1QAAAABJRU5ErkJggg==", "base64")

async function prepareStaff(page: Page) {
  await login(page, admin)
  await page.goto("/admin/users")
  await page.getByRole("button", { name: "New staff member", exact: true }).click()
  const dialog = page.getByRole("dialog")
  await dialog.getByLabel(/^Display name\*?$/).fill("English workflow staff")
  await dialog.getByLabel(/^Username\*?$/).fill(staff.username)
  await dialog.getByLabel(/^Password\*?$/).fill(staff.password)
  await dialog.getByRole("button", { name: "Create", exact: true }).click()
  await expect(dialog).toBeHidden()
  await expect(page.getByRole("row").filter({ hasText: "English workflow staff" })
    .getByRole("cell", { name: "Staff", exact: true })).toBeVisible()
  await logout(page)
  await login(page, staff)
}

async function createCatalog(page: Page, brand = brandName, vendor = vendorName) {
  await page.goto("/brands")
  await page.getByRole("button", { name: "New brand", exact: true }).click()
  let dialog = page.getByRole("dialog")
  await dialog.getByLabel(/^Name\*?$/).fill(brand)
  await dialog.getByRole("button", { name: "Save", exact: true }).click()
  await expect(dialog).toBeHidden()
  await page.goto("/vendors")
  await page.getByRole("button", { name: "New vendor", exact: true }).click()
  dialog = page.getByRole("dialog")
  await dialog.getByLabel(/^Name\*?$/).fill(vendor)
  // 臺幣不需系統匯率, 單獨跑此案例也不依賴其他 spec 的設定.
  await dialog.getByRole("combobox", { name: /^Country\*?$/ }).selectOption("TW")
  await dialog.getByRole("button", { name: "Save", exact: true }).click()
  await expect(dialog).toBeHidden()
}

async function createProduct(page: Page) {
  await page.goto("/products/new")
  await page.getByLabel(/^Name\*?$/).fill(productName)
  await page.getByRole("combobox", { name: /^Brand\*?$/ }).selectOption({ label: brandName })
  await page.getByRole("combobox", { name: /^Category\*?$/ }).selectOption({ label: "Bags" })
  await page.getByLabel(/^Cost \(TWD\)\*?$/).fill("3100")
  await page.getByLabel("Upload", { exact: true }).setInputFiles(
    filenames.map((name) => ({ name, mimeType: "image/png", buffer: png })),
  )
  for (const name of filenames) {
    await expect(page.getByRole("img", { name, exact: true })).toHaveJSProperty("naturalWidth", 16)
  }
  await page.getByRole("button", { name: "Save", exact: true }).click()
  await expect(page).toHaveURL(/\/products\/[0-9a-f-]+$/)
  await expect(page.getByRole("heading", { name: productName, exact: true })).toBeVisible()
}

async function checkPhotos(page: Page, sources: string[], sold: boolean) {
  await expect(page.getByRole("img", { name: productName, exact: true }))
    .toHaveAttribute("src", sources[0].replace("?size=640", "?size=320"))
  await page.getByRole("button", { name: "View product photos", exact: true }).click()
  const gallery = page.getByRole("dialog", { name: "Product photos", exact: true })
  const images = gallery.getByRole("img", { name: /Preview product photo/ })
  await expect(images).toHaveCount(2)
  await expect(gallery.getByText("Main photo", { exact: true })).toBeVisible()
  for (const [index, source] of sources.entries()) {
    await expect(images.nth(index)).toHaveAttribute("src", source)
    await expect(images.nth(index)).toHaveJSProperty("naturalWidth", 640)
    const downloaded = page.waitForEvent("download")
    await gallery.getByRole("link", { name: "Download original", exact: true }).nth(index).click()
    const download = await downloaded
    expect(download.suggestedFilename()).toBe(filenames[index])
    const path = await download.path()
    expect(path).toBeTruthy()
    expect(await readFile(path!)).toEqual(png)
  }
  await expect(gallery.getByRole("button", { name: "Upload", exact: true })).toHaveCount(sold ? 0 : 1)
  await expect(gallery.getByRole("button", { name: "Take photo", exact: true })).toHaveCount(sold ? 0 : 1)
  await expect(gallery.getByRole("button", { name: "Set as main", exact: true })).toHaveCount(sold ? 0 : 1)
  await expect(gallery.getByRole("button", { name: "Delete", exact: true })).toHaveCount(sold ? 0 : 1)
  if (!sold) {
    for (const name of ["Upload", "Take photo", "Set as main", "Delete"]) {
      await expect(gallery.getByRole("button", { name, exact: true })).toBeEnabled()
    }
  }
  await gallery.getByRole("button", { name: "Close", exact: true }).click()
  await expect(gallery).toBeHidden()
}

async function confirmSale(page: Page) {
  await page.getByRole("button", { name: "Confirm sale", exact: true }).click()
  const dialog = page.getByRole("dialog", { name: "Confirm sale", exact: true })
  await dialog.getByRole("button", { name: "Confirm sale", exact: true }).click()
  await expect(dialog).toBeHidden()
  await expect(page.getByRole("button", { name: "Return status", exact: true })).toBeVisible()
  await expect(page.getByRole("button", { name: "Edit product", exact: true })).toHaveCount(0)
  await expect(page.getByRole("button", { name: "Delete product", exact: true })).toHaveCount(0)
  await expect(page.getByRole("button", { name: "New quote", exact: true })).toHaveCount(0)
  await expect(page.getByRole("button", { name: "Edit", exact: true })).toHaveCount(0)
  await expect(page.getByRole("button", { name: "Delete quote", exact: true })).toHaveCount(0)
  await expect(page.getByRole("button", { name: "Confirm sale", exact: true })).toHaveCount(0)
}

test("英文介面可完成員工商品照片與交易完整流程", async ({ page }) => {
  test.setTimeout(90_000)
  let detail = ""
  let sku = ""
  const sources: string[] = []

  await test.step("店長建立員工後由員工自行建立品牌廠商與帶照片的商品", async () => {
    await prepareStaff(page)
    await createCatalog(page)
    await createProduct(page)
    detail = page.url()
    sku = (await page.getByText(/^LX\d{8}[A-Z0-9]{5}$/).first().innerText()).trim()
    await page.getByRole("button", { name: "View product photos", exact: true }).click()
    const gallery = page.getByRole("dialog", { name: "Product photos", exact: true })
    const images = gallery.getByRole("img", { name: /Preview product photo/ })
    await expect(images).toHaveCount(2)
    for (const image of await images.all()) {
      const source = await image.getAttribute("src")
      expect(source).toMatch(/^\/api\/products\/photos\/[0-9a-f-]+\/file\?size=640$/)
      sources.push(source!)
    }
    await gallery.getByRole("button", { name: "Close", exact: true }).click()
    await checkPhotos(page, sources, false)
  })

  await test.step("員工新增詢價並成交後商品與照片唯讀且可下載原圖", async () => {
    await page.getByRole("button", { name: "New quote", exact: true }).click()
    const dialog = page.getByRole("dialog", { name: "New quote", exact: true })
    await dialog.getByRole("combobox", { name: /^Vendor\*?$/ })
      .selectOption({ label: `${vendorName} · Taiwan (TWD)` })
    await dialog.getByLabel(/^Original quote\*?$/).fill("1.01")
    await dialog.getByRole("button", { name: "Save", exact: true }).click()
    await expect(dialog.getByRole("alert")).toHaveText("TWD quotes must be whole numbers")
    await dialog.getByLabel(/^Original quote\*?$/).fill("5000")
    await dialog.getByRole("button", { name: "Save", exact: true }).click()
    await expect(dialog).toBeHidden()
    await expect(page.getByText("TWD 5,000", { exact: true })).toBeVisible()
    await confirmSale(page)
    await expect(page.getByText("Current sale", { exact: true })).toHaveCount(1)
    await expect(page.getByRole("definition")).toContainText(["5,000", "3,100", "1,900", staff.username])
    await checkPhotos(page, sources, true)
  })

  await test.step("員工填寫原因退回後恢復商品詢價與照片操作並保留舊成交", async () => {
    await page.getByRole("button", { name: "Return status", exact: true }).click()
    const dialog = page.getByRole("dialog", { name: "Return status", exact: true })
    await dialog.getByLabel(/^Return reason \(required\)\*?$/).fill("   ")
    await dialog.getByRole("button", { name: "Return status", exact: true }).click()
    await expect(dialog.getByRole("alert")).toHaveText("This field is required")
    await dialog.getByLabel(/^Return reason \(required\)\*?$/).fill(returnReason)
    await dialog.getByRole("button", { name: "Return status", exact: true }).click()
    await expect(dialog).toBeHidden()
    await expect(page.getByRole("button", { name: "Edit product", exact: true })).toBeVisible()
    await expect(page.getByRole("button", { name: "Delete product", exact: true })).toBeVisible()
    await expect(page.getByRole("button", { name: "New quote", exact: true })).toBeVisible()
    await expect(page.getByRole("button", { name: "Edit", exact: true })).toBeVisible()
    await expect(page.getByRole("button", { name: "Delete quote", exact: true })).toHaveCount(0)
    await expect(page.getByText("Current sale", { exact: true })).toHaveCount(0)
    await expect(page.getByText("Returned", { exact: true })).toHaveCount(1)
    await expect(page.getByText(returnReason, { exact: true })).toHaveCount(2)
    await checkPhotos(page, sources, false)
  })

  await test.step("員工修改成本與原詢價後再成交且舊快照不被覆寫", async () => {
    await page.getByRole("button", { name: "Edit product", exact: true }).click()
    let dialog = page.getByRole("dialog", { name: "Edit product", exact: true })
    await dialog.getByLabel(/^Cost \(TWD\)\*?$/).fill("3200")
    await dialog.getByRole("button", { name: "Save", exact: true }).click()
    await expect(dialog).toBeHidden()
    await page.getByRole("button", { name: "Edit", exact: true }).click()
    dialog = page.getByRole("dialog", { name: "Quote", exact: true })
    await dialog.getByLabel(/^Original quote\*?$/).fill("6500")
    await dialog.getByRole("button", { name: "Save", exact: true }).click()
    await expect(dialog).toBeHidden()
    await expect(page.getByText("TWD 6,500", { exact: true })).toBeVisible()
    await confirmSale(page)
    await expect(page.getByText("Current sale", { exact: true })).toHaveCount(1)
    await expect(page.getByText("Returned", { exact: true })).toHaveCount(1)
    await expect(page.getByRole("definition")).toContainText([
      "6,500", "3,200", "3,300", staff.username,
      "5,000", "3,100", "1,900", staff.username, returnReason,
    ])
  })

  await test.step("重新載入後同一商品與照片兩次成交及員工流向記錄仍保留", async () => {
    await page.reload()
    await expect(page).toHaveURL(detail)
    await expect(page.getByRole("heading", { name: productName, exact: true })).toBeVisible()
    await expect(page.getByText(sku, { exact: true }).first()).toBeVisible()
    await expect(page.getByText("Current sale", { exact: true })).toHaveCount(1)
    await expect(page.getByText("Returned", { exact: true })).toHaveCount(1)
    await expect(page.getByRole("definition")).toContainText([
      "6,500", "3,200", "3,300", staff.username,
      "5,000", "3,100", "1,900", staff.username, returnReason,
    ])
    await expect(page.getByRole("listitem").filter({ hasText: staff.username })).toContainText([
      "Not acquired", "Sold", returnReason, "Sold",
    ])
    await expect(page.getByRole("listitem").filter({ hasText: staff.username })).toHaveCount(4)
    await checkPhotos(page, sources, true)
    await page.getByRole("link", { name: "Back to products", exact: true }).click()
    await page.goto(`/products?keyword=${encodeURIComponent(sku)}`)
    const row = page.getByRole("row").filter({ hasText: sku })
    await expect(row).toHaveCount(1)
    await expect(row.getByRole("cell", { name: "Sold", exact: true })).toBeVisible()
    await row.getByRole("link").filter({ hasText: productName }).click()
    await expect(page).toHaveURL(detail)
  })
})

test("英文系統設定切換語系後重新登入仍保留選擇", async ({ page, context }) => {
  await login(page, admin)
  await page.goto("/settings/system")
  await expect(page.getByRole("heading", { name: "System settings", exact: true })).toBeVisible()
  await page.getByRole("combobox", { name: "Display language", exact: true }).selectOption("zh")
  await expect(page.getByRole("heading", { name: "系統設定", exact: true })).toBeVisible()
  await page.reload()
  await expect(page.getByRole("combobox", { name: "顯示語言", exact: true })).toHaveValue("zh")
  await page.getByRole("combobox", { name: "顯示語言", exact: true }).selectOption("en")
  await expect(page.getByRole("heading", { name: "System settings", exact: true })).toBeVisible()
  await page.reload()
  await expect(page.getByRole("combobox", { name: "Display language", exact: true })).toHaveValue("en")
  expect((await context.cookies()).find((cookie) => cookie.name === "locale")?.value).toBe("en")
  await logout(page)
  await page.getByRole("textbox", { name: "Username", exact: true }).fill(admin.username)
  await page.getByLabel("Password", { exact: true }).fill("incorrect-english-password")
  await page.getByRole("button", { name: "Sign in", exact: true }).click()
  await expect(page.getByRole("alert").filter({ hasText: "Invalid Username or Password" }))
    .toContainText("Invalid Username or Password")
  await login(page, admin)
  await page.goto("/settings/system")
  await expect(page.getByRole("heading", { name: "System settings", exact: true })).toBeVisible()
  await expect(page.getByRole("combobox", { name: "Display language", exact: true })).toHaveValue("en")
})

test("真實 HEIC 上傳可顯示且下載保留原始檔案", async ({ page }, testInfo) => {
  const fixture = fileURLToPath(new URL("./fixtures/IMG_2682.heic", import.meta.url))
  const original = await readFile(fixture)
  const expectedHash = "2d9d8493696fc0054ecb4517699fec11e04bf507f1f529f6a4f293fcefdeb35e"
  expect(createHash("sha256").update(original).digest("hex")).toBe(expectedHash)
  await login(page, admin)
  await createCatalog(page, "HEIC Sample Brand", "HEIC Sample Vendor")
  await page.goto("/products/new")
  await page.getByLabel(/^Name\*?$/).fill("HEIC Real Sample Bag")
  await page.getByRole("combobox", { name: /^Brand\*?$/ }).selectOption({ label: "HEIC Sample Brand" })
  await page.getByRole("combobox", { name: /^Category\*?$/ }).selectOption({ label: "Bags" })
  await page.getByLabel(/^Cost \(TWD\)\*?$/).fill("100")
  await page.getByLabel("Upload", { exact: true }).setInputFiles({
    name: "invalid.heic", mimeType: "image/heic", buffer: Buffer.from("invalid HEIC"),
  })
  await page.getByRole("button", { name: "Save", exact: true }).click()
  await expect(page.getByRole("alert").filter({ hasText: "Choose a valid" }))
    .toHaveText("Choose a valid JPEG, PNG, WebP or HEIC photo")
  await expect(page.getByLabel(/^Name\*?$/)).toBeDisabled()
  const detail = await page.getByRole("link", { name: "Product details", exact: true }).getAttribute("href")
  expect(detail).toMatch(/^\/products\/[0-9a-f-]+$/)
  await page.getByRole("button", { name: "Remove photo", exact: true }).click()
  await page.getByLabel("Upload", { exact: true }).setInputFiles(fixture)
  await expect(page.getByText("IMG_2682.heic", { exact: true })).toBeVisible()
  await page.getByRole("button", { name: "Continue saving photos", exact: true }).click()
  // CI 的 HEIC 轉換可能超過預設 5 秒, 此處等待包含轉檔完成後的頁面導向.
  await expect(page).toHaveURL(detail!, { timeout: 15_000 })
  await page.reload()
  await page.getByRole("button", { name: "View product photos", exact: true }).click()
  const gallery = page.getByRole("dialog", { name: "Product photos", exact: true })
  const preview = gallery.getByRole("img", { name: /Preview product photo/ })
  await expect(preview).toHaveCount(1)
  await expect(preview).toHaveJSProperty("naturalWidth", 640)
  await expect(preview).toHaveJSProperty("naturalHeight", 640)
  // 公開樣本是 4:3 橫幅, 方形顯示圖的上下透明補邊可守住方向與比例.
  const alpha = await preview.evaluate((image) => {
    const canvas = document.createElement("canvas")
    canvas.width = 640; canvas.height = 640
    const drawing = canvas.getContext("2d")!
    drawing.drawImage(image as HTMLImageElement, 0, 0)
    return [[320, 0], [0, 320], [320, 320], [320, 639]]
      .map(([x, y]) => drawing.getImageData(x, y, 1, 1).data[3])
  })
  expect(alpha).toEqual([0, 255, 255, 0])
  const displayUrl = await preview.getAttribute("src")
  const display = await page.request.get(displayUrl!)
  expect(display.status()).toBe(200)
  expect(display.headers()["content-type"]).toBe("image/webp")
  await testInfo.attach("public-heic-display", { body: await display.body(), contentType: "image/webp" })
  const link = gallery.getByRole("link", { name: "Download original", exact: true })
  const originalUrl = await link.getAttribute("href")
  const response = await page.request.get(originalUrl!)
  expect(response.headers()["content-type"]).toBe("image/heic")
  expect(response.headers()["cache-control"]).toBe("private, no-store")
  const downloading = page.waitForEvent("download")
  await link.click()
  const download = await downloading
  expect(download.suggestedFilename()).toBe("IMG_2682.heic")
  const bytes = await readFile((await download.path())!)
  expect(bytes).toEqual(original)
  expect(createHash("sha256").update(bytes).digest("hex")).toBe(expectedHash)
  await gallery.getByRole("button", { name: "Close", exact: true }).click()
  await page.goto("/products?keyword=HEIC%20Real%20Sample%20Bag")
  await expect(page.getByRole("row").filter({ hasText: "HEIC Real Sample Bag" })).toHaveCount(1)
  await logout(page)
  expect((await page.request.get(originalUrl!)).status()).toBe(401)
})
