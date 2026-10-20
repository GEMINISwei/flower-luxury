"use server"

import { apiDelete, apiPatch, apiPost } from "@/shared/api/request.server"
import type { ApiRequestBody } from "@/shared/api/contract"

const refresh = { path: "/vendors" }

export async function createVendor(data: ApiRequestBody<"/vendors/", "post">) {
  return apiPost({ url: "/vendors/", data, refresh })
}

export async function updateVendor(id: string, data: ApiRequestBody<"/vendors/{id}", "patch">) {
  return apiPatch({ url: "/vendors/{id}", params: { id }, data, refresh })
}

export async function deleteVendor(id: string) {
  return apiDelete({ url: "/vendors/{id}", params: { id }, refresh })
}
