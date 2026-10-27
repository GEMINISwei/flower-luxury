import { apiUpload } from "@/shared/api/request.server"

export async function acceptsPhotoUpload() {
  const result = await apiUpload({
    url: "/products/{id}/photos", params: { id: "product" }, data: new FormData(),
  })
  if (result.status === "success") return result.data.list_data[0]?.is_main
}

export async function rejectsWrongUploadContract() {
  // @ts-expect-error JSON 端點不接受 multipart 上傳.
  await apiUpload({ url: "/products/", data: new FormData() })
  // @ts-expect-error 缺少路徑參數.
  await apiUpload({ url: "/products/{id}/photos", data: new FormData() })
  // @ts-expect-error 不能以 JSON 物件取代 FormData.
  await apiUpload({ url: "/products/{id}/photos", params: { id: "product" }, data: { files: [] } })
}
