'use client'

import { useEffect } from 'react'
import { usePathname, useRouter, useParams } from 'next/navigation'
import { AuthProvider as AuthContextProvider, useAuth } from '@/lib/auth/AuthContext'

// Protected route wrapper
function ProtectedRouteHandler({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const params = useParams()
  const locale = params.locale as string || 'en-US'
  const { isAuthenticated, isLoading } = useAuth()

  useEffect(() => {
    // Skip auth check for public routes
    const isPublicRoute = 
      pathname.includes('/login') || 
      pathname.includes('/register') || 
      pathname.includes('/forgot-password') || 
      pathname.includes('/reset-password') ||
      pathname.includes('/verify-email')
    
    if (!isLoading) {
      if (!isAuthenticated && !isPublicRoute) {
        // Redirect to login if not authenticated and not on a public route
        router.push(`/${locale}/login?redirect=${encodeURIComponent(pathname)}`)
      } else if (isAuthenticated && isPublicRoute) {
        // Redirect to dashboard if authenticated and on a public route
        router.push(`/${locale}/dashboard`)
      }
    }
  }, [isAuthenticated, isLoading, pathname, router, locale])

  // Show nothing while loading to prevent flash of content
  if (isLoading) {
    return null
  }

  return <>{children}</>
}

export default function AuthProvider({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <AuthContextProvider>
      <ProtectedRouteHandler>{children}</ProtectedRouteHandler>
    </AuthContextProvider>
  )
}
