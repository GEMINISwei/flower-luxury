"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { useEffect, useState } from "react"
import { ChevronRight, Ellipsis } from "lucide-react"
import { BottomSheet, ICON_SIZE, type MenuItem } from "@/shared/ui"
import { useLocale, useT } from "@/shared/i18n/context"
import type { RouteArea } from "@/shared/module"
import { appMessages } from "@/config/i18n"
import { getAccountMenuEntries } from "./account-menu"
import { getMobileNavigation, isMoreActive, isShellLinkActive } from "./navigation"
import { NAV_ICONS } from "./nav-icons"
import styles from "./shell.module.css"

type MobileNavigationProps = {
  area: RouteArea
  permissions: readonly string[]
  nickname: string
  userRole: string
  accountItems: MenuItem[]
}

export default function MobileNavigation({
  area, permissions, nickname, userRole, accountItems,
}: MobileNavigationProps) {
  const t = useT(appMessages)
  const locale = useLocale()
  const pathname = usePathname()
  const [openPath, setOpenPath] = useState<string | null>(null)
  const open = openPath === pathname
  const routes = getMobileNavigation(area, permissions)
  const entries = getAccountMenuEntries(area, permissions)
  const active = isMoreActive(pathname, routes.more, entries)
  useEffect(() => {
    const media = window.matchMedia("(max-width: 720px)")
    const closeOnDesktop = () => { if (!media.matches) setOpenPath(null) }
    media.addEventListener("change", closeOnDesktop)
    return () => media.removeEventListener("change", closeOnDesktop)
  }, [])
  return <>
    <nav className={styles.bottomNavigation} aria-label={t("mobileNav")}>
      {routes.primary.map((route) => {
        const Icon = NAV_ICONS[route.navIcon]
        const selected = isShellLinkActive(pathname, route.path)
        return <Link key={route.path} href={route.path} prefetch={false}
          className={`${styles.bottomNavItem} ${selected ? styles.bottomNavItemActive : ""}`}
          aria-current={selected ? "page" : undefined}>
          <Icon size={ICON_SIZE.md} aria-hidden /><span>{route.label[locale]}</span>
        </Link>
      })}
      <button type="button" className={`${styles.bottomNavItem}
        ${active ? styles.bottomNavItemActive : ""}`} aria-expanded={open}
        aria-haspopup="dialog" onClick={(event) => {
          event.currentTarget.focus(); setOpenPath(pathname)
        }}>
        <Ellipsis size={ICON_SIZE.md} aria-hidden /><span>{t("more")}</span>
      </button>
    </nav>
    <BottomSheet open={open} label={t("more")} onOpenChange={() => setOpenPath(null)}
      header={<div className={styles.moreUser}>
        <span className={styles.userAvatar} aria-hidden>{nickname[0]?.toUpperCase() ?? "?"}</span>
        <span className={styles.moreUserDetails}>
          <span className={styles.userName}>{nickname}</span>
          <span className={styles.userRole}>{userRole}</span>
        </span>
      </div>}>
      <p className={styles.moreLabel}>{t("moreFeatures")}</p>
      <div className={styles.moreItems}>
        {routes.more.map((route) => {
          const Icon = NAV_ICONS[route.navIcon]
          return <Link key={route.path} href={route.path} prefetch={false}
            onClick={() => setOpenPath(null)} className={styles.moreItem}
            aria-current={isShellLinkActive(pathname, route.path) ? "page" : undefined}>
            <Icon size={ICON_SIZE.md} aria-hidden /><span>{route.label[locale]}</span>
            <ChevronRight size={ICON_SIZE.sm} aria-hidden />
          </Link>
        })}
        {accountItems.map((item, index) => <button key={entries[index].label} type="button"
          className={`${styles.moreItem} ${entries[index].kind === "logout"
            ? styles.moreLogout : ""}`} onClick={() => { setOpenPath(null); item.onClick?.() }}>
          {item.icon}<span>{item.label}</span>
          <ChevronRight size={ICON_SIZE.sm} aria-hidden />
        </button>)}
      </div>
    </BottomSheet>
  </>
}
