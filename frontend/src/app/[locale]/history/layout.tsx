import { ReactNode } from 'react'

interface HistoryLayoutProps {
  children: ReactNode
}

export default function HistoryLayout({ children }: HistoryLayoutProps) {
  return <>{children}</>
} 