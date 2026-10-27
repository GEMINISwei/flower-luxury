import type { ProductCategory } from "./types"

export const CATEGORIES = {
  "鞋子": "shoes", "配飾": "accessories", "皮件": "leather", "包包": "bags",
  "帽子": "hats", "衣服": "clothes", "其他": "other",
} as const satisfies Record<ProductCategory, string>
