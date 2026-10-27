"use server"

import { apiDelete, apiPatch, apiPost } from "@/shared/api/request.server"

export async function createBrand(name: string) {
  return apiPost({ url: "/brands/", data: { name }, refresh: { path: "/brands" } })
}
export async function updateBrand(id: string, name: string, is_active: boolean) {
  return apiPatch({ url: "/brands/{id}", params: { id }, data: { name, is_active },
    refresh: { path: "/brands" } })
}
export async function deleteBrand(id: string) {
  return apiDelete({ url: "/brands/{id}", params: { id }, refresh: { path: "/brands" } })
}
