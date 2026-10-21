import { expect, it } from "vitest"
import { gallerySelection, statusTimeline } from "@/modules/products/capabilities"
import type { PhotoInfo, StatusHistoryInfo } from "@/modules/products/types"

const photos: PhotoInfo[] = [
  { id: "side", url: "/side.webp", is_main: false, sort_order: 2 },
  { id: "main", url: "/main.webp", is_main: true, sort_order: 3 },
  { id: "back", url: "/back.webp", is_main: false, sort_order: 1 },
]

it("圖庫預設主圖並保留縮圖排序", () => {
  const result = gallerySelection(photos, null)
  expect(result.photos.map((photo) => photo.id)).toEqual(["main", "back", "side"])
  expect(result.selected?.id).toBe("main")
  expect(gallerySelection(photos, "side").selected?.id).toBe("side")
  expect(photos[0].id).toBe("side")
})

it("圖庫選取失效時回到主圖，空圖庫回傳空值", () => {
  expect(gallerySelection(photos, "deleted").selected?.id).toBe("main")
  expect(gallerySelection(photos.filter((photo) => !photo.is_main), null).selected?.id)
    .toBe("back")
  expect(gallerySelection([], "deleted")).toEqual({ photos: [], selected: null })
})

function history(id: string, date: string, status: "sold" | "not_acquired", action: string,
  reason: string | null = null): StatusHistoryInfo {
  return { id, changed_at: date, from_status: status === "sold" ? "not_acquired" : "sold",
    to_status: status, action, reason, changed_by: "actor", operator_name: "店長" }
}

it("流向依時間排列並保留成交退回原因", () => {
  const created = "2026-10-20T01:00:00Z"
  const returned = history("return", "2026-10-21T01:00:00Z", "not_acquired", "return", "退貨")
  const sale = history("sale", "2026-10-20T03:00:00Z", "sold", "sale")
  const resold = history("resold", "2026-10-21T03:00:00Z", "sold", "sale")
  const rows = statusTimeline([resold, returned, sale], created)
  expect(rows.map((row) => row.to_status)).toEqual(["not_acquired", "sold", "not_acquired", "sold"])
  expect(rows[0].changed_at).toBe(created)
  expect(rows[2]).toEqual(returned)
  const initial = { ...history("create", created, "not_acquired", "create"), from_status: null }
  expect(statusTimeline([sale, initial], created)).toEqual([initial, sale])
})

it("空歷程以建立事件顯示未收購", () => {
  const rows = statusTimeline([], "2026-10-20T01:00:00Z")
  expect(rows).toHaveLength(1)
  expect(rows[0]).toMatchObject({ to_status: "not_acquired", action: "create",
    from_status: null, changed_at: "2026-10-20T01:00:00Z" })
})
