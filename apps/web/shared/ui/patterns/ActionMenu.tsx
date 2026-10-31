"use client"

import { MoreHorizontal, MoreVertical } from "lucide-react"
import { useT } from "@/shared/i18n/context"
import { uiMessages } from "../i18n"
import { ICON_SIZE } from "../internals"
import Menu, { type MenuItem } from "./Menu"

type ActionMenuProps = {
  items: (MenuItem | null | false | undefined)[]
  sheet?: boolean
}

/** 表格列尾的「⋮」操作選單。 */
export default function ActionMenu({ items, sheet = false }: ActionMenuProps) {
  const t = useT(uiMessages)
  const Icon = sheet ? MoreHorizontal : MoreVertical

  return (
    <Menu
      items={items}
      trigger={<Icon size={ICON_SIZE.sm} aria-hidden />}
      triggerLabel={t("actionMenu")}
      sheetTitle={sheet ? t("actionMenu") : undefined}
    />
  )
}
