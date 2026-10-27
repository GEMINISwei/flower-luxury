import { expect, it } from "vitest"
import { selectProductPhotos, productFormCapabilities } from "@/modules/products/capabilities"

const photo = (name: string, size = 100) => ({ name, size, type: "image/jpeg" })

it("選檔與連續拍照依加入順序累加且不更動原清單", () => {
  const current = [photo("first.jpg")]
  const incoming = [photo("camera.jpg"), photo("another.jpg")]
  expect(selectProductPhotos(current, incoming, "zh")).toEqual({ files: [...current, ...incoming] })
  expect(current).toHaveLength(1)
})

it("取消相機或選檔保留原有照片", () => {
  expect(selectProductPhotos([], [], "zh")).toEqual({ files: [] })
  const current = [photo("first.jpg")]
  expect(selectProductPhotos(current, [], "en")).toEqual({ files: current })
})

it("累加超過十五 MiB 或格式無效時保留原清單並提供中英錯誤", () => {
  const current = [photo("first.jpg", 8 * 1024 * 1024)]
  for (const locale of ["zh", "en"] as const) {
    for (const incoming of [[photo("second.jpg", 8 * 1024 * 1024)],
      [photo("bad.svg")], [photo("empty.jpg", 0)]]) {
      const result = selectProductPhotos(current, incoming, locale)
      expect(result.files).toBe(current)
      expect(result.error).toBeTruthy()
    }
  }
})

it("建立後照片失敗時鎖定已存欄位並允許補傳與移除照片", () => {
  expect(productFormCapabilities(false, "product-1", false)).toEqual({
    fieldsDisabled: true, showPhotos: true, canSelectPhotos: true, retryPhotos: true,
  })
  expect(productFormCapabilities(false, null, false)).toEqual({
    fieldsDisabled: false, showPhotos: true, canSelectPhotos: true, retryPhotos: false,
  })
  expect(productFormCapabilities(false, "product-1", true)).toEqual({
    fieldsDisabled: true, showPhotos: true, canSelectPhotos: false, retryPhotos: true,
  })
  expect(productFormCapabilities(true, null, false)).toEqual({
    fieldsDisabled: false, showPhotos: false, canSelectPhotos: false, retryPhotos: false,
  })
})
