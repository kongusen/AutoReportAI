'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { getAuthToken } from '@/lib/auth'

interface User {
  username: string
  email: string
  full_name?: string
  is_active: boolean
  is_superuser: boolean
  id: string
}

export default function TestPage() {
  const [token, setToken] = useState<string | null>(null)
  const [user, setUser] = useState<User | null>(null)

  useEffect(() => {
    const currentToken = getAuthToken()
    setToken(currentToken)
    
    if (currentToken) {
      // 直接调用API测试
      fetch('http://localhost:8000/api/v1/users/me', {
        headers: {
          'Authorization': `Bearer ${currentToken}`
        }
      })
      .then(res => res.json())
      .then(data => setUser(data))
      .catch(err => console.error('获取用户信息失败:', err))
    }
  }, [])

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">测试页面 (无AuthGuard)</h1>
        
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Token状态</h2>
          {token ? (
            <div className="text-green-600">
              <p>✅ Token已找到</p>
              <p className="text-sm text-gray-600 mt-2">
                Token: {token.substring(0, 50)}...
              </p>
            </div>
          ) : (
            <div className="text-red-600">
              <p>❌ 未找到Token</p>
              <p className="text-sm">请先登录: <Link href="/login" className="text-blue-600 underline">登录页面</Link></p>
            </div>
          )}
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">用户信息</h2>
          {user ? (
            <div className="text-green-600">
              <p>✅ 用户信息获取成功</p>
              <pre className="text-sm text-gray-600 mt-2 bg-gray-50 p-4 rounded">
                {JSON.stringify(user, null, 2)}
              </pre>
            </div>
          ) : token ? (
            <div className="text-blue-600">
              <p>⏳ 正在获取用户信息...</p>
            </div>
          ) : (
            <div className="text-gray-600">
              <p>需要先登录才能获取用户信息</p>
            </div>
          )}
        </div>

        <div className="mt-8 space-x-4">
          <Link href="/login" className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700">
            登录页面
          </Link>
          <Link href="/" className="bg-gray-600 text-white px-6 py-2 rounded hover:bg-gray-700">
            受保护的首页
          </Link>
        </div>
      </div>
    </div>
  )
} 