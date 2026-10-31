import type { ReactNode } from "react"
import { RefreshCw } from "lucide-react"
import { cls, ICON_SIZE } from "../internals"
import styles from "../styles/page-header.module.css"
import ActionMenu, { type ActionMenuItem } from "./ActionMenu"

type PageHeaderProps = {
  title: string
  subtitle?: string
  actions?: ReactNode
  mobileActions?: (ActionMenuItem | null | false | undefined)[]
  mobileRefresh?: { label: string; onClick: () => void; disabled?: boolean }
}

export default function PageHeader({
  title, subtitle, actions, mobileActions, mobileRefresh,
}: PageHeaderProps) {
  return (
    <header className={cls(styles.pageHeader, mobileRefresh && styles.pageHeaderCompact)}>
      <div className={styles.pageHeaderText}>
        <h1 className={styles.pageTitle}>{title}</h1>
        {subtitle && <p className={styles.pageSubtitle}>{subtitle}</p>}
      </div>
      {actions && <div className={styles.pageHeaderActions}>{actions}</div>}
      {(mobileActions || mobileRefresh) && (
        <div className={styles.pageHeaderMobileActions}>
          {mobileRefresh && <button type="button" className={styles.refreshIcon}
            aria-label={mobileRefresh.label} title={mobileRefresh.label}
            disabled={mobileRefresh.disabled} onClick={mobileRefresh.onClick}>
            <RefreshCw size={ICON_SIZE.md} aria-hidden />
          </button>}
          {mobileActions && <ActionMenu items={mobileActions} sheet={Boolean(mobileRefresh)} />}
        </div>
      )}
    </header>
  )
}
