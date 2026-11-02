"use client"

import type { ComponentProps } from "react"
import { useEffect, useRef, useTransition } from "react"
import styles from "../styles/page-header.module.css"
import IconButton from "./IconButton"
import ActionMenu from "./ActionMenu"

type PageHeaderAction = Omit<ComponentProps<typeof IconButton>, "onClick"> & {
  refresh?: boolean
  /** 重新整理可以回傳 Promise, 頁首會等它完成才捲回頂端。 */
  onClick?: () => void | Promise<unknown>
}
type PageHeaderProps = {
  title: string
  subtitle?: string
  actions?: (PageHeaderAction | null | false | undefined)[] | null
}

function headerActions(actions: PageHeaderAction[]) {
  if (actions.length <= 3) return { visible: actions, overflow: [] }
  const priority = [actions.find((item) => item.refresh), actions.find((item) => item.primary)]
    .filter((item): item is PageHeaderAction => Boolean(item))
  const visible = [...new Set([...priority, ...actions])].slice(0, 2)
  return { visible, overflow: actions.filter((item) => !visible.includes(item)) }
}

// 版面可能由 <main> 自己捲動, 視窗與它都要回到頂端.
function scrollToTop() {
  document.querySelector("main")?.scrollTo({ top: 0 })
  window.scrollTo({ top: 0 })
}

// 重新整理要像重新進入畫面: 按下時先回頂端, 新資料畫好後再回一次,
// 否則重繪時捲動位置會被改掉, 看起來像跳到中段.
function useRefreshActions(actions: PageHeaderAction[]): PageHeaderAction[] {
  const [refreshing, startRefresh] = useTransition()
  const wasRefreshing = useRef(false)
  useEffect(() => {
    if (wasRefreshing.current && !refreshing) scrollToTop()
    wasRefreshing.current = refreshing
  }, [refreshing])
  return actions.map((action) => !action.refresh ? action : { ...action, onClick: () => {
    scrollToTop()
    startRefresh(async () => { await action.onClick?.() })
  } })
}

export default function PageHeader({ title, subtitle, actions = [] }: PageHeaderProps) {
  const { visible, overflow } = headerActions(useRefreshActions(
    (actions ?? []).filter((item): item is PageHeaderAction => Boolean(item)),
  ))
  return (
    <header className={styles.pageHeader}>
      <div className={styles.pageHeaderText}>
        <h1 className={styles.pageTitle}>{title}</h1>
        {subtitle && <p className={styles.pageSubtitle}>{subtitle}</p>}
      </div>
      {visible.length > 0 && <div className={styles.pageHeaderActions}>
        {visible.map((action) => <IconButton key={action.label} {...action} />)}
        {overflow.length > 0 && <ActionMenu sheet items={overflow.map((action) => ({
          ...action,
          onClick: () => {
            if (action.type === "submit" && action.form) {
              const form = document.getElementById(action.form)
              if (form instanceof HTMLFormElement) form.requestSubmit()
            } else action.onClick?.()
          },
        }))} />}
      </div>}
    </header>
  )
}
