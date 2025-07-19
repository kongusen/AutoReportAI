import { Inter } from 'next/font/google'
import './globals.css'
import AuthProvider from '@/components/providers/AuthProvider'
import { AppProvider } from '@/lib/context/app-context'
import { StateDevTools } from '@/lib/context/dev-tools'

const inter = Inter({ subsets: ['latin'] })

export const metadata = {
  title: 'AutoReportAI',
  description: 'Automated Report Generation System',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <AppProvider>
          <AuthProvider>{children}</AuthProvider>
          <StateDevTools />
        </AppProvider>
      </body>
    </html>
  )
}
