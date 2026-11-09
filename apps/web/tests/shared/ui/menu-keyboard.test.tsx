import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { expect, it, vi } from "vitest"
import { Menu } from "@/shared/ui"

it("Menu 聚焦可用項目且方向鍵跳過停用項目並循環", async () => {
  const remove = vi.fn()
  render(<Menu trigger="⋯" triggerLabel="操作" items={[
    { label: "匯出", disabled: true, onClick: vi.fn() },
    { label: "編輯", onClick: vi.fn() },
    { label: "移動", disabled: true, onClick: vi.fn() },
    { label: "刪除", onClick: remove },
  ]} />)
  await userEvent.click(screen.getByRole("button", { name: "操作" }))
  expect(screen.getByRole("menuitem", { name: "編輯" })).toHaveFocus()
  await userEvent.keyboard("{ArrowDown}")
  expect(screen.getByRole("menuitem", { name: "刪除" })).toHaveFocus()
  await userEvent.keyboard("{ArrowDown}")
  expect(screen.getByRole("menuitem", { name: "編輯" })).toHaveFocus()
  await userEvent.keyboard("{ArrowUp}{Enter}")
  expect(remove).toHaveBeenCalledOnce()
  expect(screen.queryByRole("menu")).not.toBeInTheDocument()
  expect(screen.getByRole("button", { name: "操作" })).toHaveFocus()
})

it("Menu 按 Escape 關閉並還原觸發按鈕", async () => {
  render(<Menu trigger="⋯" triggerLabel="操作" items={[{ label: "編輯", onClick: vi.fn() }]} />)
  await userEvent.click(screen.getByRole("button", { name: "操作" }))
  await userEvent.keyboard("{Escape}")
  expect(screen.queryByRole("menu")).not.toBeInTheDocument()
  expect(screen.getByRole("button", { name: "操作" })).toHaveFocus()
})

it("Menu 全部項目停用時保留焦點且 Escape 仍可關閉", async () => {
  render(<Menu trigger="⋯" triggerLabel="操作"
    items={[{ label: "編輯", disabled: true, onClick: vi.fn() }]} />)
  const trigger = screen.getByRole("button", { name: "操作" })
  await userEvent.click(trigger)
  await userEvent.keyboard("{ArrowDown}")
  expect(trigger).toHaveFocus()
  await userEvent.keyboard("{Escape}")
  expect(screen.queryByRole("menu")).not.toBeInTheDocument()
})
