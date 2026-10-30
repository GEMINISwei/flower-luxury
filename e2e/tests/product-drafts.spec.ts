import { execFileSync } from "node:child_process"
import { randomUUID } from "node:crypto"
import { expect, test, type Page } from "@playwright/test"
import { admin, login } from "./support"

// Playwright replaces a failed worker, so each process needs its own disposable account.
const staff = { username: `draft-staff-${randomUUID().slice(0, 8)}`, password: "draft-staff-password" }
const image = { name: "supplement.png", mimeType: "image/png",
  buffer: Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAEElEQVR4nGP8zwACTGCSAQANHQEDgslx/wAAAABJRU5ErkJggg==", "base64") }
const seedScript = String.raw`
import asyncio, json, os, sys, uuid
from datetime import timedelta
from io import BytesIO
from PIL import Image
from app.server import app
from modules.brands.public import BrandTable
from modules.line_collection.model import discover_group
from modules.product_drafts import batches, collection, photos, service
from modules.product_drafts.schema import IncomingMessage, DraftUpdate, DraftFields
from shared.db.session import configure_session_factory, create_engine, session_scope
from shared.time import utc_now
actor = {"id": "22222222-2222-4222-8222-222222222222", "username": "fixture", "auth_version": 1, "permissions": [], "is_disabled": False}
async def run():
    engine = create_engine(os.environ["POSTGRES_URL"])
    configure_session_factory(engine)
    async with session_scope():
        arg = json.loads(sys.argv[1])
        if arg.get("conflict"):
            draft = await service.get_draft(arg["conflict"])
            await service.update_draft(draft.id, DraftUpdate(version=draft.version, fields=DraftFields(name="其他人的修改")), actor)
            print("{}")
        else:
            key = "C" + uuid.uuid4().hex
            group, _ = await discover_group(key)
            group.name = arg["name"]
            left, _ = await discover_group(key + "left")
            left.name, left.joined = arg["name"] + " left", False
            left.review_product_id = str(uuid.uuid4())
            source = "line:" + key
            base = utc_now() - timedelta(minutes=1)
            async def message(kind, second, text=None):
                return await collection.ingest_message(IncomingMessage(source_key=source,
                    external_id=uuid.uuid4().hex, kind=kind, text=text,
                    occurred_at=base + timedelta(seconds=second), sender_name="供應商"))
            await message("text", 0, "先到的文字")
            first = await message("image", 1)
            data = BytesIO()
            Image.new("RGB", (8, 4), "red").save(data, "PNG")
            await photos.complete_photo(first.message_id, data.getvalue(), "line.png")
            await message("text", 2, "第一行\n第二行")
            await message("text", 3, "成本三萬元")
            if arg.get("crowded"):
                for index in range(24):
                    await message("text", index + 4, f"補充訊息 {index + 1}\n" + "商品細節\n" * 8)
            second = await message("image", 40)
            await photos.mark_photo_failed(second.message_id)
            if arg.get("batch"):
                group.enabled = True
                await batches.control_collection(source, "start", base + timedelta(seconds=45))
                await batches.record_issue(source, base + timedelta(seconds=46), "ambiguous")
            brand = await BrandTable.create({"name": arg["name"], "is_active": True})
            print(json.dumps({"id": first.draft_id, "second": second.draft_id,
                "source": source, "group": str(group.id), "name": arg["name"],
                "review": left.review_product_id, "brand": str(brand["id"])}))
    await engine.dispose()
asyncio.run(run())
`
function fixture(options: Record<string, string>) {
  const project = process.env.COMPOSE_PROJECT_NAME
  if (!project?.endsWith("-e2e")) throw new Error("Draft fixtures require disposable e2e stack")
  return JSON.parse(execFileSync("docker", ["exec", `${project}-api`, "python", "-c", seedScript,
    JSON.stringify(options)], { encoding: "utf8" })) as {
    id: string; second: string; source: string; group: string; name: string; brand: string; review: string
  }
}
function seed() { return fixture({ name: `Draft ${randomUUID().slice(0, 8)}` }) }
async function open(page: Page, id: string) { await page.goto(`/product-drafts/${id}`) }
async function fillRequired(page: Page, name: string, brand: string) {
  await page.getByLabel("名稱", { exact: true }).fill(name)
  await page.getByLabel("品牌", { exact: true }).selectOption(brand)
  await page.getByLabel("分類", { exact: true }).selectOption("包包")
  await page.getByLabel("成本（新臺幣）", { exact: true }).fill("30000")
}

test.beforeAll(async ({ browser }) => {
  const page = await browser.newPage()
  await login(page, admin)
  await page.goto("/admin/users")
  await page.getByRole("button", { name: "新增員工" }).click()
  const dialog = page.getByRole("dialog")
  await dialog.getByLabel("暱稱").fill("暫存員工")
  await dialog.getByLabel("帳號").fill(staff.username)
  await dialog.getByLabel("密碼").fill(staff.password)
  await dialog.getByRole("button", { name: "建立", exact: true }).click()
  await expect(dialog).toBeHidden()
  await page.close()
})

test("group_settings_respect_permissions", async ({ page }) => {
  const data = seed()
  await login(page, admin)
  await page.goto("/admin/line-groups")
  const row = page.getByRole("row").filter({ hasText: data.name }).filter({ hasNotText: "left" })
  await row.getByRole("button", { name: "啟用收集", exact: true }).click()
  await expect(page.getByRole("dialog")).toContainText("啟用後")
  await page.getByRole("dialog").getByRole("button", { name: "啟用收集", exact: true }).click()
  await expect(row.getByRole("button", { name: "停用收集" })).toBeVisible()
  await row.getByRole("button", { name: "停用收集" }).click()
  await page.getByRole("dialog").getByRole("button", { name: "停用收集" }).click()
  await expect(row.getByRole("button", { name: "啟用收集" })).toBeVisible()
  await login(page, staff)
  await page.goto("/admin/line-groups")
  await expect(page).toHaveURL("/products")
})

test("left_group_cannot_be_enabled and withdrawal_notice_links_to_product", async ({ page }) => {
  const data = seed()
  await login(page, admin)
  await page.goto("/admin/line-groups")
  const row = page.getByRole("row").filter({ hasText: `${data.name} left` })
  await expect(row.getByRole("button", { name: "啟用收集" })).toBeDisabled()
  await expect(row.getByRole("link", { name: "確認正式商品" }))
    .toHaveAttribute("href", `/products/${data.review}`)
})

test("暫存列表只顯示收件時間狀態來源與審核", async ({ page }) => {
  const data = seed()
  await login(page, staff)
  await page.goto(`/product-drafts?source_key=${encodeURIComponent(data.source)}`)
  await expect(page.getByRole("columnheader")).toHaveText(["收件時間", "狀態", "來源", "操作"])
  await expect(page.getByText("未命名商品", { exact: true })).toHaveCount(0)
  await expect(page.getByRole("link", { name: "審核", exact: true })).toHaveCount(2)
  await expect(page.getByRole("link", { name: "審核", exact: true }).first())
    .toHaveAttribute("href", `/product-drafts/${data.second}`)
  await page.getByRole("link", { name: "審核", exact: true }).last().click()
  await expect(page.getByLabel("名稱", { exact: true })).toBeVisible()
})

test("來源篩選由視窗套用並可清除", async ({ page }) => {
  const data = seed()
  await login(page, staff)
  await page.goto("/product-drafts?seq=3")
  await expect(page.getByLabel("來源群組")).toHaveCount(0)
  await page.getByRole("button", { name: "篩選", exact: true }).click()
  const dialog = page.getByRole("dialog")
  await dialog.getByLabel("來源群組").selectOption(data.source)
  await expect(page).not.toHaveURL(/source_key=/)
  await dialog.getByRole("button", { name: "篩選", exact: true }).click()
  await expect(dialog).toBeHidden()
  await expect(page).toHaveURL(new RegExp(`source_key=${encodeURIComponent(data.source)}`))
  await expect(page).not.toHaveURL(/seq=/)
  await expect(page.getByRole("link", { name: "審核", exact: true })).toHaveCount(2)
  await page.reload()
  await page.getByRole("button", { name: "篩選（1）", exact: true }).click()
  await expect(dialog.getByLabel("來源群組")).toHaveValue(data.source)
  await dialog.getByRole("button", { name: "清除", exact: true }).click()
  await dialog.getByRole("button", { name: "篩選", exact: true }).click()
  await expect(page).toHaveURL("/product-drafts")
})

test("店長可結束批次並查看異常與歷史待歸類資料", async ({ page, context }) => {
  const data = fixture({ name: `Batch ${randomUUID().slice(0, 8)}`, batch: "true" })
  await login(page, admin)
  await page.goto("/admin/line-groups")
  const row = page.getByRole("row").filter({ hasText: data.name }).filter({ hasNotText: "left" })
  await expect(row).toContainText("收集中")
  await expect(row).toContainText("無法確認訊息歸屬")
  await row.getByRole("button", { name: "結束批次", exact: true }).click()
  await page.getByRole("dialog").getByRole("button", { name: "結束批次", exact: true }).click()
  await expect(row).toContainText("等待 /start")
  await expect(row.getByRole("button", { name: "結束批次", exact: true })).toHaveCount(0)
  await context.grantPermissions(["clipboard-read", "clipboard-write"])
  await page.goto(`/product-drafts?source_key=${encodeURIComponent(data.source)}`)
  await expect(page.getByRole("link", { name: "待歸類訊息", exact: true })).toHaveCount(0)
  await page.getByRole("link", { name: "歷史待歸類資料", exact: true }).click()
  await page.getByRole("button", { name: "先到的文字", exact: true }).click()
  await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toBe("先到的文字")
  await page.getByRole("button", { name: "刪除歷史訊息", exact: true }).click()
  await page.getByRole("dialog").getByRole("button", { name: "刪除", exact: true }).click()
  await expect(page.getByRole("button", { name: "先到的文字", exact: true })).toHaveCount(0)
  await open(page, data.id)
  await expect(page.getByRole("button", { name: "第一行 第二行", exact: true })).toBeVisible()
})

test("click_message_copies_full_text and draft_fields_remain_user_controlled", async ({ page, context }) => {
  const data = seed()
  await context.grantPermissions(["clipboard-read", "clipboard-write"])
  await login(page, staff)
  await open(page, data.id)
  await page.getByLabel("名稱", { exact: true }).fill("使用者輸入")
  await page.getByRole("button", { name: "第一行 第二行", exact: true }).click()
  await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toBe("第一行\n第二行")
  await expect(page.getByRole("status")).toContainText("已複製")
  await expect(page.getByLabel("名稱", { exact: true })).toHaveValue("使用者輸入")
  await expect(page.getByRole("button", { name: "複製全部文字" })).toHaveCount(0)
  await expect(page.getByRole("button", { name: "移動訊息" })).toHaveCount(0)
  await page.getByRole("button", { name: "成本三萬元", exact: true }).click()
  await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toBe("成本三萬元")
  await page.getByRole("button", { name: "儲存暫存", exact: true }).click()
  await expect(page.getByRole("status")).toContainText("已儲存")
  await page.reload()
  await expect(page.getByLabel("名稱", { exact: true })).toHaveValue("使用者輸入")
})

test("message_copy_failure_shows_feedback", async ({ page }) => {
  const data = seed()
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "clipboard", { value: {
      writeText: () => Promise.reject(new Error("denied")),
    } })
  })
  await login(page, staff)
  await open(page, data.id)
  await page.getByRole("button", { name: "第一行 第二行", exact: true }).click()
  await expect(page.getByRole("main").getByRole("alert")).toContainText("複製失敗")
})

