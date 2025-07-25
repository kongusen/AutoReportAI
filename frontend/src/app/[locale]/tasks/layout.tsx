import { ReactNode } from 'react'

interface TasksLayoutProps {
  children: ReactNode
}

export default function TasksLayout({ children }: TasksLayoutProps) {
  return <>{children}</>
} 