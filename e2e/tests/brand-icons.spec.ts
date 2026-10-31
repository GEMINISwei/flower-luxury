import { expect, test } from "@playwright/test"

test("登入頁與主畫面宣告可讀取的品牌圖示且安裝圖示具有實色底", async ({ page, request }) => {
  await page.goto("/login")
  const apple = page.locator('link[rel="apple-touch-icon"][sizes="180x180"]')
  await expect(apple).toHaveCount(1)
  const manifestHref = await page.locator('link[rel="manifest"]').getAttribute("href")
  const response = await request.get(manifestHref!)
  expect(response.ok()).toBe(true)
  const manifest = await response.json() as {
    icons: { src: string; sizes: string; purpose?: string }[]
  }
  const icons = [
    { src: (await apple.getAttribute("href"))!, sizes: "180x180" }, ...manifest.icons,
  ]
  expect(icons.length).toBeGreaterThanOrEqual(3)
  for (const icon of icons) {
    const result = await page.evaluate(async ({ src }) => {
      const image = new Image()
      image.src = src
      await image.decode()
      const canvas = document.createElement("canvas")
      canvas.width = image.naturalWidth
      canvas.height = image.naturalHeight
      const context = canvas.getContext("2d")!
      context.drawImage(image, 0, 0)
      const { data } = context.getImageData(0, 0, canvas.width, canvas.height)
      return {
        sizes: `${canvas.width}x${canvas.height}`, corner: [...data.slice(0, 4)],
        opaque: data.every((value, index) => index % 4 !== 3 || value === 255),
        hasArtwork: data.some((value, index) => index % 4 === 0 && value < 150),
      }
    }, icon)
    expect(result.sizes).toBe(icon.sizes)
    expect(result.corner).toEqual([244, 238, 224, 255])
    expect(result.opaque).toBe(true)
    expect(result.hasArtwork).toBe(true)
  }
  const logo = page.locator("img").first()
  const result = await logo.evaluate(async (element) => {
    const image = element as HTMLImageElement
    await image.decode()
    const canvas = document.createElement("canvas")
    canvas.width = image.naturalWidth
    canvas.height = image.naturalHeight
    const context = canvas.getContext("2d")!
    context.drawImage(image, 0, 0)
    const { data } = context.getImageData(0, 0, canvas.width, canvas.height)
    return { cornerAlpha: data[3], hasArtwork: data.some((v, i) => i % 4 === 3 && v > 200) }
  })
  expect(result.cornerAlpha).toBe(0)
  expect(result.hasArtwork).toBe(true)
  const favicon = await page.locator('link[rel="icon"][href*="favicon"]').getAttribute("href")
  const ico = await request.get(favicon!)
  expect(ico.ok()).toBe(true)
  const body = await ico.body()
  expect(body.readUInt16LE(2)).toBe(1)
  expect(body.readUInt16LE(4)).toBeGreaterThanOrEqual(3)
})
