import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { useState } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { Button, FormDialog, Modal, SelectInput, TextInput } from "@/shared/ui"

it("送出時不跑瀏覽器的原生驗證", async () => {
  const onSubmit = vi.fn((event: React.FormEvent) => event.preventDefault())
  render(<FormDialog title="新增" open isPending={false} submitText="送出"
    onClose={() => {}} onSubmit={onSubmit}><TextInput label="名稱" required /></FormDialog>)

  await userEvent.click(screen.getByRole("button", { name: "送出" }))

  expect(onSubmit).toHaveBeenCalledOnce()
})

it("Tab 與 Shift+Tab 不會跑到背景", async () => {
  render(<><Button>背景</Button><Modal title="測試" open>
    <TextInput label="名稱" /><Button>確定</Button>
  </Modal></>)
  const last = screen.getByRole("button", { name: "確定" })
  const first = screen.getByRole("button", { name: "關閉" })
  last.focus()

  await userEvent.tab()
  expect(first).toHaveFocus()
  await userEvent.tab({ shift: true })
  expect(last).toHaveFocus()
})

it("含自動聚焦欄位的對話框關閉後還原焦點", async () => {
  function Harness() {
    const [open, setOpen] = useState(false)
    return <><Button onClick={() => setOpen(true)}>開啟</Button>
      <Modal title="測試" open={open} onOpenChange={setOpen}>
        <TextInput label="名稱" autoFocus />
      </Modal></>
  }
  render(<Harness />)
  const trigger = screen.getByRole("button", { name: "開啟" })
  for (let count = 0; count < 2; count++) {
    await userEvent.click(trigger)
    expect(screen.getByLabelText("名稱")).toHaveFocus()
    await userEvent.keyboard("{Escape}")
    expect(trigger).toHaveFocus()
  }
})

describe("觸控裝置上的自動聚焦", () => {
  afterEach(() => vi.unstubAllGlobals())

  it("觸控裝置不自動聚焦輸入與選擇欄位", () => {
    vi.stubGlobal("matchMedia", (query: string) => ({ matches: query.includes("coarse") }))
    const { unmount } = render(<><TextInput label="名稱" autoFocus />
      <SelectInput label="狀態" options={[{ value: "a", label: "A" }]} autoFocus /></>)
    expect(screen.getByLabelText("名稱")).not.toHaveFocus()
    expect(screen.getByLabelText("狀態")).not.toHaveFocus()
    unmount()

    vi.stubGlobal("matchMedia", () => ({ matches: false }))
    const first = render(<TextInput label="名稱" autoFocus />)
    expect(screen.getByLabelText("名稱")).toHaveFocus()
    first.unmount()
    render(<SelectInput label="狀態" options={[{ value: "a", label: "A" }]} autoFocus />)
    expect(screen.getByLabelText("狀態")).toHaveFocus()
  })
})
