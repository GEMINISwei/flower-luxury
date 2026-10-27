import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { expect, it, vi } from "vitest"
import { ConfirmDialog } from "@/shared/ui"
import { LocaleProvider } from "@/shared/i18n/context"

it("取消與關閉不執行操作，只有明確確認才執行", async () => {
  const onConfirm = vi.fn()
  const onClose = vi.fn()
  render(<ConfirmDialog title="確認操作" open isPending={false} confirmText="確認刪除"
    onClose={onClose} onConfirm={onConfirm}>此操作無法還原</ConfirmDialog>)
  expect(screen.getByRole("dialog", { name: "確認操作" })).toHaveTextContent("此操作無法還原")
  await userEvent.click(screen.getByRole("button", { name: "取消" }))
  await userEvent.click(screen.getByRole("button", { name: "關閉" }))
  await userEvent.keyboard("{Escape}")
  expect(onClose).toHaveBeenCalledTimes(3)
  expect(onConfirm).not.toHaveBeenCalled()
  await userEvent.click(screen.getByRole("button", { name: "確認刪除" }))
  expect(onConfirm).toHaveBeenCalledTimes(1)
})

it("處理中禁止重複確認與關閉", async () => {
  const onConfirm = vi.fn()
  const onClose = vi.fn()
  render(<ConfirmDialog title="確認操作" open isPending confirmText="確認"
    onClose={onClose} onConfirm={onConfirm}>等待伺服器回應</ConfirmDialog>)
  expect(screen.getByRole("button", { name: "處理中" })).toBeDisabled()
  expect(screen.getByRole("button", { name: "取消" })).toBeDisabled()
  await userEvent.click(screen.getByRole("button", { name: "處理中" }))
  await userEvent.click(screen.getByRole("button", { name: "關閉" }))
  await userEvent.keyboard("{Escape}")
  expect(onClose).not.toHaveBeenCalled()
  expect(onConfirm).not.toHaveBeenCalled()
})

it("確認視窗的按鈕支援英文", () => {
  render(<LocaleProvider locale="en"><ConfirmDialog title="Confirm action" open
    isPending={false} confirmText="Delete" onClose={vi.fn()} onConfirm={vi.fn()}>
    This action cannot be undone
  </ConfirmDialog></LocaleProvider>)
  expect(screen.getByRole("button", { name: "Cancel" })).toBeInTheDocument()
  expect(screen.getByRole("button", { name: "Delete" })).toBeInTheDocument()
})
