import type { ReactNode } from "react"
import Link from "next/link"
import { ChevronLeft } from "lucide-react"
import { ICON_SIZE } from "../internals"
import styles from "../styles/page-header.module.css"
import ActionMenu, { type ActionMenuItem } from "./ActionMenu"

type PageHeaderProps = {
  title: string
  subtitle?: string
  back?: { href: string; label: string }
  actions?: ReactNode
  mobileActions?: (ActionMenuItem | null | false | undefined)[]
}

export default function PageHeader({
  title, subtitle, back, actions, mobileActions,
}: PageHeaderProps) {
  return (
    <header className={styles.pageHeader}>
      <div className={styles.pageHeaderHeading}>
        {back && <Link href={back.href} className={styles.pageHeaderBackLink}
          aria-label={back.label} title={back.label}>
          <ChevronLeft size={ICON_SIZE.md} aria-hidden />
        </Link>}
        <div className={styles.pageHeaderText}>
          <h1 className={styles.pageTitle}>{title}</h1>
          {subtitle && <p className={styles.pageSubtitle}>{subtitle}</p>}
        </div>
      </div>
      {actions && <div className={styles.pageHeaderActions}>{actions}</div>}
      {mobileActions && (
        <div className={styles.pageHeaderMobileActions}>
          <ActionMenu items={mobileActions} />
        </div>
      )}
    </header>
  )
}
