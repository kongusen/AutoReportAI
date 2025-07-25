import { ReactNode } from 'react'

interface DataSourcesLayoutProps {
  children: ReactNode
}

export default function DataSourcesLayout({ children }: DataSourcesLayoutProps) {
  return <>{children}</>
} 