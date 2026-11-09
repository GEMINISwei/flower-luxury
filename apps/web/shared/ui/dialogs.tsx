"use client"

import type { FormEvent, ReactNode } from "react"
import { useEffect, useRef, useState } from "react"
import { createPortal } from "react-dom"
import { X } from "lucide-react"
import { useT } from "@/shared/i18n/context"
import { FOCUSABLE_SELECTOR, ICON_SIZE } from "./internals"
import styles from "./styles/primitives.module.css"
import { uiMessages } from "./i18n"
import { Button } from "./primitives"

type ModalProps = {
  title?: string
  open: boolean
  children?: ReactNode
  width?: number
  onOpenChange?: (open: boolean) => void
}

export function Modal({ open, ...props }: ModalProps) {
  return open ? <OpenModal {...props} /> : null
}

function OpenModal({ title, children, width, onOpenChange }: Omit<ModalProps, "open">) {
  const t = useT(uiMessages)
  const onOpenChangeRef = useRef(onOpenChange)
  const dialogRef = useRef<HTMLElement>(null)
  const initialFocus = useRef<HTMLElement>(null)
  // 在子欄位掛載並執行 autoFocus 之前記住觸發元素, 每次開啟都重新記錄。
  const [previousFocus] = useState(() => typeof document !== "undefined"
    && document.activeElement instanceof HTMLElement ? document.activeElement : null)

  useEffect(() => { onOpenChangeRef.current = onOpenChange }, [onOpenChange])
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.defaultPrevented) return
      if (event.key === "Escape") onOpenChangeRef.current?.(false)
      if (event.key === "Tab" && dialogRef.current) keepTabInside(dialogRef.current, event)
    }
    document.addEventListener("keydown", handleKeyDown)
    return () => document.removeEventListener("keydown", handleKeyDown)
  }, [])
  useEffect(() => {
    const node = dialogRef.current
    if (node) {
      const active = document.activeElement
      if (active instanceof HTMLElement && node.contains(active)) initialFocus.current = active
      else {
        // Strict Mode 會重跑 effect; 清理還原焦點後, 再回到第一次選到的欄位。
        const target = initialFocus.current ?? node.querySelector<HTMLElement>("[autofocus]") ?? node
        target.focus({ preventScroll: true })
      }
    }
    return () => {
      if (previousFocus?.isConnected) previousFocus.focus({ preventScroll: true })
    }
  }, [previousFocus])

  // 外層的 transform, filter 或 backdrop-filter 會限制 fixed 遮罩範圍, 因此直接掛到 body.
  // 對話框由使用者操作後開啟, 不在 server 端渲染.
  return createPortal(
    <div className={styles.overlay} role="presentation" onMouseDown={() => onOpenChange?.(false)}>
      <section
        ref={dialogRef}
        tabIndex={-1}
        className={styles.modal}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        style={{ width: width ? `min(100%, ${width}px)` : undefined }}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className={styles.modalHeader}>
          <h2 className={styles.modalTitle}>{title}</h2>
          <button type="button" className={styles.modalClose} aria-label={t("close")} onClick={() => onOpenChange?.(false)}>
            <X size={ICON_SIZE.sm} aria-hidden="true" />
          </button>
        </div>
        <div className={styles.modalBody}>{children}</div>
      </section>
    </div>,
    document.body,
  )
}

function keepTabInside(container: HTMLElement, event: KeyboardEvent) {
  const elements = [...container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)]
    .filter((element) => element.tabIndex >= 0 && !element.closest("[hidden], [inert]"))
  const first = elements[0]
  const last = elements.at(-1)
  if (!first || !last) return
  const active = document.activeElement
  const outside = active === container || !container.contains(active)
  if (event.shiftKey && (outside || active === first)) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && (outside || active === last)) {
    event.preventDefault()
    first.focus()
  }
}

type FormDialogProps = {
  title: string
  open: boolean
  isPending: boolean
  submitText: string
  pendingText?: string
  onClose: () => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
  children: ReactNode
}

export function FormDialog({
  title,
  open,
  isPending,
  submitText,
  pendingText,
  onClose,
  onSubmit,
  children,
}: FormDialogProps) {
  const t = useT(uiMessages)
  return (
    <Modal title={title} open={open} onOpenChange={(next) => { if (!next) onClose() }}>
      <form className={styles.dialogForm} onSubmit={onSubmit} noValidate>
        {children}
        <div className={styles.dialogFormActions}>
          <Button variant="outlined" disabled={isPending} onClick={onClose}>{t("cancel")}</Button>
          <Button type="submit" disabled={isPending}>{isPending ? pendingText ?? t("pending") : submitText}</Button>
        </div>
      </form>
    </Modal>
  )
}
