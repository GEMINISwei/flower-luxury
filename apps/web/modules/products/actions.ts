"use server"

import { apiDelete, apiPatch, apiPost } from "@/shared/api/request.server"
import type { ApiRequestBody } from "@/shared/api/contract"
import type { ProductStatus } from "./types"
import { PRODUCTS_PATH } from "./manifest"
import { sendPhotoBatch } from "./photo-upload.server"

const refresh = { path: PRODUCTS_PATH }

export async function createProduct(data: ApiRequestBody<"/products/", "post">) {
  return apiPost({ url: "/products/", data, refresh })
}

export async function updateProduct(id: string, data: ApiRequestBody<"/products/{id}", "patch">) {
  return apiPatch({ url: "/products/{id}", params: { id }, data, refresh })
}

export async function deleteProduct(id: string) {
  return apiDelete({ url: "/products/{id}", params: { id }, refresh })
}

export async function changeStatus(id: string, to_status: ProductStatus, reason: string) {
  return apiPost({ url: "/products/{id}/status", params: { id },
    data: { to_status, reason }, refresh })
}

export async function returnStatus(id: string, to_status: ProductStatus, reason: string) {
  return apiPost({ url: "/products/{id}/return", params: { id },
    data: { to_status, reason }, refresh })
}

export async function setMainPhoto(id: string, photo_id: string) {
  return apiPatch({ url: "/products/{id}/photos/main", params: { id },
    data: { photo_id }, refresh })
}

export async function deletePhoto(id: string, photo_id: string) {
  return apiDelete({ url: "/products/{id}/photos/{photo_id}", params: { id, photo_id }, refresh })
}

export async function uploadPhotos(id: string, data: FormData) {
  return sendPhotoBatch(id, data)
}
