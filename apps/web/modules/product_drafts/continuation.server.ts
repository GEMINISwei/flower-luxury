import "server-only"
import { apiGet } from "@/shared/api/request.server"
import { draftQueueHref } from "./capabilities"

export async function reviewContinuation(source: string | undefined, created: string,
  unavailableId?: string) {
  const next = await apiGet({ url: "/product-drafts/next-review",
    query: source ? { source_key: source } : {} })
  const target = next.status === "success" && next.data.id !== unavailableId
    ? next.data.id ?? undefined : undefined
  const href = draftQueueHref(target, source, created)
  return next.status === "success" && !next.data.id ? `${href}&completed=1` : href
}
