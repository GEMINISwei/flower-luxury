"use client"

import Link from "next/link"
import type { ComponentProps } from "react"
import { ChevronLeft } from "lucide-react"
import { Container } from "../primitives"
import { ICON_SIZE } from "../internals"
import ui from "../styles/page-header.module.css"
import PageHeader from "./PageHeader"

type FormPageShellProps = Pick<ComponentProps<typeof PageHeader>, "mobileActions" | "mobileRefresh"> & {
  title: string
  subtitle?: string
  actions: React.ReactNode
  backHref: string
  backLabel: string
  children: React.ReactNode
}

export default function FormPageShell({
  title,
  subtitle,
  actions,
  mobileActions,
  mobileRefresh,
  backHref,
  backLabel,
  children,
}: FormPageShellProps) {
  return (
    <Container size="lg" padded>
      <PageHeader title={title} subtitle={subtitle} actions={actions}
        mobileActions={mobileActions} mobileRefresh={mobileRefresh} />
      <Link href={backHref} className={ui.detailBackLink}>
        <ChevronLeft size={ICON_SIZE.md} />
        {backLabel}
      </Link>
      {children}
    </Container>
  )
}
