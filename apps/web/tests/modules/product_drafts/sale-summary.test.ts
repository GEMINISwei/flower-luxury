import { expect, it } from "vitest"
import { draftSaleSummary } from "@/modules/product_drafts/capabilities"

const quote = { id: "a", vendor_id: "v", original_amount: "100", exchange_rate: "4.5" }

it("成交預覽使用選定報價逐筆匯率與目前成本並呈現虧損", () => {
  expect(draftSaleSummary([quote], "a", "500"))
    .toEqual({ quote, amountTwd: 450, cost: 500, profit: -50 })
  expect(draftSaleSummary([quote], null, "500")).toBeNull()
  expect(draftSaleSummary([quote], "missing", "500")).toBeNull()
  expect(draftSaleSummary([quote], "a", "")).toBeNull()
})

it("成交預覽以十進位乘法四捨五入臺幣並保留零成本", () => {
  const decimal = { ...quote, original_amount: "2.10", exchange_rate: "5.000000" }
  expect(draftSaleSummary([decimal], "a", "0"))
    .toEqual({ quote: decimal, amountTwd: 11, cost: 0, profit: 11 })
})
