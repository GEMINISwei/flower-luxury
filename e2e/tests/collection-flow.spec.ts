import { execFileSync } from "node:child_process"
import { randomUUID } from "node:crypto"
import { expect, test as base, type BrowserContext, type Page } from "@playwright/test"
import { admin, login } from "./support"

let manager: Awaited<ReturnType<BrowserContext["storageState"]>> | undefined
const test = base.extend({
  storageState: async ({ browser, baseURL }, use) => {
    if (!manager) {
      const context = await browser.newContext({ baseURL })
      try {
        const page = await context.newPage()
        await login(page, admin)
        manager = await context.storageState()
      } finally { await context.close() }
    }
    await use(manager)
  },
})

const script = String.raw`
import asyncio, json, os, sys, uuid
from datetime import timedelta
from io import BytesIO
from PIL import Image
from sqlalchemy import select
from app.server import app
from modules.line_collection.model import discover_group
from modules.product_drafts import model, raw_photos, rounds
from modules.product_drafts.schema import IncomingMessage
from shared.db.session import configure_session_factory, create_engine, session_scope
from shared.time import utc_now

async def main():
    engine = create_engine(os.environ["POSTGRES_URL"])
    configure_session_factory(engine)
    async with session_scope():
        args = json.loads(sys.argv[1])
        if args.get("source"):
            source = args["source"]
            first = await active_first(source)
            await rounds.receive_message(IncomingMessage(source_key=source,
                external_id=uuid.uuid4().hex, kind="text", text="晚到待確認內容",
                occurred_at=first.occurred_at + timedelta(milliseconds=500)))
            rows = list(await model.active_session().scalars(select(model.DraftTable).where(
                model.DraftTable.source_key == source)))
            print(json.dumps({"draft": str(rows[0].id), "snapshot": rows[0].finalized_snapshot}))
        else:
            key = "C" + uuid.uuid4().hex
            group, _ = await discover_group(key)
            group.name, group.enabled = args["name"], True
            source = "line:" + key
            when = utc_now() - timedelta(seconds=30)
            group.collect_from = when - timedelta(seconds=1)
            image = await rounds.receive_message(IncomingMessage(source_key=source,
                external_id=uuid.uuid4().hex, kind="image", occurred_at=when))
            output = BytesIO()
            Image.new("RGB", (8, 4), "red").save(output, "PNG")
            await raw_photos.save_original(image.message_id, output.getvalue(), "original.png")
            await rounds.receive_message(IncomingMessage(source_key=source,
                external_id=uuid.uuid4().hex, kind="text", text="手袋原文",
                occurred_at=when + timedelta(seconds=2)))
            current = await rounds.current_collection(source)
            print(json.dumps({"source": source, "round": current.id, "name": args["name"]}))
    await engine.dispose()

async def active_first(source):
    return await model.active_session().scalar(select(model.MessageTable).where(
        model.MessageTable.source_key == source, model.MessageTable.kind == "image")
        .order_by(model.MessageTable.occurred_at))

asyncio.run(main())
`

function fixture(args: Record<string, string>) {
  const project = process.env.COMPOSE_PROJECT_NAME
  if (!project?.endsWith("-e2e")) throw new Error("Disposable stack required")
  return JSON.parse(execFileSync("docker", ["exec", `${project}-api`, "python", "-c", script,
    JSON.stringify(args)], { encoding: "utf8" })) as {
    source: string; round: string; name: string; draft?: string; snapshot?: unknown
  }
}

async function complete(page: Page, source: string) {
  await page.goto(`/product-drafts?source_key=${encodeURIComponent(source)}`)
  await page.getByRole("button", { name: "收集完成", exact: true }).click()
  const dialog = page.getByRole("dialog")
  await dialog.getByRole("button", { name: "收集完成", exact: true }).click()
  await expect(dialog).toBeHidden()
  await page.getByRole("link", { name: "確認分組", exact: true }).click()
}

test("收集完成後先確認分組，定稿才進行加工並開放審核", async ({ page }) => {
  const data = fixture({ name: `Collection ${randomUUID().slice(0, 8)}` })
  await page.goto(`/product-drafts?source_key=${encodeURIComponent(data.source)}`)
  await expect(page.getByRole("status")).toContainText("已收到 2 則訊息")
  await expect(page.getByRole("link", { name: "審核", exact: true })).toHaveCount(0)
  await complete(page, data.source)
  await expect(page.getByRole("heading", { name: "確認商品分組" })).toBeVisible()
  await expect(page.getByText("手袋原文", { exact: true })).toBeVisible()
  await expect(page.getByLabel("名稱", { exact: true })).toHaveCount(0)
  await page.getByRole("button", { name: "確認分組並定稿", exact: true }).click()
  await page.getByRole("dialog").getByRole("button", { name: "確認分組並定稿", exact: true }).click()
  await page.goto(`/product-drafts?source_key=${encodeURIComponent(data.source)}`)
  await expect.poll(async () => {
    await page.reload()
    return page.getByRole("link", { name: "審核", exact: true }).count()
  }, { timeout: 30_000 }).toBe(1)
})

test("遲到訊息由人工加入未定稿商品，加入後仍需確認定稿", async ({ page }) => {
  const data = fixture({ name: `Late ${randomUUID().slice(0, 8)}` })
  await complete(page, data.source)
  const late = fixture({ source: data.source })
  await page.goto(`/product-drafts/issues?source_key=${encodeURIComponent(data.source)}`)
  await expect(page.getByText("晚到待確認內容", { exact: true })).toBeVisible()
  await page.getByRole("combobox").selectOption(late.draft!)
  await page.getByRole("button", { name: "加入商品", exact: true }).click()
  await expect(page.getByText("沒有待確認訊息。", { exact: true })).toBeVisible()
  await page.goto(`/product-drafts/${late.draft}`)
  await expect(page.getByText("晚到待確認內容", { exact: true })).toBeVisible()
  await expect(page.getByRole("button", { name: "確認分組並定稿", exact: true })).toBeEnabled()
})

test("定稿後遲到訊息不再加入原組別或觸發二次處理", async ({ page }) => {
  const data = fixture({ name: `Frozen ${randomUUID().slice(0, 8)}` })
  await complete(page, data.source)
  await page.getByRole("button", { name: "確認分組並定稿", exact: true }).click()
  await page.getByRole("dialog").getByRole("button", { name: "確認分組並定稿", exact: true }).click()
  await expect(page.getByRole("dialog")).toBeHidden()
  const late = fixture({ source: data.source })
  expect(JSON.stringify(late.snapshot)).not.toContain("晚到待確認內容")
  await page.goto(`/product-drafts/issues?source_key=${encodeURIComponent(data.source)}`)
  await expect(page.getByText("晚到待確認內容", { exact: true })).toBeVisible()
  await expect(page.getByRole("combobox").getByRole("option", { includeHidden: true })).toHaveCount(1)
  await expect(page.getByRole("button", { name: "加入商品", exact: true })).toBeDisabled()
})
