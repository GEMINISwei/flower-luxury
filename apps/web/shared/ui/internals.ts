// UI kit 的內部工具; 版面元件直接使用 `as`、`className` 與 `style`。

/** 鍵盤可聚焦的元素; 對話框在這些元素之間循環。 */
export const FOCUSABLE_SELECTOR = [
  "a[href]", "button:not(:disabled)", "input:not(:disabled):not([type='hidden'])",
  "select:not(:disabled)", "textarea:not(:disabled)", "[tabindex]:not([tabindex='-1']):not(:disabled)",
].join(", ")

/** 手機與平板由使用者點欄位才輸入, 避免開啟對話框就跳出鍵盤。 */
export function isCoarsePointer() {
  return typeof window !== "undefined" && typeof window.matchMedia === "function"
    && window.matchMedia("(pointer: coarse)").matches
}

export function cls(...parts: Array<string | false | null | undefined>) {
  return parts.filter(Boolean).join(" ")
}

/** 版面元件共用的基本 props: 換 HTML 標籤、加 class、加行內樣式。 */
export type BaseProps = {
  /** 要渲染成哪個 HTML 標籤, 預設由各元件決定。例: `<Container as="section">`。 */
  as?: React.ElementType
  className?: string
  style?: React.CSSProperties
}

/**
 * 間距刻度的階號。刻意是聯集而不是 `number`: 階號不是倍率, 而是 `shared/ui/styles/tokens.css` 裡真的
 * 存在的那幾個 token。收成 `number` 的話 `gap={7}` 會產生不存在的 `var(--space-7)`,
 * gap 靜靜變成 0。
 */
export type SpaceStep = 1 | 2 | 3 | 4 | 5 | 6 | 8 | 10 | 12

/**
 * 間距: 階號換成對應的 token, 字串原樣輸出。
 *
 * 回傳 `var(--space-n)` 而不是自己算 px —— 刻度的單一事實來源留在 CSS 那一側
 * (`shared/ui/styles/tokens.css` 的 `--space-*`)。在這裡算 px 的話, 改刻度要同時改兩邊。
 */
export function spacing(value: SpaceStep | string | undefined) {
  if (value === undefined) return undefined
  return typeof value === "number" ? `var(--space-${value})` : value
}

/**
 * 圖示尺寸。lucide 的 `size` prop 產生 `<svg width height>`, CSS 的 `--size-icon-*` 管不到它,
 * 所以刻度在這裡再宣告一份, **數字必須與 `shared/ui/styles/tokens.css` 的 `--size-icon-*` 相同**。
 *
 * 尺寸會隨斷點變的圖示 (側欄與底部導覽) 不要用這個 —— media query 改得動 CSS, 改不動 prop。
 */
export const ICON_SIZE = { sm: 16, md: 20, lg: 24 } as const

/**
 * 關閉瀏覽器與密碼管理器自己的輸入紀錄與自動填入, 欄位的建議只由系統提供時用。
 *
 * Chrome 與 Safari 對個人資料的自動填入會無視 `autocomplete="off"`, 改看標籤文字
 * (「名稱」「Name」被當成姓名), 所以輸入框也不要給會被判斷成個人資料的 `name`。
 * 這幾個屬性集中在這裡, 瀏覽器改版讓某一招失效時只要改一處。
 */
export const NO_BROWSER_SUGGESTIONS = {
  autoComplete: "off",
  "data-1p-ignore": "true",
  "data-lpignore": "true",
  "data-form-type": "other",
} as const