test("stale_draft_preserves_unsaved_input", async ({ page }) => {
  const data = seed()
  await login(page, staff)
  await open(page, data.id)
  await page.getByLabel("名稱", { exact: true }).fill("尚未儲存的名稱")
  fixture({ conflict: data.id })
  await page.getByRole("button", { name: "儲存暫存", exact: true }).click()
  await expect(page.getByRole("main").getByRole("alert")).toContainText("資料已變更")
  await expect(page.getByLabel("名稱", { exact: true })).toHaveValue("尚未儲存的名稱")
  await page.getByRole("button", { name: "重新載入資料", exact: true }).click()
  await expect(page.getByLabel("名稱", { exact: true })).toHaveValue("尚未儲存的名稱")
  await page.getByRole("button", { name: "儲存暫存", exact: true }).click()
  await expect(page.getByRole("status")).toContainText("已儲存")
})

test("draft_photos_can_be_organized_securely", async ({ page, browser }) => {
  const data = seed()
  await login(page, staff)
  await open(page, data.id)
  await page.getByLabel("補上傳照片").setInputFiles(image)
  await expect(page.getByTestId("draft-photo")).toHaveCount(2)
  const last = page.getByTestId("draft-photo").last()
  await last.getByRole("button", { name: "設為主圖" }).click()
  await expect(last).toContainText("主圖")
  const href = await last.getByRole("link", { name: "下載原圖" }).getAttribute("href")
  const response = await page.request.get(href!)
  expect(response.status()).toBe(200)
  expect(response.headers()["cache-control"]).toContain("no-store")
  const anonymous = await browser.newContext()
  expect((await anonymous.request.get(href!)).status()).toBe(401)
  await anonymous.close()
  await expect(page.getByRole("button", { name: "向前移動", exact: true })).toHaveCount(0)
  await expect(page.getByRole("button", { name: "向後移動", exact: true })).toHaveCount(0)
  await last.getByRole("button", { name: "刪除照片" }).click()
  await page.getByRole("dialog").getByRole("button", { name: "刪除", exact: true }).click()
  await expect(page.getByTestId("draft-photo")).toHaveCount(1)
  await expect(page.getByTestId("draft-photo").first()).toContainText("主圖")
})

