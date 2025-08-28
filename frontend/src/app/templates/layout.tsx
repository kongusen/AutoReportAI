'use client'

import { AppLayout } from '@/components/layout/AppLayout'

export default function TemplatesLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <AppLayout>
      {children}
    </AppLayout>
  )
}