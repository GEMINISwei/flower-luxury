"use client"

import { useEffect, useState } from "react"
import { draftReturnHref, draftStorage } from "../list-state"

export function useDraftReturnHref(id: string, fallback: string) {
  const [href, setHref] = useState(fallback)
  useEffect(() => {
    const target = draftReturnHref(draftStorage(), id, fallback)
    queueMicrotask(() => setHref(target))
  }, [id, fallback])
  return href
}