test("draft_can_be_reviewed_individually", async ({ page }) => {
  const data = seed()
  await login(page, staff)
  await open(page, data.id)
  await page.getByRole("button", { name: "審核建檔", exact: true }).click()
  await expect(page.getByRole("main").getByRole("alert")).toContainText("名稱")
  await fillRequired(page, data.name, data.brand)
  await page.getByRole("button", { name: "審核建檔", exact: true }).click()
  await page.getByRole("dialog").getByRole("button", { name: "審核建檔", exact: true }).click()
  await expect(page).toHaveURL(/\/products\/[0-9a-f-]+$/)
  await expect(page.getByRole("heading", { name: data.name, exact: true })).toBeVisible()
})

test("discard_requires_confirmation", async ({ page }) => {
  const data = seed()
  await login(page, staff)
  await open(page, data.id)
  await page.getByRole("button", { name: "放棄暫存", exact: true }).click()
  await page.getByRole("dialog").getByRole("button", { name: "取消", exact: true }).click()
  await expect(page).toHaveURL(`/product-drafts/${data.id}`)
  await page.getByRole("button", { name: "放棄暫存", exact: true }).click()
  await page.getByRole("dialog").getByRole("button", { name: "放棄暫存", exact: true }).click()
  await expect(page).toHaveURL("/product-drafts")
  await open(page, data.id)
  await expect(page.getByLabel("名稱", { exact: true })).toHaveCount(0)
})

