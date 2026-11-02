import type { GetRequest, Schema } from "@/shared/api/contract"

export type ProductInfo = Schema<"ProductInfo">
export type ProductStatus = Schema<"ProductStatus">
export type ProductCategory = Schema<"ProductCategory">
export type SuggestionField = NonNullable<GetRequest<"/products/suggestions">["query"]>["field"]
export type StatusHistoryInfo = Schema<"StatusHistoryInfo">

export type PhotoInfo = Schema<"PhotoInfo">

export type QuoteInfo = Schema<"QuoteInfo">
export type SaleInfo = Schema<"SaleInfo">
