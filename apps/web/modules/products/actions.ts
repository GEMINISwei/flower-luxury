"use server"

import { redirect } from "next/navigation"
import { apiDelete, apiPatch, apiPost, apiUpload } from "@/shared/api/request.server"
import type { ApiRequestBody } from "@/shared/api/contract"
import { fetchPaginatedList } from "@/shared/pagination/fetch.server"
import { getT } from "@/shared/i18n/locale.server"
import { getLocale } from "@/shared/i18n/locale.server"
import { validatePhotoBatch } from "./validation"
import { productListQuery } from "./capabilities"
import { productMessages } from "./i18n"
import { PRODUCTS_PATH } from "./manifest"

const refresh = { path: PRODUCTS_PATH }

export async function loadProductPage(filters: Record<string, string>, cursor: string) {
  const t = await getT(productMessages)
  return fetchPaginatedList({ url: "/products/", cursor, direction: "next", limit: 20,
    query: productListQuery(filters), errorFallback: t("failed") })
}

export async function createProduct(data: ApiRequestBody<"/products/", "post">) {
  return apiPost({ url: "/products/", data, refresh })
}

export async function updateProduct(id: string, data: ApiRequestBody<"/products/{id}", "patch">) {
  return apiPatch({ url: "/products/{id}", params: { id }, data, refresh })
}

export async function deleteProduct(id: string) {
  const result = await apiDelete({ url: "/products/{id}", params: { id }, refresh })
  if (result.status === "success" || result.status === "info") {
    // 刪除後不再算繪目前詳情頁, 直接讓 Server Action 導向列表.
    redirect(PRODUCTS_PATH)
  }
  return result
}

export async function uploadPhotos(id: string, data: FormData) {
  const files = data.getAll("files").filter((file): file is File => file instanceof File)
  const error = validatePhotoBatch(files, await getLocale())
  if (error) return { status: "failure" as const, code: 422, data: { detail: error }, message: error }
  const body = new FormData()
  files.forEach((file) => body.append("files", file))
  return apiUpload({ url: "/products/{id}/photos", params: { id }, data: body, refresh })
}

export async function setMainPhoto(id: string, photo_id: string) {
  return apiPatch({ url: "/products/{id}/photos/main", params: { id }, data: { photo_id }, refresh })
}

export async function deletePhoto(id: string, photo_id: string) {
  return apiDelete({ url: "/products/{id}/photos/{photo_id}", params: { id, photo_id }, refresh })
}
