import "server-only"
/** 登入、註冊畫面與目前使用者的 Server 公開面。 */

export { default as LoginPage, generateMetadata as generateLoginMetadata } from "./login-page.server"
export type { LoginPageProps } from "./login-page.server"
export { getCurrentUser } from "./current-user.server"

export { default as SignupPage, generateMetadata as generateSignupMetadata } from "./signup-page.server"
