import { execFileSync } from "node:child_process"
import { randomUUID } from "node:crypto"
import { expect, test, type BrowserContext, type Page } from "@playwright/test"
import { admin, login } from "./support"
import { expectHeaderFits } from "./header-layout"

// Playwright replaces a failed worker, so each process needs its own disposable account.
const staff = { username: `draft-staff-${randomUUID().slice(0, 8)}`, password: "draft-staff-password" }
let workspaceState: Awaited<ReturnType<BrowserContext["storageState"]>> | undefined
let managerState: Awaited<ReturnType<BrowserContext["storageState"]>> | undefined
const workspaceTest = test.extend({
  storageState: async ({ browser, baseURL, locale }, use) => {
    // 版面驗收共用登入憑證, 避免整套 smoke 測試耗盡同一 IP 的登入額度.
    if (!workspaceState) {
      const context = await browser.newContext({ baseURL, locale })
      try {
        const page = await context.newPage()
        await login(page, staff)
        workspaceState = await context.storageState()
      } finally { await context.close() }
    }
    await use(workspaceState)
  },
})
async function draftMenu(page: Page, label: string) {
  await page.locator("header").getByRole("button", { name: "操作選單", exact: true }).click()
  await page.getByRole("menuitem", { name: label, exact: true }).click()
}

