import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { expect, it, vi } from "vitest"
import { Button, Modal } from "@/shared/ui"

it("Modal 頁首操作位於關閉鍵之前並保留名稱", () => {
  render(<Modal title="附件" open headerActions={<Button>上傳</Button>}>內容</Modal>)
  const dialog = screen.getByRole("dialog", { name: "附件" })
  const buttons = within(dialog).getAllByRole("button")
  expect(buttons.map((button) => button.getAttribute("aria-label") ?? button.textContent))
    .toEqual(["上傳", "關閉"])
  expect(buttons[0].parentElement).toBe(buttons[1].parentElement)
})

it("操作 Modal 頁首按鈕不會誤關閉視窗", async () => {
  const onOpenChange = vi.fn()
  const upload = vi.fn()
  render(<Modal title="附件" open onOpenChange={onOpenChange}
    headerActions={<Button onClick={upload}>上傳</Button>}>內容</Modal>)
  await userEvent.click(screen.getByRole("button", { name: "上傳" }))
  expect(upload).toHaveBeenCalledOnce()
  expect(onOpenChange).not.toHaveBeenCalled()
  await userEvent.click(screen.getByRole("button", { name: "關閉" }))
  expect(onOpenChange).toHaveBeenCalledWith(false)
})
