import "server-only"
/**
 * auth 模組的 Server 公開面。
 *
 * 登入與公開註冊畫面屬於 auth, 註冊碼規則由 registration 模組擁有。
 *
 * auth 沒有「模組主頁」, 所以頁面用 `<name>-page.server.tsx` 命名 (有主頁的
 * 模組是 `page.server.tsx` + `<name>-page.server.tsx`, 例見 `modules/roles`)。
 */

export { default as LoginPage, generateMetadata as generateLoginMetadata } from "./login-page.server"
export type { LoginPageProps } from "./login-page.server"
export { getCurrentUser } from "./current-user.server"
export { default as SignupPage, generateMetadata as generateSignupMetadata } from "./signup-page.server"
