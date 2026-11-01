import { productListQuery } from "./capabilities"

type StorageAccess = Pick<Storage, "getItem" | "setItem"> | null
export type ProductReturnPoint = { id: string; href: string; count: number; offset: number }
const FILTER_KEY = "products.filters.v1"
const RETURN_KEY = "products.return.v1"

export function productStorage(kind: "localStorage" | "sessionStorage"): StorageAccess {
  try { return window[kind] } catch { return null }
}

function read(storage: StorageAccess, key: string): unknown {
  try { return JSON.parse(storage?.getItem(key) ?? "null") } catch { return null }
}

function write(storage: StorageAccess, key: string, value: unknown) {
  try { storage?.setItem(key, JSON.stringify(value)) } catch { /* 儲存不可用時仍允許瀏覽. */ }
}

export function readProductFilters(storage: StorageAccess): Record<string, string> | null {
  const value = read(storage, FILTER_KEY)
  if (!value || typeof value !== "object" || Array.isArray(value)) return null
  return orderedFilters(Object.fromEntries(Object.entries(value)
    .filter((entry): entry is [string, string] => typeof entry[1] === "string")))
}

export function saveProductFilters(storage: StorageAccess, filters: Record<string, string>) {
  write(storage, FILTER_KEY, orderedFilters(Object.fromEntries(Object.entries(filters)
    .map(([key, value]) => [key, value.trim()]))))
}

function orderedFilters(filters: Record<string, string>) {
  const allowed = productListQuery(filters)
  return Object.fromEntries(Object.entries(filters).filter(([key]) => Object.hasOwn(allowed, key)))
}

export function productListHref(params: URLSearchParams): string {
  const fields = new Set([...Object.keys(productListQuery(Object.fromEntries(params))),
    "cursor", "direction", "seq"])
  const query = new URLSearchParams([...params].filter(([key]) => fields.has(key))).toString()
  return query ? `/products?${query}` : "/products"
}

export function saveProductReturnPoint(storage: StorageAccess, point: ProductReturnPoint | null) {
  write(storage, RETURN_KEY, point)
}

export function readProductReturnPoint(storage: StorageAccess): ProductReturnPoint | null {
  const value = read(storage, RETURN_KEY)
  if (!value || typeof value !== "object") return null
  const point = value as ProductReturnPoint
  if (typeof point.id !== "string" || !point.id || typeof point.href !== "string") return null
  if (point.href !== "/products" && !point.href.startsWith("/products?")) return null
  if (point.href !== productListHref(new URLSearchParams(point.href.split("?")[1]))) return null
  return validPosition(point) ? point : null
}

function validPosition(point: ProductReturnPoint) {
  return Number.isSafeInteger(point.count) && point.count >= 1
    && typeof point.offset === "number" && Number.isFinite(point.offset)
}
