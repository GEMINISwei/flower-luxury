import { act, fireEvent, render, screen } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { AutocompleteInput, TextInput } from "@/shared/ui"

function setup(loadOptions: (keyword: string) => Promise<string[]>, value = "") {
  const onChange = vi.fn()
  const view = render(<AutocompleteInput label="型號" value={value} onChange={onChange}
    loadOptions={loadOptions} />)
  return { onChange, view, input: screen.getByRole("combobox", { name: "型號" }) }
}

async function settle(ms = 250) {
  await act(async () => { await vi.advanceTimersByTimeAsync(ms) })
}

describe("AutocompleteInput", () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  it("點進欄位時就列出常用值", async () => {
    const loadOptions = vi.fn().mockResolvedValue(["Classic 25", "Classic 30"])
    const { input } = setup(loadOptions)
    fireEvent.focus(input)
    await settle()
    expect(loadOptions).toHaveBeenCalledWith("")
    expect(screen.getAllByRole("option").map((option) => option.textContent))
      .toEqual(["Classic 25", "Classic 30"])
    expect(input).toHaveAttribute("aria-expanded", "true")
  })

  it("停止輸入一段時間後才查詢", async () => {
    const loadOptions = vi.fn().mockResolvedValue(["Classic 25"])
    const { view, input } = setup(loadOptions)
    fireEvent.focus(input)
    for (const value of ["c", "cl", "cla"]) {
      view.rerender(<AutocompleteInput label="型號" value={value} onChange={vi.fn()}
        loadOptions={loadOptions} />)
      await settle(100)
    }
    expect(loadOptions).not.toHaveBeenCalled()
    await settle()
    expect(loadOptions).toHaveBeenCalledTimes(1)
    expect(loadOptions).toHaveBeenCalledWith("cla")
  })

  it("只採用最後一次查詢的結果", async () => {
    let resolveOld: (values: string[]) => void = () => {}
    const loadOptions = vi.fn()
      .mockImplementationOnce(() => new Promise<string[]>((resolve) => { resolveOld = resolve }))
      .mockResolvedValueOnce(["新的結果"])
    const { view, input } = setup(loadOptions, "a")
    fireEvent.focus(input)
    await settle()
    view.rerender(<AutocompleteInput label="型號" value="ab" onChange={vi.fn()}
      loadOptions={loadOptions} />)
    await settle()
    await act(async () => { resolveOld(["舊的結果"]) })
    expect(screen.getAllByRole("option").map((option) => option.textContent)).toEqual(["新的結果"])
  })

  it("可用方向鍵與 Enter 選取，Esc 關閉清單", async () => {
    const { input, onChange } = setup(vi.fn().mockResolvedValue(["Black", "Blue"]))
    fireEvent.focus(input)
    await settle()
    fireEvent.keyDown(input, { key: "ArrowDown" })
    fireEvent.keyDown(input, { key: "ArrowDown" })
    expect(input).toHaveAttribute("aria-activedescendant",
      screen.getByRole("option", { name: "Blue" }).id)
    fireEvent.keyDown(input, { key: "Enter" })
    expect(onChange).toHaveBeenCalledWith("Blue")
    expect(screen.queryByRole("listbox")).toBeNull()
    fireEvent.keyDown(input, { key: "ArrowDown" })
    expect(screen.getByRole("listbox")).toBeInTheDocument()
    fireEvent.keyDown(input, { key: "Escape" })
    expect(screen.queryByRole("listbox")).toBeNull()
  })

  it("點選選項會填入欄位並收起清單", async () => {
    const { input, onChange } = setup(vi.fn().mockResolvedValue(["Black"]))
    fireEvent.focus(input)
    await settle()
    fireEvent.mouseDown(screen.getByRole("option", { name: "Black" }))
    expect(onChange).toHaveBeenCalledWith("Black")
    expect(screen.queryByRole("listbox")).toBeNull()
  })

  it("沒有符合的值時不顯示清單，仍可自由輸入", async () => {
    const { input, onChange } = setup(vi.fn().mockResolvedValue([]))
    fireEvent.focus(input)
    await settle()
    expect(screen.queryByRole("listbox")).toBeNull()
    fireEvent.change(input, { target: { value: "全新型號" } })
    expect(onChange).toHaveBeenCalledWith("全新型號")
  })

  it("查詢失敗時不顯示清單也不中斷輸入", async () => {
    const { input } = setup(vi.fn().mockRejectedValue(new Error("offline")))
    fireEvent.focus(input)
    await settle()
    expect(screen.queryByRole("listbox")).toBeNull()
    expect(input).not.toBeDisabled()
  })

  it("關閉瀏覽器自己的輸入紀錄與自動填入", () => {
    const { input } = setup(vi.fn().mockResolvedValue([]))
    expect(input).toHaveAttribute("autocomplete", "off")
    expect(input).toHaveAttribute("aria-autocomplete", "list")
    expect(input).not.toHaveAttribute("name")
  })
})

describe("TextInput 的瀏覽器建議", () => {
  it("指定 browserSuggestions={false} 時關閉瀏覽器自己的輸入紀錄與自動填入", () => {
    render(<TextInput label="年份" browserSuggestions={false} />)
    expect(screen.getByLabelText("年份")).toHaveAttribute("autocomplete", "off")
  })

  it("預設保留瀏覽器的建議，讓登入等表單照常自動填入", () => {
    render(<TextInput label="帳號" />)
    expect(screen.getByLabelText("帳號")).not.toHaveAttribute("autocomplete", "off")
  })
})
