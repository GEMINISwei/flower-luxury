"use server"

import { redirect } from "next/navigation"
import { revalidatePath } from "next/cache"
import { apiDelete, apiPatch, apiPost, apiUpload } from "@/shared/api/request.server"
import type { ApiRequestBody } from "@/shared/api/contract"
import { fetchPaginatedList } from "@/shared/pagination/fetch.server"
import { getT } from "@/shared/i18n/locale.server"
import { getLocale } from "@/shared/i18n/locale.server"
import { validatePhotoBatch } from "./validation"
import { productListQuery } from "./capabilities"
import { productMessages } from "./i18n"
import type { ProductStatus } from "./types"
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
  const result = await apiPatch({ url: "/products/{id}", params: { id }, data, refresh })
  // 成本更新要隨 Action 一起刷新詳情, 避免關閉表單後立刻用舊成本確認成交.
  if (result.status === "success") revalidatePath(`${PRODUCTS_PATH}/${id}`)
  return result
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

export async function returnStatus(id: string, to_status: ProductStatus, reason: string) {
  return apiPost({ url: "/products/{id}/return", params: { id },
    data: { to_status, reason }, refresh })
}

export async function createQuote(id: string, data: ApiRequestBody<"/products/{id}/quotes", "post">) {
  return apiPost({ url: "/products/{id}/quotes", params: { id }, data, refresh })
}

export async function updateQuote(
  id: string, quote_id: string, data: ApiRequestBody<"/products/{id}/quotes/{quote_id}", "patch">,
) {
  return apiPatch({ url: "/products/{id}/quotes/{quote_id}", params: { id, quote_id }, data, refresh })
}

export async function deleteQuote(id: string, quote_id: string) {
  return apiDelete({ url: "/products/{id}/quotes/{quote_id}", params: { id, quote_id }, refresh })
}

export async function confirmSale(id: string, data: ApiRequestBody<"/products/{id}/sales", "post">) {
  return apiPost({ url: "/products/{id}/sales", params: { id }, data, refresh })
}
