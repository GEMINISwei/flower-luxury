import type { ReactNode } from "react"
import { cls } from "../internals"
import styles from "../styles/page-header.module.css"

type IconButtonProps = {
  label: string
  icon: ReactNode
  onClick?: () => void
  disabled?: boolean
  primary?: boolean
  color?: "default" | "error"
  type?: "button" | "submit"
  form?: string
}

export default function IconButton({
  label, icon, onClick, disabled, primary, color, type = "button", form,
}: IconButtonProps) {
  return <button type={type} form={form} aria-label={label} title={label}
    disabled={disabled} onClick={onClick}
    className={cls(styles.iconButton, primary && styles.primaryAction,
      color === "error" && styles.dangerAction)}>
    <span aria-hidden="true">{icon}</span>
  </button>
}
