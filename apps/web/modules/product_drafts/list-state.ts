type StorageAccess = Pick<Storage, "getItem" | "setItem"> | null
type DraftReturnPoint = { id: string; href: string }
const RETURN_KEY = "product-drafts.return.v1"
const LIST_PATH = "/product-drafts"
// created、completed 是審核完成的一次性提示, 返回時不該再出現一次.
const LIST_FIELDS = new Set(["source_key", "cursor", "direction", "seq"])

export function draftStorage(): StorageAccess {
  try { return window.sessionStorage } catch { return null }
}

export function draftListHref(params: URLSearchParams): string {
  const query = new URLSearchParams([...params].filter(([key]) => LIST_FIELDS.has(key))).toString()
  return query ? `${LIST_PATH}?${query}` : LIST_PATH
}

export function saveDraftReturnPoint(storage: StorageAccess, point: DraftReturnPoint) {
  try { storage?.setItem(RETURN_KEY, JSON.stringify(point)) } catch { /* 儲存不可用時仍允許瀏覽. */ }
}

function readReturnPoint(storage: StorageAccess): DraftReturnPoint | null {
  try {
    const point = JSON.parse(storage?.getItem(RETURN_KEY) ?? "null") as DraftReturnPoint | null
    return typeof point?.id === "string" && typeof point.href === "string" ? point : null
  } catch { return null }
}

export function draftReturnHref(storage: StorageAccess, id: string, fallback: string): string {
  const point = readReturnPoint(storage)
  if (point?.id !== id) return fallback
  const [path, query] = point.href.split("?")
  const valid = path === LIST_PATH && point.href === draftListHref(new URLSearchParams(query))
  return valid ? point.href : fallback
}
