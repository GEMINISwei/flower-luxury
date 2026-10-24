import { useRef } from "react"
import { act, renderHook } from "@testing-library/react"
import { afterEach, beforeEach, expect, it, vi } from "vitest"
import { useMobileProducts } from "@/modules/products/ui/useMobileProducts"
import type { ProductInfo } from "@/modules/products/types"

const loadProductPage = vi.hoisted(() => vi.fn())
vi.mock("@/modules/products/actions", () => ({ loadProductPage }))

const first: ProductInfo = { id: "one", name: "Bag", brand_id: "brand", brand: "Brand",
  category: "包包", sku: "SKU-1", cost_price: 100, year: 2024, status: "not_acquired",
  created_by: "user", created_at: "2026-10-22T00:00:00Z" }
const meta = { hasNext: true, nextCursor: "next", hasPrevious: false,
  prevCursor: null, totalCount: 2 }
const filters = { keyword: "bag", status: "not_acquired" }
let mobile = true
let callbacks: IntersectionObserverCallback[] = []
const disconnect = vi.fn()
const observe = vi.fn()

beforeEach(() => {
  vi.clearAllMocks()
  callbacks = []
  mobile = true
  vi.stubGlobal("matchMedia", () => ({ get matches() { return mobile } }))
  vi.stubGlobal("IntersectionObserver", class {
    constructor(callback: IntersectionObserverCallback, options: IntersectionObserverInit) {
      callbacks.push(callback)
      expect(options.rootMargin ?? "0px").toBe("0px")
    }
    observe = observe
    disconnect = disconnect
  })
})
afterEach(() => vi.unstubAllGlobals())

function setup() {
  return renderHook(() => {
    const sentinel = useRef(document.createElement("div"))
    return useMobileProducts({ products: [first], meta, filters, sentinel,
      errorFallback: "Unable to load" })
  })
}

async function intersect(visible = true) {
  await act(async () => {
    callbacks.at(-1)?.([{ isIntersecting: visible }] as IntersectionObserverEntry[],
      {} as IntersectionObserver)
  })
}

it("手機到達底部才載入並保留篩選與原商品，最後一批停止續載", async () => {
  loadProductPage.mockResolvedValue({ items: [{ ...first, id: "two" }],
    meta: { ...meta, hasNext: false, nextCursor: null }, errorMessage: "" })
  const { result } = setup()
  expect(loadProductPage).not.toHaveBeenCalled()
  await intersect(false)
  expect(loadProductPage).not.toHaveBeenCalled()
  mobile = false
  await intersect()
  expect(loadProductPage).not.toHaveBeenCalled()
  mobile = true
  await intersect()
  expect(loadProductPage).toHaveBeenCalledWith(filters, "next")
  expect(result.current.products.map((product) => product.id)).toEqual(["one", "two"])
  expect(result.current.meta.hasNext).toBe(false)
  await intersect()
  expect(loadProductPage).toHaveBeenCalledOnce()
})

it("載入中重複觸底只送出一次請求", async () => {
  let finish!: (value: unknown) => void
  loadProductPage.mockImplementation(() => new Promise((resolve) => { finish = resolve }))
  const { result } = setup()
  await intersect()
  expect(result.current.loading).toBe(true)
  await intersect()
  expect(loadProductPage).toHaveBeenCalledOnce()
  await act(async () => finish({ items: [], meta: { ...meta, hasNext: false }, errorMessage: "" }))
  expect(result.current.loading).toBe(false)
})

it("續載失敗保留原商品與游標，明確重試後才再次請求", async () => {
  loadProductPage.mockResolvedValue({ items: [], meta: { ...meta, nextCursor: null },
    errorMessage: "Failed" })
  const { result } = setup()
  await intersect()
  expect(result.current.products).toEqual([first])
  expect(result.current.meta.nextCursor).toBe("next")
  expect(result.current.errorMessage).toBe("Failed")
  await intersect()
  expect(loadProductPage).toHaveBeenCalledOnce()
  loadProductPage.mockResolvedValue({ items: [{ ...first, id: "two" }],
    meta: { ...meta, hasNext: false }, errorMessage: "" })
  act(() => result.current.retry())
  await intersect()
  expect(loadProductPage).toHaveBeenCalledTimes(2)
  expect(result.current.products).toHaveLength(2)
})

it("請求意外失敗顯示可重試訊息，不自動連續重送", async () => {
  loadProductPage.mockRejectedValue(new Error("network"))
  const { result } = setup()
  await intersect()
  expect(result.current.errorMessage).toBe("Unable to load")
  expect(result.current.loading).toBe(false)
  await intersect()
  expect(loadProductPage).toHaveBeenCalledOnce()
})

it("切換篩選離開列表後，舊請求不影響新的列表", async () => {
  let finish!: (value: unknown) => void
  loadProductPage.mockImplementation(() => new Promise((resolve) => { finish = resolve }))
  const previous = setup()
  await intersect()
  previous.unmount()
  const next = setup()
  await act(async () => finish({ items: [{ ...first, id: "stale" }], meta, errorMessage: "" }))
  expect(next.result.current.products).toEqual([first])
  expect(disconnect).toHaveBeenCalled()
})
