import type { ApiResponse } from "@/shared/api/contract"

export async function saveProductWithPhotos({ productId, files, save, upload, onCreated }: {
  productId?: string | null
  files: readonly File[]
  save: () => Promise<ApiResponse<{ id: string }>>
  upload: (id: string, body: FormData) => Promise<ApiResponse>
  onCreated: (id: string) => void
}): Promise<ApiResponse<{ id: string }>> {
  let result: ApiResponse<{ id: string }> = {
    status: "success", code: 200, data: { id: productId ?? "" }, message: "",
  }
  if (!productId) {
    result = await save()
    if (result.status !== "success") return result
    productId = result.data.id
    // 先保存編號, 上傳失敗或連線中斷後仍可補傳到同一商品.
    onCreated(productId)
  }
  if (files.length) {
    const body = new FormData()
    files.forEach((file) => body.append("files", file))
    const uploaded = await upload(productId, body)
    if (uploaded.status !== "success") return uploaded
  }
  return result
}
