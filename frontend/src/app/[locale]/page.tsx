'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function LocalePage({ params }: { params: Promise<{ locale: string }> }) {
  const router = useRouter()

  useEffect(() => {
    const handleRedirect = async () => {
      const { locale } = await params
      router.replace(`/${locale}/dashboard`)
    }
    handleRedirect()
  }, [router, params])

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="bg-white p-8 rounded-lg shadow-md max-w-md w-full text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-600 mx-auto mb-4"></div>
        <h1 className="text-xl font-semibold text-gray-900 mb-2">
          正在跳转...
        </h1>
        <p className="text-gray-600">
          正在加载 AutoReportAI 应用
        </p>
      </div>
    </div>
  )
}