import { describe, expect, it } from "vitest"
import { AREA_ROUTES } from "@/config/routes"
import { getAccountMenuEntries } from "@/config/shell/account-menu"

const labels = (entries: ReturnType<typeof getAccountMenuEntries>) => entries.map((e) => e.label)

describe("getAccountMenuEntries", () => {
  it("超級管理者在使用者區看得到管理後台的入口，連到第一個管理頁", () => {
    const entries = getAccountMenuEntries("user", ["*"])

    expect(labels(entries)).toEqual(["goAdminArea", "accountSettings", "systemSettings", "logout"])
    expect(entries[0]).toMatchObject({ href: AREA_ROUTES.admin[0].path })
  })

  it("在管理區一律能回使用者區", () => {
    const entries = getAccountMenuEntries("admin", ["*"])

    expect(labels(entries)).toEqual(["goUserArea", "accountSettings", "systemSettings", "logout"])
    expect(entries[0]).toMatchObject({ href: "/products" })
  })

  it("一般帳號可分別進入用戶設定與系統設定", () => {
    const entries = getAccountMenuEntries("user", [])
    expect(labels(entries)).toEqual(["accountSettings", "systemSettings", "logout"])
    expect(entries[0]).toMatchObject({ href: "/settings" })
    expect(entries[1]).toMatchObject({ href: "/settings/system" })
  })
})
