/**
 * 頁首的重新整理要等同「重新進入這個畫面」: 回到第一頁, 而且等新資料畫好之後才停在頂端。
 * 只在按下的瞬間捲回頂端, 資料回來重繪時位置還會被改掉。
 */

import { act, fireEvent, render, renderHook, screen } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { PageHeader, useListRefresh } from "@/shared/ui"

const push = vi.fn()
const refresh = vi.fn()
let search = ""

vi.mock("next/navigation", () => ({
  usePathname: () => "/records",
  useRouter: () => ({ push, refresh }),
  useSearchParams: () => new URLSearchParams(search),
}))

describe("頁首重新整理", () => {
  const scrollWindow = vi.fn()
  beforeEach(() => {
    vi.clearAllMocks()
    vi.stubGlobal("scrollTo", scrollWindow)
  })
  afterEach(() => vi.unstubAllGlobals())

  it("等資料更新完成後再捲回頂端，避免重繪時又被拉走", async () => {
    let finish: () => void = () => {}
    const reload = vi.fn(() => new Promise<void>((resolve) => { finish = resolve }))
    render(<main><PageHeader title="項目" actions={[{
      label: "重新整理", icon: <span aria-hidden>R</span>, refresh: true, onClick: reload,
    }]} /></main>)
    const main = document.querySelector("main")!
    main.scrollTo = vi.fn()
    fireEvent.click(screen.getByRole("button", { name: "重新整理" }))
    expect(reload).toHaveBeenCalledOnce()
    vi.mocked(main.scrollTo).mockClear()
    scrollWindow.mockClear()
    await act(async () => { finish() })
    expect(main.scrollTo).toHaveBeenCalledWith({ top: 0 })
    expect(scrollWindow).toHaveBeenCalledWith({ top: 0 })
  })
})

describe("useListRefresh", () => {
  beforeEach(() => vi.clearAllMocks())

  it("在第一頁時重新取得資料並保留篩選", () => {
    search = "keyword=bag"
    const { result } = renderHook(() => useListRefresh())
    act(() => { result.current() })
    expect(refresh).toHaveBeenCalledOnce()
    expect(push).not.toHaveBeenCalled()
  })

  it("在其他頁時回到保留篩選的第一頁", () => {
    search = "keyword=bag&cursor=abc&direction=next&seq=3"
    const { result } = renderHook(() => useListRefresh())
    act(() => { result.current() })
    expect(push).toHaveBeenCalledWith("/records?keyword=bag")
    expect(refresh).not.toHaveBeenCalled()
  })
})
