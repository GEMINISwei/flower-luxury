import "server-only"
export { default as DraftsPage, generateMetadata as generateDraftsMetadata } from "./page.server"
export type { DraftsPageProps } from "./page.server"
export { default as DraftDetailPage,
  generateMetadata as generateDraftDetailMetadata } from "./detail-page.server"
export type { DraftDetailPageProps } from "./detail-page.server"
export { default as PrefillSettingsPage,
  generateMetadata as generatePrefillSettingsMetadata } from "./prefill-page.server"
