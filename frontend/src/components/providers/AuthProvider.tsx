'use client'

import { useEffect } from 'react'
import { usePathname, useRouter } from 'next/navigation'

export default function AuthProvider({
  children,
}: {
  children: React.ReactNode
}) {
  const router = useRouter()
  const pathname = usePathname()

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    const isAuthPage = pathname === '/login'

    if (!token && !isAuthPage) {
      router.push('/login')
    } else if (token && isAuthPage) {
      router.push('/')
    }
  }, [pathname, router])

  return <>{children}</>
}
