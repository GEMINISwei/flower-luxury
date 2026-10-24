"use client"

import { Container } from "../primitives"
import PageHeader from "./PageHeader"

type FormPageShellProps = {
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
  backHref,
  backLabel,
  children,
}: FormPageShellProps) {
  return (
    <Container size="lg" padded>
      <PageHeader title={title} subtitle={subtitle} actions={actions}
        back={{ href: backHref, label: backLabel }} />
      {children}
    </Container>
  )
}
