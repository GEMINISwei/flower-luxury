"use server"
import { revalidatePath } from "next/cache"
import { redirect } from "next/navigation"
import { apiDelete, apiGet, apiPatch, apiPost } from "@/shared/api/request.server"
import type { DraftFields } from "./types"
import { reviewContinuation } from "./continuation.server"

const refresh = { path: "/product-drafts" }
export async function selectDraftSale(id: string, version: number, quote_id: string | null) {
  return apiPatch({ url: "/product-drafts/{id}/sale-selection", params: { id },
    data: { version, quote_id } })
}
export async function reloadDraft(id: string) {
  return apiGet({ url: "/product-drafts/{id}", params: { id } })
}
export async function saveDraft(id: string, version: number, fields: DraftFields,
  manual_fields: (keyof DraftFields)[] = []) {
  return apiPatch({ url: "/product-drafts/{id}", params: { id },
    data: { version, fields, manual_fields }, refresh })
}
export async function approveDraft(id: string, version: number, source?: string) {
  const result = await apiPost({ url: "/product-drafts/{id}/approve", params: { id },
    data: { version } })
  if (result.status === "success") {
    revalidatePath("/product-drafts"); revalidatePath("/products")
    redirect(await reviewContinuation(source, result.data.product_id))
  }
  return result
}

export async function resolveDraftIssue(id: string,
  data: { action: "attach" | "discard"; target_draft_id?: string; target_version?: number }) {
  return apiPost({ url: "/product-drafts/issues/{id}/resolve", params: { id }, data,
    refresh })
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
export async function savePrefillSettings(supplement: string, revision: number) {
  return apiPatch({ url: "/draft-prefill/settings", data: { supplement, revision },
    refresh: { path: "/admin/draft-prefill" } })
}
export async function previewPrefill(text: string, supplement: string) {
  return apiPost({ url: "/draft-prefill/preview", data: { text, supplement } })
}
export async function saveDraftQuote(id: string, version: number,
  data: { vendor_id: string; original_amount: string; exchange_rate: string; note: string | null },
  quote_id?: string) {
  return quote_id
    ? apiPatch({ url: "/product-drafts/{id}/quotes/{quote_id}", params: { id, quote_id },
      data: { version, ...data } })
    : apiPost({ url: "/product-drafts/{id}/quotes", params: { id }, data: { version, ...data } })
}
export async function deleteDraftQuote(id: string, version: number, quote_id: string) {
  return apiDelete({ url: "/product-drafts/{id}/quotes/{quote_id}", params: { id, quote_id },
    query: { version } })
}
