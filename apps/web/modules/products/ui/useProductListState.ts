"use client"

import { useEffect, useRef, useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { productListHref, productStorage, readProductFilters, saveProductFilters,
  readProductReturnPoint, saveProductReturnPoint, type ProductReturnPoint } from "../list-state"

export function useProductListState(filters: Record<string, string>) {
  const router = useRouter()
  const params = useSearchParams()
  const href = productListHref(new URLSearchParams(params.toString()))
  const [state, setState] = useState<{ ready: boolean; point: ProductReturnPoint | null }>(
    { ready: false, point: null })
  useEffect(() => {
    const storage = productStorage("localStorage")
    const saved = readProductFilters(storage)
    const explicit = Object.keys(filters).some((key) => params.has(key))
    if (!explicit && saved && Object.keys(saved).length) {
      router.replace(productListHref(new URLSearchParams(saved)), { scroll: false })
      return
    }
    saveProductFilters(storage, Object.fromEntries(params))
    const point = readProductReturnPoint(productStorage("sessionStorage"))
    queueMicrotask(() => setState({ ready: true, point: point?.href === href ? point : null }))
  }, [filters, href, router, params])

  function applyFilters(values: Record<string, string>) {
    saveProductFilters(productStorage("localStorage"), values)
    saveProductReturnPoint(productStorage("sessionStorage"), null)
  }
  function remember(id: string, count: number) {
    const row = document.getElementById(`product-${id}`)
    saveProductReturnPoint(productStorage("sessionStorage"), {
      id, count, href, offset: row?.getBoundingClientRect().top ?? 0,
    })
  }
  return { ...state, applyFilters, remember }
}

export function useProductPosition(point: ProductReturnPoint | null, restoring: boolean) {
  const restored = useRef<ProductReturnPoint | null>(null)
  useEffect(() => {
    if (!point || restoring || restored.current === point) return
    const frame = requestAnimationFrame(() => {
      const rows = document.querySelectorAll<HTMLElement>('[id^="product-"]')
      const row = document.getElementById(`product-${point.id}`)
        ?? rows[Math.min(point.count, rows.length) - 1]
      if (!row) return
      const delta = row.getBoundingClientRect().top - point.offset
      if (window.matchMedia("(max-width: 720px)").matches) window.scrollBy(0, delta)
      else {
        const main = row.closest("main")
        if (main) main.scrollTop += delta
      }
      restored.current = point
    })
    return () => cancelAnimationFrame(frame)
  }, [point, restoring])
}

export function useProductReturnHref(id: string) {
  const [href, setHref] = useState("/products")
  useEffect(() => {
    const point = readProductReturnPoint(productStorage("sessionStorage"))
    if (point?.id === id) queueMicrotask(() => setHref(point.href))
  }, [id])
  return href
}
