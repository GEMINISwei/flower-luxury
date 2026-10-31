import { expect, type Page } from "@playwright/test"

export async function expectHeaderFits(page: Page) {
  const heading = page.getByRole("heading", { level: 1 })
  await expect(heading).toBeVisible()
  await page.evaluate(() => document.fonts.ready)
  const layout = await heading.evaluate((element) => {
    const header = element.closest("header")!
    const box = (node: Element) => {
      const { left, right, top, bottom, width } = node.getBoundingClientRect()
      return { left, right, top, bottom, width }
    }
    return {
      header: box(header), title: box(element), viewport: innerWidth,
      overflow: header.scrollWidth - header.clientWidth,
      controls: [...header.querySelectorAll("button, a")]
        .filter((node) => node.getBoundingClientRect().width > 0)
        .map((node) => ({ ...box(node), label: node.textContent })),
    }
  })
  expect(layout.overflow).toBeLessThanOrEqual(1)
  expect(layout.header.left).toBeGreaterThanOrEqual(-1)
  expect(layout.header.right).toBeLessThanOrEqual(layout.viewport + 1)
  expect(layout.title.width).toBeGreaterThanOrEqual(120)
  for (const control of layout.controls) {
    expect(control.left, control.label ?? "").toBeGreaterThanOrEqual(layout.header.left)
    expect(control.right, control.label ?? "").toBeLessThanOrEqual(layout.header.right)
    expect(control.bottom).toBeLessThanOrEqual(layout.header.bottom)
    const separate = control.top >= layout.title.bottom - 1
      || control.left >= layout.title.right - 1 || control.right <= layout.title.left + 1
    expect(separate, control.label ?? "").toBe(true)
  }
}
