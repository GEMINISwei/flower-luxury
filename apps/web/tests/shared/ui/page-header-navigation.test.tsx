import { render, screen, within } from "@testing-library/react"
import { expect, it } from "vitest"
import PageHeader from "@/shared/ui/patterns/PageHeader"
import FormPageShell from "@/shared/ui/patterns/FormPageShell"

it("返回入口與頁面標題同在頁首並保留可存取名稱", () => {
  render(<PageHeader title="項目詳情" back={{ href: "/records", label: "返回列表" }}
    actions={<button type="button">儲存</button>} />)
  const header = screen.getByRole("banner")
  const back = within(header).getByRole("link", { name: "返回列表" })
  expect(back).toHaveAttribute("href", "/records")
  expect(back).toHaveAttribute("title", "返回列表")
  expect(back.textContent).toBe("")
  expect(within(header).getByRole("heading", { level: 1, name: "項目詳情" }))
    .toBeInTheDocument()
  expect(within(header).getByRole("button", { name: "儲存" })).toBeInTheDocument()
})

it("表單外殼只在頁首提供一個返回入口", () => {
  render(<FormPageShell title="項目詳情" subtitle="項目編號" backHref="/records"
    backLabel="返回列表" actions={<button type="button">儲存</button>}>
    <section aria-label="內容">項目資料</section>
  </FormPageShell>)
  const links = screen.getAllByRole("link", { name: "返回列表" })
  expect(links).toHaveLength(1)
  expect(screen.getByRole("banner")).toContainElement(links[0])
  expect(links[0]).toHaveAttribute("href", "/records")
})
