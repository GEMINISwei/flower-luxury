"use client"

import { useEffect, useState, type RefObject } from "react"
import type { ApiListMeta } from "@/shared/api/response"
import type { ProductInfo } from "../types"
import { appendProducts, canLoadMoreProducts } from "../capabilities"
import { loadProductPage } from "../actions"

export function useMobileProducts({ products, meta, filters, sentinel, errorFallback }: {
  products: ProductInfo[]; meta: ApiListMeta; filters: Record<string, string>;
  sentinel: RefObject<HTMLDivElement | null>; errorFallback: string
}) {
  const [page, setPage] = useState({ products, meta, errorMessage: "" })
  const [loading, setLoading] = useState(false)
  useEffect(() => {
    const target = sentinel.current
    if (!target || !page.meta.hasNext || !page.meta.nextCursor || page.errorMessage) return
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
            meta: result.meta, errorMessage: "" })
      } catch {
        if (active) setPage((current) => ({ ...current, errorMessage: errorFallback }))
      } finally {
        if (active) setLoading(false)
      }
    }
    const observer = new IntersectionObserver((entries) => {
      if (canLoadMoreProducts({ mobile: media.matches,
        intersecting: entries.some((entry) => entry.isIntersecting), loading: pending,
        errorMessage: page.errorMessage, ...page.meta })) void loadNext()
    }, { rootMargin: "0px", threshold: 1 })
    observer.observe(target)
    return () => { active = false; observer.disconnect() }
  }, [page.meta, page.errorMessage, filters, sentinel, errorFallback])
  return { ...page, loading, retry: () => setPage((current) => ({ ...current, errorMessage: "" })) }
}
