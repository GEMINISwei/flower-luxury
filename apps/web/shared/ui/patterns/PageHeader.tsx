"use client"

import type { ComponentProps } from "react"
import styles from "../styles/page-header.module.css"
import IconButton from "./IconButton"
import ActionMenu from "./ActionMenu"

type PageHeaderAction = ComponentProps<typeof IconButton> & { refresh?: boolean }
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

export default function PageHeader({ title, subtitle, actions = [] }: PageHeaderProps) {
  const { visible, overflow } = headerActions(
    (actions ?? []).filter((item): item is PageHeaderAction => Boolean(item)),
  )
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
