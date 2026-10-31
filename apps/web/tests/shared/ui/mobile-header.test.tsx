import { useState } from "react"
import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { expect, it, vi } from "vitest"
import { FormPageShell, Modal } from "@/shared/ui"

it("手機 Header 操作面板保留停用狀態並關閉後執行操作", async () => {
  const blocked = vi.fn()
  const reload = vi.fn()
  function Subject() {
    const [confirm, setConfirm] = useState(false)
    return <FormPageShell title="整理商品暫存" backHref="/product-drafts" backLabel="返回"
      actions={<button>桌面操作</button>}
      mobileRefresh={{ label: "重新載入資料", onClick: reload }}
      mobileActions={[
        { label: "儲存暫存", disabled: true, onClick: blocked },
        { label: "放棄暫存", color: "error", onClick: () => setConfirm(true) },
      ]}>
      <Modal title="確認放棄" open={confirm} onOpenChange={setConfirm}>確認內容</Modal>
    </FormPageShell>
  }
  render(<Subject />)
  await userEvent.click(screen.getByRole("button", { name: "重新載入資料", exact: true }))
  expect(reload).toHaveBeenCalledOnce()
  await userEvent.click(screen.getByRole("button", { name: "操作選單", exact: true }))
  const sheet = screen.getByRole("dialog", { name: "操作選單", exact: true })
  const save = within(sheet).getByRole("menuitem", { name: "儲存暫存", exact: true })
  expect(save).toBeDisabled()
  await userEvent.click(save)
  expect(blocked).not.toHaveBeenCalled()
  expect(sheet).toBeInTheDocument()
  await userEvent.click(within(sheet).getByRole("menuitem", { name: "放棄暫存", exact: true }))
  expect(screen.queryByRole("dialog", { name: "操作選單", exact: true })).not.toBeInTheDocument()
  const confirmation = screen.getByRole("dialog", { name: "確認放棄", exact: true })
  expect(confirmation).toHaveFocus()
})