test("mobile and English draft workflow", async ({ page }) => {
  const data = seed()
  await login(page, staff)
  await page.context().addCookies([{ name: "locale", value: "en", url: process.env.E2E_BASE_URL! }])
  await page.setViewportSize({ width: 390, height: 844 })
  await open(page, data.id)
  await expect(page.getByRole("heading", { name: "Original messages", exact: true })).toBeVisible()
  await page.getByRole("button", { name: "Save draft", exact: true }).click()
  await expect(page.getByRole("status")).toContainText("Saved")
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})


test("多張暫存照片可左右切換且不改動商品欄位", async ({ page }) => {
  const data = seed()
  await login(page, staff)
  await open(page, data.id)
  await page.getByLabel("名稱", { exact: true }).fill("待儲存的商品")
  const gallery = page.getByRole("region", { name: "照片瀏覽" })
  await expect(page.getByRole("button", { name: "上一張照片", exact: true })).toBeDisabled()
  await page.getByLabel("補上傳照片").setInputFiles([image, { ...image, name: "third.png" }])
  await expect(page.getByTestId("draft-photo")).toHaveCount(3)
  const firstImage = await gallery.getByTestId("draft-photo").first().boundingBox()
  const galleryBox = await gallery.boundingBox()
  expect(firstImage!.width).toBeLessThanOrEqual(galleryBox!.width + 1)
  const firstUrl = await gallery.getByRole("link", { name: "預覽照片" }).first().getAttribute("href")
  await page.getByRole("button", { name: "下一張照片", exact: true }).click()
  await expect(page.getByText("第 2 張，共 3 張", { exact: true })).toBeVisible()
  const second = gallery.getByTestId("draft-photo").nth(1)
  const secondBox = await second.boundingBox()
  expect(Math.abs(secondBox!.x - galleryBox!.x)).toBeLessThan(2)
  expect(await second.getByRole("link", { name: "預覽照片" }).getAttribute("href"))
    .not.toBe(firstUrl)
  await gallery.focus()
  await page.keyboard.press("ArrowRight")
  await expect(page.getByText("第 3 張，共 3 張", { exact: true })).toBeVisible()
  await expect(page.getByRole("button", { name: "下一張照片", exact: true })).toBeDisabled()
  await page.getByRole("button", { name: "上一張照片", exact: true }).click()
  await expect(page.getByText("第 2 張，共 3 張", { exact: true })).toBeVisible()
  await expect(page.getByLabel("名稱", { exact: true })).toHaveValue("待儲存的商品")
})

