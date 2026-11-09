import { expect } from "@playwright/test"
import { SIGNED_OUT, login, test } from "../support"

test.use({ storageState: SIGNED_OUT })

test("一般帳號進入管理區會被導回商品列表", async ({ page, member }) => {
    await login(page, member)

    await page.goto("/admin/users")

    await expect(page).toHaveURL("/products")
  })
