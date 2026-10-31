import { useState } from "react"
import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { expect, it, vi } from "vitest"
import { Check, Plus, RefreshCw, Save, Trash2 } from "lucide-react"
import { FormPageShell, Modal, PageHeader } from "@/shared/ui"

it("頁首三項操作直接顯示且四項操作保留重整與主要功能", async () => {
  const actions = [
    { label: "重整", icon: <RefreshCw />, refresh: true, onClick: vi.fn() },
    { label: "儲存", icon: <Save />, onClick: vi.fn() },
    { label: "建檔", icon: <Check />, primary: true, onClick: vi.fn() },
  ]
  const { rerender } = render(<PageHeader title="資料" actions={actions} />)
  expect(screen.getAllByRole("button")).toHaveLength(3)
  expect(screen.queryByRole("button", { name: "操作選單" })).not.toBeInTheDocument()
  rerender(<PageHeader title="資料" actions={[
    ...actions, { label: "刪除", icon: <Trash2 />, onClick: vi.fn() },
  ]} />)
  expect(screen.getAllByRole("button")).toHaveLength(3)
  expect(screen.getByRole("button", { name: "重整" })).toBeVisible()
  expect(screen.getByRole("button", { name: "建檔" })).toBeVisible()
  await userEvent.click(screen.getByRole("button", { name: "操作選單" }))
  expect(screen.getAllByRole("menuitem").map((item) => item.textContent)).toEqual(["儲存", "刪除"])
})

it("頁首圖示保留名稱停用狀態與表單送出", async () => {
  const submit = vi.fn()
  render(<>
    <PageHeader title="設定" actions={[
      { label: "新增", icon: <Plus />, disabled: true, onClick: vi.fn() },
      { label: "儲存設定", icon: <Save />, primary: true, type: "submit", form: "settings" },
    ]} />
    <form id="settings" onSubmit={(event) => { event.preventDefault(); submit() }} />
  </>)
  for (const button of screen.getAllByRole("button")) {
    expect(button.textContent).toBe("")
    expect(button).toHaveAttribute("title", button.getAttribute("aria-label"))
  }
  expect(screen.getByRole("button", { name: "新增" })).toBeDisabled()
  await userEvent.click(screen.getByRole("button", { name: "儲存設定" }))
  expect(submit).toHaveBeenCalledOnce()
})

it("手機 Header 操作面板保留停用狀態並關閉後執行操作", async () => {
  const blocked = vi.fn()
  const reload = vi.fn()
  function Subject() {
    const [confirm, setConfirm] = useState(false)
    return <FormPageShell title="整理商品暫存" backHref="/product-drafts" backLabel="返回"
      actions={[
        { label: "重新載入資料", icon: <RefreshCw />, refresh: true, onClick: reload },
        { label: "建檔", icon: <Check />, primary: true, onClick: vi.fn() },
        { label: "儲存暫存", icon: <Save />, disabled: true, onClick: blocked },
        { label: "放棄暫存", icon: <Trash2 />, color: "error", onClick: () => setConfirm(true) },
      ]}>
      <Modal title="確認放棄" open={confirm} onOpenChange={setConfirm}>確認內容</Modal>
    </FormPageShell>
  }
  render(<Subject />)
  await userEvent.click(screen.getByRole("button", { name: "重新載入資料" }))
  expect(reload).toHaveBeenCalledOnce()
  await userEvent.click(screen.getByRole("button", { name: "操作選單" }))
  const sheet = screen.getByRole("dialog", { name: "操作選單" })
  const save = within(sheet).getByRole("menuitem", { name: "儲存暫存" })
  expect(save).toBeDisabled()
  await userEvent.click(save)
  expect(blocked).not.toHaveBeenCalled()
  expect(sheet).toBeInTheDocument()
  await userEvent.click(within(sheet).getByRole("menuitem", { name: "放棄暫存" }))
  expect(screen.queryByRole("dialog", { name: "操作選單" })).not.toBeInTheDocument()
  const confirmation = screen.getByRole("dialog", { name: "確認放棄" })
  expect(confirmation).toHaveFocus()
})
