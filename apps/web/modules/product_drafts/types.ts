import type { Schema } from "@/shared/api/contract"
export type DraftInfo = Schema<"DraftInfo">
export type DraftFields = Schema<"DraftFields">
export type DraftSummary = Schema<"DraftSummary">
export type MessageInfo = Schema<"MessageInfo">
export type SourceInfo = Schema<"SourceInfo">
export type DraftValues = Record<keyof Required<DraftFields>, string>
export type DraftQuoteInfo = Schema<"DraftQuoteInfo">
export type PrefillSettingsInfo = Schema<"PrefillSettingsInfo">
