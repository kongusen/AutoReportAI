'use client'

import { Toaster } from 'react-hot-toast'
import { AuthProvider } from './AuthProvider'
import { WebSocketProvider } from './WebSocketProvider'

interface AppProvidersProps {
  children: React.ReactNode
}

export function AppProviders({ children }: AppProvidersProps) {
  return (
    <AuthProvider>
      <WebSocketProvider>
        {children}
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: '#fff',
              color: '#000',
              border: '1px solid #e5e5e5',
              borderRadius: '8px',
              fontSize: '14px',
            },
            success: {
              style: {
                border: '1px solid #22c55e',
              },
            },
            error: {
              style: {
                border: '1px solid #ef4444',
              },
            },
          }}
        />
      </WebSocketProvider>
    </AuthProvider>
  )
}