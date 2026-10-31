import { readFile } from "node:fs/promises"
import { expect, test, type Page } from "@playwright/test"
import { admin, login, logout } from "./support"

const staff = { username: "lifecycle-staff", password: "lifecycle-staff-password" }
const productName = "Lifecycle Bag"
const brandName = "Lifecycle Brand"
const vendorName = "Lifecycle Vendor"
const returnReason = "員工驗收退回後重新議價"
const filenames = ["lifecycle-front.png", "lifecycle-back.png"]
const png = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAABAAAAAICAIAAAB/FOjAAAAAFklEQVR4nGP8z0AaYCJRPcOoBgYiAACTUAEPHJZO1QAAAABJRU5ErkJggg==", "base64")

async function prepareStaff(page: Page) {
  await login(page, admin)
  await page.goto("/admin/users")
  await page.getByRole("button", { name: "新增員工", exact: true }).click()
  const dialog = page.getByRole("dialog")
  await dialog.getByLabel("暱稱").fill("完整流程員工")
  await dialog.getByLabel("帳號").fill(staff.username)
  await dialog.getByLabel(/^密碼\*?$/).fill(staff.password)
  await dialog.getByRole("button", { name: "建立", exact: true }).click()
  await expect(dialog).toBeHidden()
  await expect(page.getByRole("row").filter({ hasText: "完整流程員工" })
    .getByRole("cell", { name: "員工", exact: true })).toBeVisible()
  await logout(page)
  await login(page, staff)
}

async function createCatalog(page: Page) {
  await page.goto("/brands")
  await page.getByRole("button", { name: "新增品牌", exact: true }).click()
  let dialog = page.getByRole("dialog")
  await dialog.getByLabel(/^名稱\*?$/).fill(brandName)
  await dialog.getByRole("button", { name: "儲存", exact: true }).click()
  await expect(dialog).toBeHidden()
  await page.goto("/vendors")
  await page.getByRole("button", { name: "新增廠商", exact: true }).click()
  dialog = page.getByRole("dialog")
  await dialog.getByLabel(/^名稱\*?$/).fill(vendorName)
  await dialog.getByRole("button", { name: "儲存", exact: true }).click()
  await expect(dialog).toBeHidden()
}

async function createProduct(page: Page) {
  await page.goto("/products/new")
  await page.getByLabel(/^名稱\*?$/).fill(productName)
  await page.getByRole("combobox", { name: /^品牌\*?$/ }).selectOption({ label: brandName })
  await page.getByRole("combobox", { name: /^分類\*?$/ }).selectOption("包包")
  await page.getByLabel(/^成本（新臺幣）\*?$/).fill("3100")
  await page.getByLabel("上傳", { exact: true }).setInputFiles(
    filenames.map((name) => ({ name, mimeType: "image/png", buffer: png })),
  )
  for (const name of filenames) {
    await expect(page.getByRole("img", { name, exact: true })).toHaveJSProperty("naturalWidth", 16)
  }
  await page.getByRole("button", { name: "儲存", exact: true }).click()
  await expect(page).toHaveURL(/\/products\/[0-9a-f-]+$/)
  await expect(page.getByRole("heading", { name: productName, exact: true })).toBeVisible()
}

async function checkPhotos(page: Page, sources: string[], sold: boolean) {
  await expect(page.getByRole("img", { name: productName, exact: true }))
    .toHaveAttribute("src", sources[0].replace("?size=640", "?size=320"))
  await page.getByRole("button", { name: "查看商品照片", exact: true }).click()
  const gallery = page.getByRole("dialog", { name: "商品照片", exact: true })
  const images = gallery.getByRole("img", { name: /預覽商品照片/ })
  await expect(images).toHaveCount(2)
  await expect(gallery.getByText("主圖", { exact: true })).toBeVisible()
  for (const [index, source] of sources.entries()) {
    await expect(images.nth(index)).toHaveAttribute("src", source)
    await expect(images.nth(index)).toHaveJSProperty("naturalWidth", 640)
    const downloaded = page.waitForEvent("download")
    await gallery.getByRole("link", { name: "下載原圖", exact: true }).nth(index).click()
    const download = await downloaded
    expect(download.suggestedFilename()).toBe(filenames[index])
    const path = await download.path()
    expect(path).toBeTruthy()
    expect(await readFile(path!)).toEqual(png)
  }
  await expect(gallery.getByRole("button", { name: "上傳", exact: true })).toHaveCount(sold ? 0 : 1)
  await expect(gallery.getByRole("button", { name: "直接拍照", exact: true })).toHaveCount(sold ? 0 : 1)
  await expect(gallery.getByRole("button", { name: "設為主圖", exact: true })).toHaveCount(sold ? 0 : 1)
  await expect(gallery.getByRole("button", { name: "刪除", exact: true })).toHaveCount(sold ? 0 : 1)
  if (!sold) {
    for (const name of ["上傳", "直接拍照", "設為主圖", "刪除"]) {
      await expect(gallery.getByRole("button", { name, exact: true })).toBeEnabled()
    }
  }
  await gallery.getByRole("button", { name: "關閉", exact: true }).click()
  await expect(gallery).toBeHidden()
}

