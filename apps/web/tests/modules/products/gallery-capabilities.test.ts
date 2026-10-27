import { expect, it } from "vitest"
import { gallerySelection } from "@/modules/products/capabilities"
import type { PhotoInfo } from "@/modules/products/types"

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

