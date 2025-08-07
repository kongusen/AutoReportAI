import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { AppProviders } from '@/components/providers/AppProviders'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'AutoReportAI - 智能报告生成平台',
  description: 'AI驱动的自动化报告生成和数据分析平台',
  keywords: ['AI报告', '数据分析', '自动化', '商业智能'],
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN" className="h-full">
      <body className={`${inter.className} h-full antialiased`}>
        <AppProviders>
          {children}
        </AppProviders>
      </body>
    </html>
  )
}