test("大量原始訊息在固定高度區域捲動且可逐則完整複製", async ({ page, context }) => {
  const data = fixture({ name: `Long ${randomUUID().slice(0, 8)}`, crowded: "yes" })
  await context.grantPermissions(["clipboard-read", "clipboard-write"])
  await login(page, staff)
  await open(page, data.id)
  const messages = page.getByRole("region", { name: "訊息內容" })
  expect(await messages.evaluate((element) => element.scrollHeight > element.clientHeight)).toBe(true)
  expect(await messages.evaluate((element) => element.clientHeight)).toBeLessThanOrEqual(480)
  await messages.focus()
  await page.keyboard.press("End")
  await expect.poll(() => messages.evaluate((element) => element.scrollTop)).toBeGreaterThan(0)
  await expect(page.getByRole("button", { name: "複製全部文字" })).toHaveCount(0)
  await messages.getByRole("button", { name: /補充訊息 24/ }).click()
  await expect.poll(() => page.evaluate(() => navigator.clipboard.readText()))
    .toBe("補充訊息 24\n" + "商品細節\n".repeat(8))
})

test("手機版暫存工作區不橫向溢出且可切換照片", async ({ page }) => {
  const data = seed()
  await login(page, staff)
  await page.setViewportSize({ width: 390, height: 844 })
  await page.context().addCookies([{ name: "locale", value: "en", url: process.env.E2E_BASE_URL! }])
  await open(page, data.id)
  await page.getByLabel("Upload additional photos").setInputFiles(image)
  await page.getByRole("button", { name: "Next photo", exact: true }).click()
  await expect(page.getByText("Photo 2 of 2", { exact: true })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await expect(page.getByRole("button", { name: "Copy all text", exact: true })).toHaveCount(0)
  await expect(page.getByRole("button", { name: "Move message", exact: true })).toHaveCount(0)
  await expect(page.getByRole("button", { name: "Move earlier", exact: true })).toHaveCount(0)
  await expect(page.getByRole("button", { name: "Move later", exact: true })).toHaveCount(0)
  const messages = page.getByRole("region", { name: "Message content" })
  await expect(messages).toHaveAttribute("tabindex", "0")
  expect((await messages.boundingBox())!.width).toBeLessThan(390)
})