async function confirmSale(page: Page) {
  await page.getByRole("button", { name: "確認成交", exact: true }).click()
  const dialog = page.getByRole("dialog", { name: "確認成交", exact: true })
  await dialog.getByRole("button", { name: "確認成交", exact: true }).click()
  await expect(dialog).toBeHidden()
  await expect(page.getByRole("button", { name: "退回狀態", exact: true })).toBeVisible()
  await expect(page.getByRole("button", { name: "編輯商品", exact: true })).toHaveCount(0)
  await expect(page.getByRole("button", { name: "刪除商品", exact: true })).toHaveCount(0)
  await expect(page.getByRole("button", { name: "新增詢價", exact: true })).toHaveCount(0)
  await expect(page.getByRole("button", { name: "編輯", exact: true })).toHaveCount(0)
  await expect(page.getByRole("button", { name: "刪除詢價", exact: true })).toHaveCount(0)
  await expect(page.getByRole("button", { name: "確認成交", exact: true })).toHaveCount(0)
}

test("員工建立商品上傳照片後可詢價成交退回再成交並保留照片與歷史快照", async ({ page }) => {
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
    await page.getByRole("button", { name: "查看商品照片", exact: true }).click()
    const gallery = page.getByRole("dialog", { name: "商品照片", exact: true })
    const images = gallery.getByRole("img", { name: /預覽商品照片/ })
    await expect(images).toHaveCount(2)
    for (const image of await images.all()) {
      const source = await image.getAttribute("src")
      expect(source).toMatch(/^\/api\/products\/photos\/[0-9a-f-]+\/file\?size=640$/)
      sources.push(source!)
    }
    await gallery.getByRole("button", { name: "關閉", exact: true }).click()
    await checkPhotos(page, sources, false)
  })

  await test.step("員工新增詢價並成交後商品與照片唯讀且可下載原圖", async () => {
    await page.getByRole("button", { name: "新增詢價", exact: true }).click()
    const dialog = page.getByRole("dialog", { name: "新增詢價", exact: true })
    await dialog.getByRole("combobox", { name: /^廠商\*?$/ })
      .selectOption({ label: `${vendorName}` })
    await dialog.getByLabel(/^報價\*?$/).fill("5000")
    await dialog.getByRole("button", { name: "儲存", exact: true }).click()
    await expect(dialog).toBeHidden()
    await expect(page.getByText("TWD 5,000", { exact: true })).toBeVisible()
    await confirmSale(page)
    await expect(page.getByText("目前成交", { exact: true })).toHaveCount(1)
    await expect(page.getByRole("heading", { name: "成交歷史", exact: true })).toHaveCount(0)
    await expect(page.getByRole("heading", { name: "流向記錄", exact: true })).toHaveCount(0)
    await page.getByRole("link", { name: "查看商品歷程", exact: true }).click()
    await expect(page.getByRole("definition")).toContainText(["5,000", "3,100", "1,900", staff.username])
    await page.getByRole("link", { name: "返回商品詳情", exact: true }).click()
    await expect(page).toHaveURL(detail)
    await checkPhotos(page, sources, true)
  })

  await test.step("員工填寫原因退回後恢復商品詢價與照片操作並保留舊成交", async () => {
    await page.getByRole("button", { name: "退回狀態", exact: true }).click()
    const dialog = page.getByRole("dialog", { name: "退回狀態", exact: true })
    await dialog.getByLabel(/^退回原因（必填）\*?$/).fill(returnReason)
    await dialog.getByRole("button", { name: "退回狀態", exact: true }).click()
    await expect(dialog).toBeHidden()
    await expect(page.getByRole("button", { name: "編輯商品", exact: true })).toBeVisible()
    await expect(page.getByRole("button", { name: "刪除商品", exact: true })).toBeVisible()
    await expect(page.getByRole("button", { name: "新增詢價", exact: true })).toBeVisible()
    await expect(page.getByRole("button", { name: "編輯", exact: true })).toBeVisible()
    await expect(page.getByRole("button", { name: "刪除詢價", exact: true })).toHaveCount(0)
    await expect(page.getByText("目前成交", { exact: true })).toHaveCount(0)
    await expect(page.getByText("已退回", { exact: true })).toHaveCount(0)
    await page.getByRole("link", { name: "查看商品歷程", exact: true }).click()
    await expect(page.getByText("已退回", { exact: true })).toHaveCount(1)
    await expect(page.getByText(returnReason, { exact: true })).toHaveCount(2)
    await page.getByRole("link", { name: "返回商品詳情", exact: true }).click()
    await expect(page).toHaveURL(detail)
    await checkPhotos(page, sources, false)
  })

  await test.step("員工修改成本與原詢價後再成交且舊快照不被覆寫", async () => {
    await page.getByRole("button", { name: "編輯商品", exact: true }).click()
    let dialog = page.getByRole("dialog", { name: "編輯商品", exact: true })
    await dialog.getByLabel(/^成本（新臺幣）\*?$/).fill("3200")
    await dialog.getByRole("button", { name: "儲存", exact: true }).click()
    await expect(dialog).toBeHidden()
    await page.getByRole("button", { name: "編輯", exact: true }).click()
    dialog = page.getByRole("dialog", { name: "詢價", exact: true })
    await dialog.getByLabel(/^報價\*?$/).fill("6500")
    await dialog.getByRole("button", { name: "儲存", exact: true }).click()
    await expect(dialog).toBeHidden()
    await expect(page.getByText("TWD 6,500", { exact: true })).toBeVisible()
    await confirmSale(page)
    await expect(page.getByText("目前成交", { exact: true })).toHaveCount(1)
    await expect(page.getByText("已退回", { exact: true })).toHaveCount(0)
    await page.getByRole("link", { name: "查看商品歷程", exact: true }).click()
    await expect(page.getByText("已退回", { exact: true })).toHaveCount(1)
    await expect(page.getByRole("definition")).toContainText([
      "6,500", "3,200", "3,300", staff.username,
      "5,000", "3,100", "1,900", staff.username, returnReason,
    ])
    await page.getByRole("link", { name: "返回商品詳情", exact: true }).click()
    await expect(page).toHaveURL(detail)
  })

  await test.step("重新載入後同一商品與照片兩次成交及員工流向記錄仍保留", async () => {
    await page.reload()
    await expect(page).toHaveURL(detail)
    await expect(page.getByRole("heading", { name: productName, exact: true })).toBeVisible()
    await expect(page.getByText(sku, { exact: true }).first()).toBeVisible()
    await expect(page.getByText("目前成交", { exact: true })).toHaveCount(1)
    await expect(page.getByText("已退回", { exact: true })).toHaveCount(0)
    await page.getByRole("link", { name: "查看商品歷程", exact: true }).click()
    await expect(page.getByText("已退回", { exact: true })).toHaveCount(1)
    await expect(page.getByRole("definition")).toContainText([
      "6,500", "3,200", "3,300", staff.username,
      "5,000", "3,100", "1,900", staff.username, returnReason,
    ])
    await expect(page.getByRole("listitem").filter({ hasText: staff.username })).toContainText([
      "未收購", "已出售", returnReason, "已出售",
    ])
    await expect(page.getByRole("listitem").filter({ hasText: staff.username })).toHaveCount(4)
    await page.getByRole("link", { name: "返回商品詳情", exact: true }).click()
    await expect(page).toHaveURL(detail)
    await checkPhotos(page, sources, true)
    await page.getByRole("link", { name: "返回商品列表", exact: true }).click()
    await page.goto(`/products?keyword=${encodeURIComponent(sku)}`)
    const row = page.getByRole("row").filter({ hasText: sku })
    await expect(row).toHaveCount(1)
    await expect(row.getByRole("cell", { name: "已出售", exact: true })).toBeVisible()
    await row.getByRole("link").filter({ hasText: productName }).click()
    await expect(page).toHaveURL(detail)
  })
})
