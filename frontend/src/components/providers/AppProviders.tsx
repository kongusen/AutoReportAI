'use client'

import React from 'react'
import { LoadingProvider } from './LoadingProvider'
import { ErrorNotificationProvider } from './ErrorNotificationProvider'
import AuthProvider from './AuthProvider'
import { NotificationProvider } from './NotificationProvider'
import { I18nProvider } from './I18nProvider'
import { ThemeProvider } from '@/components/ui/ThemeProvider'

interface AppProvidersProps {
  children: React.ReactNode
  locale?: string
}

export function AppProviders({ children, locale }: AppProvidersProps) {
  return (
    <ThemeProvider>
      <I18nProvider initialLocale={locale === 'en-US' ? 'en-US' : 'zh-CN'}>
        <AuthProvider>
          <LoadingProvider maxConcurrentLoading={3}>
            <ErrorNotificationProvider 
              maxNotifications={5}
              defaultPosition="top-right"
            >
              <NotificationProvider>
                {children}
              </NotificationProvider>
            </ErrorNotificationProvider>
          </LoadingProvider>
        </AuthProvider>
      </I18nProvider>
    </ThemeProvider>
  )
}

// Export individual providers for selective use
export {
  LoadingProvider,
  ErrorNotificationProvider,
  AuthProvider,
  NotificationProvider,
  I18nProvider,
  ThemeProvider,
}

// Export hooks for easy access
export { useLoading } from './LoadingProvider'
export { useErrorNotification, useApiErrorHandler, useFormErrorHandler } from './ErrorNotificationProvider'
export { default as useAuth } from './AuthProvider'
export { useNotificationContext as useNotification } from './NotificationProvider'
export { useI18n } from './I18nProvider'