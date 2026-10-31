"use server"
import { revalidatePath } from "next/cache"
import { redirect } from "next/navigation"
import { apiDelete, apiGet, apiPatch, apiPost } from "@/shared/api/request.server"
import type { DraftFields } from "./types"

const refresh = { path: "/product-drafts" }
export async function reloadDraft(id: string) {
  return apiGet({ url: "/product-drafts/{id}", params: { id } })
}
export async function saveDraft(id: string, version: number, fields: DraftFields) {
  return apiPatch({ url: "/product-drafts/{id}", params: { id }, data: { version, fields }, refresh })
}
export async function approveDraft(id: string, version: number) {
  const result = await apiPost({ url: "/product-drafts/{id}/approve", params: { id },
    data: { version } })
  if (result.status === "success") {
    revalidatePath("/product-drafts"); revalidatePath("/products")
    redirect(`/products/${result.data.product_id}`)
  }
  return result
}
export async function discardDraft(id: string, version: number) {
  const result = await apiDelete({ url: "/product-drafts/{id}", params: { id }, query: { version } })
  if (result.status === "success") { revalidatePath("/product-drafts"); redirect("/product-drafts") }
  return result
}
export async function setDraftMainPhoto(id: string, version: number, photo_id: string) {
  return apiPatch({ url: "/product-drafts/{id}/photos/main", params: { id },
    data: { version, photo_id } })
}
export async function deleteDraftPhoto(id: string, version: number, photo_id: string) {
  return apiDelete({ url: "/product-drafts/{id}/photos/{photo_id}", params: { id, photo_id },
    query: { version } })
}
