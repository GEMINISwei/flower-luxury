"use client"

import { useEffect, useState, type RefObject } from "react"
import type { ApiListMeta } from "@/shared/api/response"
import type { ProductInfo } from "../types"
import { appendProducts, canLoadMoreProducts } from "../capabilities"
import { loadProductPage } from "../actions"

export function useMobileProducts({
  products, meta, filters, sentinel, errorFallback, restore, enabled = true,
}: {
  products: ProductInfo[]; meta: ApiListMeta; filters: Record<string, string>;
  sentinel: RefObject<HTMLDivElement | null>; errorFallback: string
  restore?: { id: string; count: number } | null
  enabled?: boolean
}) {
  const [page, setPage] = useState({ products, meta, errorMessage: "" })
  const [loading, setLoading] = useState(false)
  const restoring = Boolean(restore && page.products.length < restore.count
    && !page.products.some((product) => product.id === restore.id) && page.meta.hasNext
    && page.meta.nextCursor)
  useEffect(() => {
    const target = sentinel.current
    if (!enabled || !target || !page.meta.hasNext || !page.meta.nextCursor
        || page.errorMessage) return
    const media = window.matchMedia("(max-width: 720px)")
    let active = true
    let pending = false
    async function loadNext() {
      pending = true
      setLoading(true)
      try {
        const result = await loadProductPage(filters, page.meta.nextCursor!)
        if (!active) return
        setPage((current) => result.errorMessage
          ? { ...current, errorMessage: result.errorMessage }
          : { products: appendProducts(current.products, result.items),
            meta: result.meta.nextCursor === current.meta.nextCursor
              ? { ...result.meta, hasNext: false } : result.meta, errorMessage: "" })
      } catch {
        if (active) setPage((current) => ({ ...current, errorMessage: errorFallback }))
      } finally {
        if (active) setLoading(false)
      }
    }
    if (restoring && media.matches) {
      void loadNext()
      return () => { active = false }
    }
    const observer = new IntersectionObserver((entries) => {
      if (canLoadMoreProducts({ mobile: media.matches,
        intersecting: entries.some((entry) => entry.isIntersecting), loading: pending,
        errorMessage: page.errorMessage, ...page.meta })) void loadNext()
    }, { rootMargin: "0px", threshold: 1 })
    observer.observe(target)
    return () => { active = false; observer.disconnect() }
  }, [page.meta, page.errorMessage, filters, sentinel, errorFallback, restoring, enabled])
  return { ...page, loading, restoring,
    retry: () => setPage((current) => ({ ...current, errorMessage: "" })) }
}
