'use client'

import { useAuthStore } from '@/features/auth/authStore'
import { Avatar } from '@/components/ui/Avatar'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { CogIcon, UserIcon, KeyIcon, BellIcon } from '@heroicons/react/24/outline'
import Link from 'next/link'

export default function ProfilePage() {
  const { user } = useAuthStore()

  const profileSections = [
    {
      title: '基本信息',
      description: '管理您的个人资料和账户信息',
      icon: UserIcon,
      href: '#basic-info',
      disabled: true
    },
    {
      title: '系统设置',
      description: '配置应用偏好设置和系统选项',
      icon: CogIcon,
      href: '/settings'
    },
    {
      title: '安全设置',
      description: '管理密码、两步验证和账户安全',
      icon: KeyIcon,
      href: '#security',
      disabled: true
    },
    {
      title: '通知设置',
      description: '配置邮件通知和消息提醒',
      icon: BellIcon,
      href: '#notifications',
      disabled: true
    }
  ]

  return (
    <div className="max-w-4xl mx-auto">
      {/* 页面标题 */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">个人中心</h1>
        <p className="mt-2 text-gray-600">管理您的个人资料和账户设置</p>
      </div>

      {/* 用户信息卡片 */}
      <Card className="mb-8">
        <div className="p-6">
          <div className="flex items-center space-x-4">
            <Avatar
              size="lg"
              src={undefined}
              fallback={user?.username || user?.email}
            />
            <div className="flex-1">
              <h2 className="text-xl font-semibold text-gray-900">
                {user?.username || '未设置用户名'}
              </h2>
              <p className="text-gray-600">{user?.email}</p>
              <div className="mt-2">
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                  在线
                </span>
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* 设置选项网格 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {profileSections.map((section) => {
          const IconComponent = section.icon
          const isDisabled = section.disabled

          const content = (
            <Card className={`h-full transition-all duration-200 ${
              isDisabled 
                ? 'opacity-50 cursor-not-allowed' 
                : 'hover:shadow-lg hover:border-blue-300 cursor-pointer'
            }`}>
              <div className="p-6">
                <div className="flex items-start space-x-4">
                  <div className={`flex-shrink-0 p-3 rounded-lg ${
                    isDisabled ? 'bg-gray-100' : 'bg-blue-50'
                  }`}>
                    <IconComponent className={`h-6 w-6 ${
                      isDisabled ? 'text-gray-400' : 'text-blue-600'
                    }`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className={`text-lg font-semibold ${
                      isDisabled ? 'text-gray-400' : 'text-gray-900'
                    }`}>
                      {section.title}
                      {isDisabled && (
                        <span className="ml-2 text-xs font-normal text-gray-400">
                          (即将开放)
                        </span>
                      )}
                    </h3>
                    <p className={`mt-1 text-sm ${
                      isDisabled ? 'text-gray-400' : 'text-gray-600'
                    }`}>
                      {section.description}
                    </p>
                  </div>
                </div>
              </div>
            </Card>
          )

          if (isDisabled) {
            return (
              <div key={section.title}>
                {content}
              </div>
            )
          }

          return (
            <Link key={section.title} href={section.href}>
              {content}
            </Link>
          )
        })}
      </div>

      {/* 快捷操作 */}
      <div className="mt-8 flex flex-wrap gap-4">
        <Button variant="outline" size="sm" disabled>
          编辑资料
        </Button>
        <Button variant="outline" size="sm" disabled>
          更改头像
        </Button>
        <Button variant="outline" size="sm" disabled>
          导出数据
        </Button>
      </div>
    </div>
  )
}