const seedScript = String.raw`
import asyncio, json, os, sys, uuid
from datetime import timedelta
from io import BytesIO
from PIL import Image
from app.server import app
from modules.brands.public import BrandTable
from modules.line_collection.model import discover_group
from modules.product_drafts import batches, collection, model as draft_model, photos, service
from modules.product_drafts.schema import IncomingMessage, DraftUpdate, DraftFields
from shared.db.session import configure_session_factory, create_engine, session_scope
from shared.time import utc_now
actor = {"id": "22222222-2222-4222-8222-222222222222", "username": "fixture", "auth_version": 1, "permissions": [], "is_disabled": False}
async def run():
    engine = create_engine(os.environ["POSTGRES_URL"])
    configure_session_factory(engine)
    async with session_scope():
        arg = json.loads(sys.argv[1])
        if arg.get("ai"):
            os.environ["GEMINI_API_KEY"] = "fixture-only"
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
            if arg.get("buffer"):
                from modules.product_drafts import buffer
                group.enabled = True
                await buffer.queue_control(source, "start", base)
                await buffer.queue_message(IncomingMessage(source_key=source,
                    external_id=uuid.uuid4().hex, kind="image",
                    occurred_at=base + timedelta(seconds=1)))
                print(json.dumps({"id": "", "second": "", "source": source,
                    "group": str(group.id), "name": arg["name"], "brand": "", "review": ""}))
                return
            async def message(kind, second, text=None):
                return await collection.ingest_message(IncomingMessage(source_key=source,
                    external_id=uuid.uuid4().hex, kind=kind, text=text,
                    occurred_at=base + timedelta(seconds=second), sender_id="U_hidden_sender_code"))
            await message("text", 0, "先到的文字")
            first = await message("image", 1)
            data = BytesIO()
            Image.new("RGB", (8, 4), "red").save(data, "PNG")
            await photos.complete_photo(first.message_id, data.getvalue(), "line.png")
            for index in range(1, int(arg.get("photos", "1"))):
                extra = await message("image", 1 + index / 10)
                await photos.complete_photo(extra.message_id, data.getvalue(), f"line-{index}.png")
            await message("text", 2, "第一行\n第二行")
            await message("text", 3, "成本三萬元")
            if arg.get("crowded"):
                for index in range(24):
                    await message("text", index + 4, f"補充訊息 {index + 1}\n" + "商品細節\n" * 8)
            second = await message("image", 40)
            await photos.mark_photo_failed(second.message_id)
            last = await draft_model.get_draft_row(second.draft_id)
            last.collecting = False
            if arg.get("collecting"):
                first_row = await draft_model.get_draft_row(first.draft_id)
                first_row.collecting = True
            if arg.get("processing"):
                first_row = await draft_model.get_draft_row(first.draft_id)
                first_row.processing = True
            if arg.get("single"):
                from modules.product_drafts import review
                from modules.product_drafts.schema import VersionRequest
                last_info = await service.get_draft(second.draft_id)
                await review.discard_draft(last_info.id, VersionRequest(version=last_info.version), actor)
            if arg.get("issue"):
                from unittest.mock import patch
                from modules.product_drafts import buffer
                from shared.jobs.contracts import Job
                await buffer.queue_control(source, "start", base + timedelta(seconds=41))
                for kind in ("image", "text"):
                    await buffer.queue_message(IncomingMessage(source_key=source,
                        external_id=uuid.uuid4().hex, kind=kind,
                        text="同時到達待確認文字" if kind == "text" else None,
                        occurred_at=base + timedelta(seconds=42)))
                with patch.object(buffer, "utc_now", return_value=utc_now() + timedelta(minutes=4)):
                    await buffer.process_buffer(Job(id=uuid.uuid4(), task_name="product_drafts.buffer",
                        payload={"source_key": source}, attempts=1))
            if arg.get("batch"):
                group.enabled = True
                await batches.control_collection(source, "start", base + timedelta(seconds=45))
                await batches.record_issue(source, base + timedelta(seconds=46), "ambiguous")
            brand = await BrandTable.create({"name": arg["name"], "is_active": True})
            if arg.get("ai"):
                from unittest.mock import AsyncMock, patch
                from modules.product_drafts import prefill
                from modules.product_drafts.prefill_schema import PrefillContent, PrefillResult
                from modules.vendors.public import VendorTable
                from shared.jobs.contracts import Job
                vendor = await VendorTable.create({"name": arg["name"] + " buyer", "is_active": True, "has_quotes": False})
                draft = await service.get_draft(first.draft_id)
                result = PrefillResult(name="AI 商品", vendor_info=[{"vendor_id": str(vendor["id"]), "original_amount": "100", "exchange_rate": "4.5"}])
                with patch.object(prefill, "release_connection", AsyncMock()), patch.object(prefill, "generate_prefill", AsyncMock(return_value=PrefillContent(content=result.model_dump_json()))):
                    await prefill.run_prefill(Job(id=uuid.uuid4(), task_name="product_drafts.prefill", attempts=1, payload={"draft_id": draft.id, "revision": draft.prefill_revision}))
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
  managerState = await page.context().storageState()
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


workspaceTest("緩衝收件時顯示處理中且尚未開放新商品審核", async ({ page }) => {
  const data = fixture({ name: `Buffer ${randomUUID().slice(0, 8)}`, buffer: "true" })
  await page.context().addCookies(managerState!.cookies)
  await page.goto("/admin/line-groups")
  const row = page.getByRole("row").filter({ hasText: data.name }).filter({ hasNotText: "left" })
  await expect(row).toContainText("處理中")
  await page.goto(`/product-drafts?source_key=${encodeURIComponent(data.source)}`)
  await expect(page.getByRole("link", { name: "審核", exact: true })).toHaveCount(0)
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
    .toHaveAttribute("href", `/product-drafts/${data.id}?source_key=${encodeURIComponent(data.source)}`)
  await page.getByRole("link", { name: "審核", exact: true }).first().click()
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

test("店長可結束批次並查看異常且不再顯示歷史待歸類資料", async ({ page }) => {
  const data = fixture({ name: `Batch ${randomUUID().slice(0, 8)}`, batch: "true" })
  await login(page, admin)
  await page.goto("/admin/line-groups")
  const row = page.getByRole("row").filter({ hasText: data.name }).filter({ hasNotText: "left" })
  await expect(row).toContainText("收集中")
  await expect(row).toContainText("無法確認訊息歸屬")
  await row.getByRole("button", { name: "結束批次", exact: true }).click()
  await page.getByRole("dialog").getByRole("button", { name: "結束批次", exact: true }).click()
  await expect(row).toContainText("待整理")
  await expect(row.getByRole("button", { name: "結束批次", exact: true })).toHaveCount(0)
  await expect(row.getByRole("cell", { name: "已加入", exact: true })).toBeVisible()
  await expect(row).not.toContainText("批次開始")
  await expect(row).not.toContainText("批次結束")
  const leftRow = page.getByRole("row").filter({ hasText: `${data.name} left` })
  await expect(leftRow.getByRole("cell", { name: "未加入", exact: true })).toBeVisible()
  await expect(leftRow).toContainText("已停用")
  for (const suffix of ["", "&view=messages"]) {
    await page.goto(`/product-drafts?source_key=${encodeURIComponent(data.source)}${suffix}`)
    await expect(page.getByRole("heading", { name: "商品暫存", exact: true })).toBeVisible()
    await expect(page.getByRole("link", { name: "歷史待歸類資料", exact: true })).toHaveCount(0)
    await expect(page.getByRole("button", { name: "先到的文字", exact: true })).toHaveCount(0)
    await expect(page.getByRole("button", { name: "刪除歷史訊息", exact: true })).toHaveCount(0)
  }
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
  await draftMenu(page, "儲存暫存")
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
  await draftMenu(page, "儲存暫存")
  await expect(page.getByRole("main").getByRole("alert")).toContainText("資料已變更")
  await expect(page.getByLabel("名稱", { exact: true })).toHaveValue("尚未儲存的名稱")
  await page.getByRole("button", { name: "重新載入資料", exact: true }).click()
  await expect(page.getByLabel("名稱", { exact: true })).toHaveValue("尚未儲存的名稱")
  await draftMenu(page, "儲存暫存")
  await expect(page.getByRole("status")).toContainText("已儲存")
})

test("draft_photos_can_be_organized_securely", async ({ page, browser }) => {
  const data = fixture({ name: `Photos ${randomUUID().slice(0, 8)}`, photos: "2" })
  await login(page, staff)
  await open(page, data.id)
  await expect(page.getByTestId("draft-photo")).toHaveCount(2)
  await page.getByRole("button", { name: "下一張照片", exact: true }).click()
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
  await expect(page.getByRole("link", { name: "查看已建檔商品", exact: true })).toBeVisible()
  await page.getByRole("link", { name: "查看已建檔商品", exact: true }).click()
  await expect(page).toHaveURL(/\/products\/[0-9a-f-]+$/)
  await expect(page.getByRole("heading", { name: data.name, exact: true })).toBeVisible()
})

test("discard_requires_confirmation", async ({ page }) => {
  const data = seed()
  await login(page, staff)
  await open(page, data.id)
  await draftMenu(page, "放棄暫存")
  await page.getByRole("dialog").getByRole("button", { name: "取消", exact: true }).click()
  await expect(page).toHaveURL(`/product-drafts/${data.id}`)
  await draftMenu(page, "放棄暫存")
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
  await page.locator("header").getByRole("button", { name: "Actions", exact: true }).click()
  await page.getByRole("menuitem", { name: "Save draft", exact: true }).click()
  await expect(page.getByRole("status")).toContainText("Saved")
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})


workspaceTest("多張暫存照片可左右切換且不改動商品欄位", async ({ page }) => {
  const data = fixture({ name: `Gallery ${randomUUID().slice(0, 8)}`, photos: "3" })
  await open(page, data.id)
  await page.getByLabel("名稱", { exact: true }).fill("待儲存的商品")
  const gallery = page.getByRole("region", { name: "照片瀏覽" })
  await expect(page.getByRole("button", { name: "上一張照片", exact: true })).toBeDisabled()
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

workspaceTest("大量原始訊息在固定高度區域捲動且可逐則完整複製", async ({ page, context }) => {
  const data = fixture({ name: `Long ${randomUUID().slice(0, 8)}`, crowded: "yes" })
  await context.grantPermissions(["clipboard-read", "clipboard-write"])
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

workspaceTest("手機版暫存工作區不橫向溢出且可切換照片", async ({ page }) => {
  const data = fixture({ name: `Mobile ${randomUUID().slice(0, 8)}`, photos: "2" })
  await page.setViewportSize({ width: 390, height: 844 })
  await page.context().addCookies([{ name: "locale", value: "en", url: process.env.E2E_BASE_URL! }])
  await open(page, data.id)
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

workspaceTest("暫存原始訊息只顯示時間與文字且不提供補上傳", async ({ page }) => {
  const data = seed()
  await open(page, data.id)
  const messages = page.getByRole("region", { name: "訊息內容", exact: true })
  await expect(messages.getByRole("article")).toHaveCount(2)
  await expect(messages.getByRole("button")).toHaveText(["第一行\n第二行", "成本三萬元"])
  await expect(messages.getByRole("img")).toHaveCount(0)
  await expect(messages).not.toContainText("圖片訊息")
  await expect(messages).not.toContainText("U_hidden_sender_code")
  await expect(messages).not.toContainText("未提供傳送者")
  for (const article of await messages.getByRole("article").all()) {
    expect(await article.evaluate((element) => element.querySelector("time")?.dateTime))
      .toMatch(/^\d{4}-\d{2}-\d{2}T/)
  }
  await expect(page.getByLabel("補上傳照片")).toHaveCount(0)
  await expect(page.getByTestId("draft-photo")).toHaveCount(1)
  await open(page, data.second)
  await expect(page.getByRole("region", { name: "訊息內容", exact: true }).getByRole("article"))
    .toHaveCount(0)
  await expect(page.getByRole("region", { name: "照片整理", exact: true }))
    .toContainText("下載失敗")
  await expect(page.getByRole("main")).not.toContainText("補上傳")
})

workspaceTest("暫存返回位於內容頂端且操作集中於頁首", async ({ page }) => {
  const data = seed()
  await open(page, data.id)
  const back = page.getByRole("link", { name: "返回暫存列表", exact: true })
  await expect(back).toHaveAttribute("href", "/product-drafts")
  expect(await back.evaluate((element) => Boolean(element.closest("header")))).toBe(false)
  const backBox = (await back.boundingBox())!
  for (const label of ["重新載入資料", "審核建檔", "操作選單"]) {
    const action = page.getByRole("button", { name: label, exact: true })
    expect(await action.evaluate((element) => Boolean(element.closest("header")))).toBe(true)
    const box = (await action.boundingBox())!
    expect(box.y + box.height).toBeLessThanOrEqual(backBox.y)
  }
  const photos = (await page.getByRole("region", { name: "照片整理", exact: true }).boundingBox())!
  expect(backBox.y + backBox.height).toBeLessThan(photos.y)
  await back.click()
  await expect(page).toHaveURL("/product-drafts")
})

workspaceTest("商品資訊依指定六列排列且最多兩欄", async ({ page }) => {
  const data = seed()
  await open(page, data.id)
  await expect(page.getByRole("heading", { name: "商品資訊", exact: true })).toBeVisible()
  const rows = [["名稱"], ["成本（新臺幣）"], ["品牌", "分類"],
    ["型號", "序號"], ["年份", "顏色"], ["備註"]]
  for (const width of [1440, 1024, 390]) {
    await page.setViewportSize({ width, height: 1000 })
    let bottom = 0
    for (const row of rows) {
      const first = (await page.getByLabel(row[0], { exact: true }).boundingBox())!
      expect(first.y).toBeGreaterThan(bottom)
      if (row.length === 2) {
        const second = (await page.getByLabel(row[1], { exact: true }).boundingBox())!
        expect(Math.abs(first.y - second.y)).toBeLessThan(2)
        expect(first.x + first.width).toBeLessThan(second.x)
      } else {
        const brand = (await page.getByLabel("品牌", { exact: true }).boundingBox())!
        const category = (await page.getByLabel("分類", { exact: true }).boundingBox())!
        expect(Math.abs(first.width - (category.x + category.width - brand.x))).toBeLessThan(2)
      }
      bottom = first.y + first.height
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  }
})

workspaceTest("店長可設定全域審核預填且員工無法進入", async ({ page, browser }) => {
  if (!managerState) throw new Error("Manager session is not initialized")
  const context = await browser.newContext({ storageState: managerState,
    baseURL: process.env.E2E_BASE_URL, locale: "zh-TW" })
  try {
    const manager = await context.newPage()
    await manager.goto("/admin/draft-prefill")
    await expect(manager.getByRole("heading", { name: "AI 助手", exact: true })).toBeVisible()
    await expect(manager.getByRole("link", { name: "AI 助手", exact: true })).toBeVisible()
    await expect(manager.getByLabel("基礎 Prompt", { exact: true })).toHaveCount(0)
    await expect(manager.getByText("Gemini 3.5 Flash-Lite 已設定", { exact: true })).toHaveCount(0)
    await expect(manager.getByText("可補充術語、分類與金額寫法", { exact: false })).toHaveCount(0)
    const card = manager.getByRole("region", { name: "審核預填", exact: true })
    await expect(card.getByRole("separator")).toBeVisible()
    await expect(card.getByLabel("測試文字", { exact: true })).toBeVisible()
    await expect(card.getByRole("textbox", { name: /^補充條件 \d+$/ })).toHaveCount(0)
    await card.getByRole("button", { name: "新增條件", exact: true }).click()
    await card.getByLabel("補充條件 1", { exact: true }).fill("底價表示商品成本。")
    await card.getByRole("button", { name: "新增條件", exact: true }).click()
    await card.getByLabel("補充條件 2", { exact: true }).fill("需要刪除的條件。")
    await card.getByRole("button", { name: "新增條件", exact: true }).click()
    await card.getByLabel("補充條件 3", { exact: true }).fill("小香表示 Chanel。")
    await card.getByRole("button", { name: "刪除條件 2", exact: true }).click()
    await expect(card.getByLabel("補充條件 2", { exact: true })).toHaveValue("小香表示 Chanel。")
    await expect(card.getByLabel("補充條件 3", { exact: true })).toHaveCount(0)
    const save = manager.getByRole("button", { name: "儲存設定", exact: true })
    await save.click()
    await expect(manager.getByRole("status")).toContainText("已儲存")
    await manager.reload()
    await expect(card.getByLabel("補充條件 1", { exact: true })).toHaveValue("底價表示商品成本。")
    await expect(card.getByLabel("補充條件 2", { exact: true })).toHaveValue("小香表示 Chanel。")
    for (const width of [1280, 390]) {
      await manager.setViewportSize({ width, height: 844 })
      await expect(save).toBeVisible()
      const titleBox = (await manager.getByRole("heading", { name: "AI 助手", exact: true })
        .boundingBox())!
      const saveBox = (await save.boundingBox())!
      expect(saveBox.x).toBeGreaterThan(titleBox.x + titleBox.width)
      expect(Math.abs(saveBox.y + saveBox.height / 2 - titleBox.y - titleBox.height / 2))
        .toBeLessThan(2)
      expect(await manager.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    }
    await card.getByRole("button", { name: "刪除條件 1", exact: true }).click()
    await expect(card.getByLabel("補充條件 1", { exact: true })).toHaveValue("小香表示 Chanel。")
    await card.getByRole("button", { name: "刪除條件 1", exact: true }).click()
    await save.click()
    await expect(manager.getByRole("status")).toContainText("已儲存")
    await manager.reload()
    await expect(card.getByRole("textbox", { name: /^補充條件 \d+$/ })).toHaveCount(0)
    await expect(manager.getByText("尚未設定 Gemini API 金鑰", { exact: false })).toBeVisible()
  } finally { await context.close() }
  await page.goto("/admin/draft-prefill")
  await expect(page).toHaveURL("/products")
})

workspaceTest("暫存詢價可手動管理並於審核轉入正式商品", async ({ page }) => {
  const data = seed()
  await page.goto("/vendors")
  await page.getByRole("button", { name: "新增廠商", exact: true }).click()
  let dialog = page.getByRole("dialog")
  await dialog.getByLabel(/^名稱\*?$/).fill(data.name)
  await dialog.getByRole("button", { name: "儲存", exact: true }).click()
  await expect(dialog).toBeHidden()
  await open(page, data.id)
  await fillRequired(page, data.name, data.brand)
  const info = (await page.getByLabel("備註", { exact: true }).boundingBox())!
  const section = page.getByRole("region", { name: "廠商詢價", exact: true })
  expect((await section.boundingBox())!.y).toBeGreaterThan(info.y + info.height)
  await section.getByRole("button", { name: "新增詢價", exact: true }).click()
  dialog = page.getByRole("dialog", { name: "新增詢價", exact: true })
  await dialog.getByLabel(/^廠商\*?$/).selectOption({ label: `${data.name}` })
  await dialog.getByLabel(/^報價\*?$/).fill("1200")
  await expect(dialog.getByLabel(/^匯率\*?$/)).toHaveValue("1")
  await dialog.getByRole("button", { name: "儲存", exact: true }).click()
  await expect(dialog).toBeHidden()
  await expect(page.getByLabel("名稱", { exact: true })).toHaveValue(data.name)
  await expect(section).toContainText("1,200")
  await section.getByRole("button", { name: "編輯詢價", exact: true }).click()
  dialog = page.getByRole("dialog", { name: "編輯詢價", exact: true })
  await dialog.getByLabel(/^報價\*?$/).fill("1500")
  await dialog.getByRole("button", { name: "儲存", exact: true }).click()
  await expect(dialog).toBeHidden()
  await expect(section).toContainText("1,500")
  await section.getByRole("button", { name: "刪除詢價", exact: true }).click()
  dialog = page.getByRole("dialog", { name: "刪除詢價", exact: true })
  await dialog.getByRole("button", { name: "刪除詢價", exact: true }).click()
  await expect(dialog).toBeHidden()
  await expect(section).toContainText("尚無詢價")
  await section.getByRole("button", { name: "新增詢價", exact: true }).click()
  dialog = page.getByRole("dialog", { name: "新增詢價", exact: true })
  await dialog.getByLabel(/^廠商\*?$/).selectOption({ label: `${data.name}` })
  await dialog.getByLabel(/^報價\*?$/).fill("1800")
  await dialog.getByLabel(/^匯率\*?$/).fill("2")
  await dialog.getByRole("button", { name: "儲存", exact: true }).click()
  await expect(dialog).toBeHidden()
  await page.getByRole("button", { name: "審核建檔", exact: true }).click()
  dialog = page.getByRole("dialog")
  await dialog.getByRole("button", { name: "審核建檔", exact: true }).click()
  await page.getByRole("link", { name: "查看已建檔商品", exact: true }).click()
  await expect(page).toHaveURL(/\/products\/[0-9a-f-]+$/)
  await expect(page.getByText("TWD 3,600", { exact: true }).first()).toBeVisible()
})

workspaceTest("手機英文暫存詢價與預填狀態不溢出", async ({ page }) => {
  const data = seed()
  await page.context().addCookies([{ name: "locale", value: "en", url: process.env.E2E_BASE_URL! }])
  await page.setViewportSize({ width: 390, height: 844 })
  await open(page, data.id)
  await expect(page.getByRole("region", { name: "Vendor quotes", exact: true })).toBeVisible()
  await expect(page.getByRole("button", { name: "Run prefill again", exact: true })).toHaveCount(0)
  await expect(page.getByText("AI prefill is unavailable: Gemini API key is not configured.",
    { exact: true })).toBeVisible()
  await page.getByRole("button", { name: "Add quote", exact: true }).click()
  await expect(page.getByRole("dialog", { name: "Add quote", exact: true })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})


workspaceTest("AI 報價顯示於暫存且不提供重新預填", async ({ page }) => {
  const data = fixture({ name: `AI ${randomUUID().slice(0, 8)}`, ai: "yes" })
  await open(page, data.id)
  await expect(page.getByLabel("名稱", { exact: true })).toHaveValue("AI 商品")
  await expect(page.getByRole("button", { name: "重新預填", exact: true })).toHaveCount(0)
  const quotes = page.getByRole("region", { name: "廠商詢價", exact: true })
  await expect(quotes.getByText(`${data.name} buyer`, { exact: true })).toBeVisible()
  await quotes.getByRole("button", { name: "編輯詢價", exact: true }).click()
  const dialog = page.getByRole("dialog", { name: "編輯詢價", exact: true })
  await expect(dialog.getByLabel(/^報價\*?$/)).toHaveValue("100")
  await expect(dialog.getByLabel(/^匯率\*?$/)).toHaveValue("4.5")
  await dialog.getByRole("button", { name: "取消", exact: true }).click()
  await page.getByLabel("名稱", { exact: true }).fill("人工修正")
  await draftMenu(page, "儲存暫存")
  await expect(page.getByRole("status")).toContainText("已儲存")
  await page.reload()
  await expect(page.getByLabel("名稱", { exact: true })).toHaveValue("人工修正")
})

workspaceTest("手機與窄桌面頁首的標題和操作按鈕保持可見且不互相遮擋", async ({ page }) => {
  test.setTimeout(90_000)
  const data = seed()
  await page.context().addCookies(managerState!.cookies)
  const paths = ["/products", "/product-drafts", "/admin/users", "/admin/draft-prefill",
    "/admin/registration", `/product-drafts/${data.id}`]
  for (const width of [320, 390, 720, 900, 1280]) {
    await page.setViewportSize({ width, height: 844 })
    for (const path of paths) {
      await page.goto(path)
      await expectHeaderFits(page)
    }
  }
})

async function expectSingleRowHeader(page: Page) {
  await expectHeaderFits(page)
  const layout = await page.getByRole("heading", { level: 1 }).evaluate((heading) => {
    const header = heading.closest("header")!
    const title = heading.getBoundingClientRect()
    return [...header.querySelectorAll("button")]
      .filter((button) => button.getBoundingClientRect().width > 0)
      .map((button) => {
        const box = button.getBoundingClientRect()
        return { center: box.y + box.height / 2, titleCenter: title.y + title.height / 2,
          text: button.textContent }
      })
  })
  expect(layout.length).toBeGreaterThan(0)
  expect(layout.length).toBeLessThanOrEqual(3)
  for (const control of layout) {
    expect(Math.abs(control.center - control.titleCenter)).toBeLessThan(2)
    expect(control.text).toBe("")
  }
}

workspaceTest("英文手機暫存標題與圖示維持單排", async ({ page }) => {
  const data = seed()
  await page.context().addCookies([{ name: "locale", value: "en", url: process.env.E2E_BASE_URL! }])
  await open(page, data.id)
  for (const width of [320, 390, 720, 900, 1280]) {
    await page.setViewportSize({ width, height: 844 })
    await expectHeaderFits(page)
    if (width <= 720) await expectSingleRowHeader(page)
    for (const name of ["Reload data", "Approve and create product"]) {
      await page.getByRole("button", { name, exact: true }).click({ trial: true })
    }
    await page.locator("header").getByRole("button", { name: "Actions", exact: true }).click()
    const sheet = page.getByRole("dialog", { name: "Actions", exact: true })
    for (const name of ["Save draft", "Discard draft"]) {
      await sheet.getByRole("menuitem", { name, exact: true }).click({ trial: true })
    }
    await sheet.getByRole("button", { name: "Close", exact: true }).click()
  }
  await page.setViewportSize({ width: 320, height: 844 })
  await page.getByRole("button", { name: "Reload data", exact: true }).click()
  await expect(page.getByRole("status")).toContainText("Latest data loaded")
  await page.locator("header").getByRole("button", { name: "Actions", exact: true }).click()
  await page.getByRole("menuitem", { name: "Discard draft", exact: true }).click()
  await expect(page.getByRole("dialog", { name: "Actions", exact: true })).toHaveCount(0)
  await expect(page.getByRole("dialog", { name: "Discard draft", exact: true })).toBeVisible()
  await page.getByRole("button", { name: "Cancel", exact: true }).click()
  await page.goto("/product-drafts")
  await expectSingleRowHeader(page)
  await page.locator("header").getByRole("button", { name: "Filter", exact: true }).click()
  await expect(page.getByRole("dialog", { name: "Filter", exact: true })).toBeVisible()
})

workspaceTest("手機暫存以重整圖示與操作面板完成整理流程", async ({ page }) => {
  test.setTimeout(90_000)
  const data = seed()
  await page.setViewportSize({ width: 320, height: 844 })
  await page.goto("/product-drafts")
  await expectSingleRowHeader(page)
  await page.getByRole("button", { name: "重新整理", exact: true }).click()
  await page.locator("header").getByRole("button", { name: "篩選", exact: true }).click()
  const filter = page.getByRole("dialog")
  await filter.getByLabel("來源群組").selectOption(data.source)
  await filter.getByRole("button", { name: "篩選", exact: true }).click()
  await expect(filter).toBeHidden()
  await expect(page).toHaveURL(new RegExp(`source_key=${encodeURIComponent(data.source)}`))
  await expect(page.locator("header").getByRole("button", { name: "篩選（1）", exact: true })).toBeVisible()
  await open(page, data.id)
  await expectSingleRowHeader(page)
  await fillRequired(page, data.name, data.brand)
  await page.getByRole("button", { name: "重新載入資料", exact: true }).click()
  await expect(page.getByRole("status")).toContainText("已載入最新資料")
  await expect(page.getByLabel("名稱", { exact: true })).toHaveValue(data.name)
  await page.locator("header").getByRole("button", { name: "操作選單", exact: true }).click()
  await page.getByRole("menuitem", { name: "儲存暫存", exact: true }).click()
  await expect(page.getByRole("status")).toContainText("已儲存")
  await page.reload()
  await expect(page.getByLabel("名稱", { exact: true })).toHaveValue(data.name)
  fixture({ conflict: data.id })
  await page.locator("header").getByRole("button", { name: "操作選單", exact: true }).click()
  await page.getByRole("menuitem", { name: "儲存暫存", exact: true }).click()
  await expect(page.getByRole("main").getByRole("alert")).toContainText("資料已變更")
  await page.locator("header").getByRole("button", { name: "操作選單", exact: true }).click()
  for (const name of ["儲存暫存", "放棄暫存"]) {
    await expect(page.getByRole("menuitem", { name, exact: true })).toBeDisabled()
  }
  await page.getByRole("dialog").getByRole("button", { name: "關閉", exact: true }).click()
  await page.getByRole("button", { name: "重新載入資料", exact: true }).click()
  await expect(page.getByRole("status")).toContainText("已載入最新資料")
  await fillRequired(page, data.name, data.brand)
  await expect(page.locator("header").getByRole("button", { name: "審核建檔", exact: true })).toBeEnabled()
  await page.locator("header").getByRole("button", { name: "審核建檔", exact: true }).click()
  const approve = page.getByRole("dialog", { name: "審核建檔", exact: true })
  await expect(page.getByRole("dialog", { name: "操作選單", exact: true })).toHaveCount(0)
  await approve.getByRole("button", { name: "審核建檔", exact: true }).click()
  await expect(page.getByRole("link", { name: "查看已建檔商品", exact: true })).toBeVisible()
  await open(page, data.second)
  await page.locator("header").getByRole("button", { name: "操作選單", exact: true }).click()
  await page.getByRole("menuitem", { name: "放棄暫存", exact: true }).click()
  await page.getByRole("dialog").getByRole("button", { name: "取消", exact: true }).click()
  await expect(page).toHaveURL(`/product-drafts/${data.second}`)
  await page.locator("header").getByRole("button", { name: "操作選單", exact: true }).click()
  await page.getByRole("menuitem", { name: "放棄暫存", exact: true }).click()
  await page.getByRole("dialog").getByRole("button", { name: "放棄暫存", exact: true }).click()
  await expect(page).toHaveURL("/product-drafts")
})

workspaceTest("收集中與處理中停用審核且直接網址不顯示整理表單", async ({ page }) => {
  for (const flag of ["collecting", "processing"]) {
    const data = fixture({ name: `Blocked ${randomUUID().slice(0, 8)}`, [flag]: "true" })
    await page.goto(`/product-drafts?source_key=${encodeURIComponent(data.source)}`)
    await expect(page.getByRole("button", { name: "審核", exact: true })).toBeDisabled()
    await open(page, data.id)
    await expect(page.getByLabel("名稱", { exact: true })).toHaveCount(0)
    await expect(page.getByRole("main")).toContainText(flag === "collecting" ? "收集中" : "處理中")
  }
})

workspaceTest("待確認原文可加入商品且忽略剩餘異常後恢復審核", async ({ page }) => {
  const data = fixture({ name: `Issue ${randomUUID().slice(0, 8)}`, issue: "true" })
  await page.goto(`/product-drafts?source_key=${encodeURIComponent(data.source)}`)
  await page.getByRole("link", { name: "處理待確認訊息", exact: true }).first().click()
  const text = page.getByRole("article").filter({ hasText: "同時到達待確認文字" })
  await text.getByLabel("目標商品", { exact: true }).selectOption(data.id)
  await text.getByRole("button", { name: "加入商品", exact: true }).click()
  await expect(text).toHaveCount(0)
  const image = page.getByRole("article").filter({ hasText: "圖片訊息" })
  await image.getByRole("button", { name: "忽略訊息", exact: true }).click()
  await page.getByRole("dialog").getByRole("button", { name: "忽略訊息", exact: true }).click()
  await expect(image).toHaveCount(0)
  await open(page, data.id)
  await expect(page.getByLabel("名稱", { exact: true })).toBeVisible()
  await expect(page.getByRole("button", { name: "同時到達待確認文字", exact: true })).toBeVisible()
})

workspaceTest("審核後自動開啟同群組下一筆並在沒有下一筆時返回列表", async ({ page }) => {
  const data = seed()
  await page.goto(`/product-drafts/${data.id}?source_key=${encodeURIComponent(data.source)}`)
  await fillRequired(page, data.name, data.brand)
  await page.getByRole("button", { name: "審核建檔", exact: true }).click()
  await page.getByRole("dialog").getByRole("button", { name: "審核建檔", exact: true }).click()
  await expect(page).toHaveURL(new RegExp(`/product-drafts/${data.second}\\?`))
  await expect(page).toHaveURL(new RegExp(`source_key=${encodeURIComponent(data.source)}`))
  await expect(page.getByRole("link", { name: "查看已建檔商品", exact: true })).toBeVisible()
  const last = fixture({ name: `Last ${randomUUID().slice(0, 8)}`, single: "true" })
  await page.goto(`/product-drafts/${last.id}?source_key=${encodeURIComponent(last.source)}`)
  await fillRequired(page, last.name, last.brand)
  await page.getByRole("button", { name: "審核建檔", exact: true }).click()
  await page.getByRole("dialog").getByRole("button", { name: "審核建檔", exact: true }).click()
  await expect(page).toHaveURL(/\/product-drafts\?source_key=/)
  await expect(page.getByRole("status")).toContainText("目前沒有待審核商品")
})

workspaceTest("下一筆暫存已被他人移除時重新尋找同群組待審核商品", async ({ page }) => {
  const data = seed()
  await page.goto(`/product-drafts/${randomUUID()}?source_key=${encodeURIComponent(data.source)}`
    + `&created=${randomUUID()}`)
  await expect(page).toHaveURL(new RegExp(`/product-drafts/${data.id}\\?`))
  await expect(page).toHaveURL(new RegExp(`source_key=${encodeURIComponent(data.source)}`))
  await expect(page.getByLabel("名稱", { exact: true })).toBeVisible()
})

workspaceTest("尚未產生暫存商品列時列表仍顯示處理中", async ({ page }) => {
  const data = fixture({ name: `Queued ${randomUUID().slice(0, 8)}`, buffer: "true" })
  await page.goto(`/product-drafts?source_key=${encodeURIComponent(data.source)}`)
  await expect(page.getByRole("status")).toContainText("處理中")
  await expect(page.getByRole("link", { name: "審核", exact: true })).toHaveCount(0)
})

workspaceTest("手機頁首直接開啟新增與篩選", async ({ page }) => {
  await page.context().addCookies(managerState!.cookies)
  await page.setViewportSize({ width: 320, height: 844 })
  await page.goto("/admin/users")
  await expectHeaderFits(page)
  const header = page.locator("header")
  await header.getByRole("button", { name: "篩選", exact: true }).click()
  await expect(page.getByRole("dialog")).toBeVisible()
  await page.getByRole("dialog").getByRole("button", { name: "關閉", exact: true }).click()
  await header.getByRole("button", { name: "新增員工", exact: true }).click()
  await expect(page.getByRole("dialog", { name: "新增員工", exact: true })).toBeVisible()
})

workspaceTest("商品列表頁首整合篩選與暫存且窄螢幕不溢出", async ({ page }) => {
  for (const width of [320, 390, 720, 1280]) {
    await page.setViewportSize({ width, height: 844 })
    await page.goto("/products")
    await expectSingleRowHeader(page)
    const header = page.locator("header")
    await expect(header.getByRole("button")).toHaveCount(3)
    for (const name of ["重新整理", "新增商品", "操作選單"]) {
      await expect(header.getByRole("button", { name, exact: true })).toBeVisible()
    }
    await expect(page.getByRole("button", { name: "篩選", exact: true })).toHaveCount(0)
    await expect(header.getByRole("button", { name: "商品暫存", exact: true })).toHaveCount(0)
    for (const nav of await page.getByRole("navigation").all()) {
      await expect(nav.getByRole("link", { name: "商品暫存", exact: true })).toHaveCount(0)
    }
    await header.getByRole("button", { name: "操作選單", exact: true }).click()
    await page.getByRole("menuitem", { name: "篩選", exact: true }).click()
    await expect(page.getByRole("dialog", { name: "操作選單", exact: true })).toBeHidden()
    await expect(page.getByRole("dialog")).toBeVisible()
    await page.getByRole("dialog").getByRole("button", { name: "關閉", exact: true }).click()
    await header.getByRole("button", { name: "操作選單", exact: true }).click()
    await page.getByRole("menuitem", { name: "商品暫存", exact: true }).click()
    await expect(page).toHaveURL("/product-drafts")
  }
})

workspaceTest("管理導覽將註冊碼設定放在最後", async ({ page }) => {
  await page.context().addCookies(managerState!.cookies)
  await page.goto("/admin/users")
  const links = page.getByRole("navigation", { name: "主要導覽", exact: true }).getByRole("link")
  await expect(links.last()).toHaveText("註冊碼設定")
})

workspaceTest("AI 助手以卡片右上角新增條件且隱藏冗餘標籤", async ({ page }) => {
  await page.context().addCookies(managerState!.cookies)
  for (const width of [320, 1280]) {
    await page.setViewportSize({ width, height: 844 })
    await page.goto("/admin/draft-prefill")
    const card = page.getByRole("region", { name: "審核預填", exact: true })
    await expect(card.getByRole("heading", { name: "補充條件", exact: true })).toHaveCount(0)
    await expect(card.getByText("測試文字", { exact: true })).toHaveCount(0)
    await expect(card.getByRole("textbox", { name: "測試文字", exact: true })).toBeVisible()
    const add = card.getByRole("button", { name: "新增條件", exact: true })
    const heading = card.getByRole("heading", { name: "審核預填", exact: true })
    const box = (await add.boundingBox())!
    const title = (await heading.boundingBox())!
    expect(Math.abs(box.y + box.height / 2 - title.y - title.height / 2)).toBeLessThan(2)
    expect(box.x).toBeGreaterThan(title.x + title.width)
    await add.click()
    await expect(card.getByRole("textbox", { name: /^補充條件 \d+$/ }).last()).toBeVisible()
  }
})
