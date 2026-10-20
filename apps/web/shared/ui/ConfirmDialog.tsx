"use client"

import type { ReactNode } from "react"
import { FormDialog } from "./dialogs"

type ConfirmDialogProps = {
  title: string
  open: boolean
  isPending: boolean
  confirmText: string
  children: ReactNode
  onClose: () => void
  onConfirm: () => void
}

export function ConfirmDialog({
  title, open, isPending, confirmText, children, onClose, onConfirm,
}: ConfirmDialogProps) {
  return <FormDialog title={title} open={open} isPending={isPending} submitText={confirmText}
    onClose={() => { if (!isPending) onClose() }}
    onSubmit={(event) => {
      event.preventDefault()
      if (!isPending) onConfirm()
    }}>
    {children}
  </FormDialog>
}
