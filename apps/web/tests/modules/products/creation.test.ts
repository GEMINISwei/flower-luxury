import { expect, it, vi } from "vitest"
import type { ApiResponse } from "@/shared/api/contract"
import { saveProductWithPhotos } from "@/modules/products/creation"

const created: ApiResponse<{ id: string }> = {
  status: "success", code: 200, data: { id: "product-1" }, message: "Created",
}
const failed: ApiResponse = {
  status: "failure", code: 422, data: { detail: "Rejected" }, message: "Rejected",
}
const photo = new File(["photo"], "camera.jpg", { type: "image/jpeg" })

function dependencies() {
  return {
    save: vi.fn(async () => created),
    upload: vi.fn<(id: string, body: FormData) => Promise<ApiResponse>>().mockResolvedValue({
      status: "success", code: 200, data: {}, message: "Uploaded",
    }),
    onCreated: vi.fn<(id: string) => void>(),
  }
}

it("未選照片可直接建立商品", async () => {
  const deps = dependencies()
  expect(await saveProductWithPhotos({ files: [], ...deps })).toEqual(created)
  expect(deps.save).toHaveBeenCalledOnce()
  expect(deps.upload).not.toHaveBeenCalled()
})

it("先建立商品再以同一商品上傳所有選取與拍攝照片", async () => {
  const deps = dependencies()
  const second = new File(["second"], "library.heic", { type: "image/heic" })
  const result = await saveProductWithPhotos({ files: [photo, second], ...deps })
  expect(result).toEqual(created)
  const [id, body] = deps.upload.mock.calls[0]
  expect(id).toBe("product-1")
  expect(body.getAll("files")).toEqual([photo, second])
  expect(deps.onCreated).toHaveBeenCalledWith("product-1")
  expect(deps.onCreated.mock.invocationCallOrder[0])
    .toBeLessThan(deps.upload.mock.invocationCallOrder[0])
})

it("商品建立失敗不傳照片且不記錄商品編號", async () => {
  const deps = dependencies()
  const result = await saveProductWithPhotos({ files: [photo], ...deps,
    save: async () => failed })
  expect(result).toEqual(failed)
  expect(deps.upload).not.toHaveBeenCalled()
  expect(deps.onCreated).not.toHaveBeenCalled()
})

it("照片失敗後保留已建立編號且重試不重複建檔", async () => {
  const deps = dependencies()
  deps.upload.mockResolvedValueOnce(failed)
  expect(await saveProductWithPhotos({ files: [photo], ...deps })).toEqual(failed)
  const productId = deps.onCreated.mock.calls[0][0]
  const result = await saveProductWithPhotos({ files: [photo], productId, ...deps })
  expect(result.status).toBe("success")
  expect(deps.save).toHaveBeenCalledOnce()
  expect(deps.upload).toHaveBeenCalledTimes(2)
  expect(deps.upload.mock.calls.map(([id]) => id)).toEqual(["product-1", "product-1"])
})

it("上傳連線中斷前已記錄商品編號供重試", async () => {
  const deps = dependencies()
  deps.upload.mockRejectedValueOnce(new Error("Offline"))
  await expect(saveProductWithPhotos({ files: [photo], ...deps })).rejects.toThrow("Offline")
  expect(deps.onCreated).toHaveBeenCalledWith("product-1")
})

it("建立後移除全部待傳照片可繼續前往已建立商品", async () => {
  const deps = dependencies()
  const result = await saveProductWithPhotos({ files: [], productId: "product-1", ...deps })
  expect(result.status).toBe("success")
  if (result.status === "success") expect(result.data.id).toBe("product-1")
  expect(deps.save).not.toHaveBeenCalled()
  expect(deps.upload).not.toHaveBeenCalled()
})
