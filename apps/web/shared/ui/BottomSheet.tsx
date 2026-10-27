"use client"

import { useEffect, useRef, type ReactNode } from "react"
import { createPortal } from "react-dom"
import { X } from "lucide-react"
import { useT } from "@/shared/i18n/context"
import { ICON_SIZE } from "./internals"
import { uiMessages } from "./i18n"
import styles from "./styles/bottom-sheet.module.css"

const FOCUSABLE = "a[href], button:not(:disabled), input:not(:disabled), "
  + "select:not(:disabled), textarea:not(:disabled), [tabindex='0']"

type BottomSheetProps = {
  open: boolean
  label: string
  header: ReactNode
  children: ReactNode
  onOpenChange: (open: boolean) => void
}

export function BottomSheet({ open, label, header, children, onOpenChange }: BottomSheetProps) {
  const t = useT(uiMessages)
  const panel = useRef<HTMLElement>(null)
  const change = useRef(onOpenChange)
  useEffect(() => { change.current = onOpenChange }, [onOpenChange])
  useEffect(() => {
    if (!open) return
    const previousFocus = document.activeElement
    const overflow = document.body.style.overflow
    document.body.style.overflow = "hidden"
    const node = panel.current
    const targets = () => Array.from(node?.querySelectorAll<HTMLElement>(FOCUSABLE) ?? [])
      .filter((element) => !element.closest("[hidden], [inert]"))
    targets()[0]?.focus({ preventScroll: true })
    function keydown(event: KeyboardEvent) {
      if (event.key === "Escape") { event.preventDefault(); change.current(false); return }
      if (event.key !== "Tab") return
      const elements = targets()
      const first = elements[0]
      const last = elements.at(-1)
      const outside = !node?.contains(document.activeElement)
      if (event.shiftKey && (outside || document.activeElement === first)) {
        event.preventDefault(); last?.focus()
      } else if (!event.shiftKey && (outside || document.activeElement === last)) {
        event.preventDefault(); first?.focus()
      }
    }
    document.addEventListener("keydown", keydown)
    return () => {
      document.removeEventListener("keydown", keydown)
      document.body.style.overflow = overflow
      if (previousFocus instanceof HTMLElement && previousFocus.isConnected) {
        previousFocus.focus({ preventScroll: true })
      }
    }
  }, [open])
  if (!open) return null
  return createPortal(
    <div className={styles.overlay} role="presentation" onMouseDown={() => onOpenChange(false)}>
      <section ref={panel} role="dialog" aria-modal="true" aria-label={label}
        className={styles.sheet} onMouseDown={(event) => event.stopPropagation()}>
        <div className={styles.handle} aria-hidden />
        <header className={styles.header}>
          <div className={styles.identity}>{header}</div>
          <button type="button" className={styles.close} aria-label={t("close")}
            onClick={() => onOpenChange(false)}><X size={ICON_SIZE.sm} aria-hidden /></button>
        </header>
        <div className={styles.body}>{children}</div>
      </section>
    </div>, document.body,
  )
}
