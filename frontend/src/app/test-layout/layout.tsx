'use client'

import { AppLayout } from '@/components/layout/AppLayout'

export default function TestLayoutLayout({
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