import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { expect, it, vi } from "vitest"
import { BottomSheet } from "@/shared/ui"

it("底部彈窗可關閉並還原焦點", async () => {
  const user = userEvent.setup()
  const onOpenChange = vi.fn()
  const trigger = document.createElement("button")
  document.body.appendChild(trigger)
  trigger.focus()
  const { rerender, unmount } = render(<BottomSheet open label="更多" header={<span>Alex</span>}
    onOpenChange={onOpenChange}><a href="/settings">設定</a></BottomSheet>)
  const dialog = screen.getByRole("dialog", { name: "更多" })
  expect(within(dialog).getByText("Alex")).toBeInTheDocument()
  expect(dialog.contains(document.activeElement)).toBe(true)
  await user.click(screen.getByRole("button", { name: "關閉" }))
  expect(onOpenChange).toHaveBeenLastCalledWith(false)
  await user.keyboard("{Escape}")
  expect(onOpenChange).toHaveBeenCalledTimes(2)
  await user.click(dialog.parentElement!)
  expect(onOpenChange).toHaveBeenCalledTimes(3)
  rerender(<BottomSheet open={false} label="更多" header="Alex"
    onOpenChange={onOpenChange}>內容</BottomSheet>)
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
  expect(trigger).toHaveFocus()
  unmount(); trigger.remove()
})

it("底部彈窗限制焦點並鎖定背景捲動", async () => {
  const user = userEvent.setup()
  document.body.style.overflow = "auto"
  const { unmount } = render(<BottomSheet open label="更多" header="Alex"
    onOpenChange={() => {}}><button>設定</button><button>登出</button></BottomSheet>)
  expect(document.body.style.overflow).toBe("hidden")
  screen.getByRole("button", { name: "登出" }).focus()
  await user.tab()
  expect(screen.getByRole("button", { name: "關閉" })).toHaveFocus()
  await user.tab({ shift: true })
  expect(screen.getByRole("button", { name: "登出" })).toHaveFocus()
  unmount()
  expect(document.body.style.overflow).toBe("auto")
  document.body.style.overflow = ""
})
