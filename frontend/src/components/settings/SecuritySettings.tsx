'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/Button'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import toast from 'react-hot-toast'
import { SettingsService } from '@/services/settingsService'
import { EyeIcon, EyeSlashIcon } from '@heroicons/react/24/outline'

export function SecuritySettings() {
  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  })
  const [showPasswords, setShowPasswords] = useState({
    current: false,
    new: false,
    confirm: false
  })
  const [isChangingPassword, setIsChangingPassword] = useState(false)

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      toast.error('新密码确认不匹配')
      return
    }

    if (passwordForm.new_password.length < 8) {
      toast.error('密码长度至少8位')
      return
    }

    setIsChangingPassword(true)
    
    try {
      await SettingsService.changePassword({
        current_password: passwordForm.current_password,
        new_password: passwordForm.new_password
      })
      toast.success('密码修改成功')
      setPasswordForm({
        current_password: '',
        new_password: '',
        confirm_password: ''
      })
    } catch (error) {
      toast.error('密码修改失败')
    } finally {
      setIsChangingPassword(false)
    }
  }

  const togglePasswordVisibility = (field: 'current' | 'new' | 'confirm') => {
    setShowPasswords(prev => ({
      ...prev,
      [field]: !prev[field]
    }))
  }

  const handleLogoutAllDevices = async () => {
    if (!confirm('确定要登出所有设备吗？您需要重新登录。')) return
    
    try {
      await SettingsService.logoutAllDevices()
      toast.success('已登出所有设备')
    } catch (error) {
      toast.error('操作失败')
    }
  }

  const downloadAccountData = async () => {
    try {
      await SettingsService.exportAccountData()
      toast.success('数据导出请求已提交，完成后将通过邮件发送下载链接')
    } catch (error) {
      toast.error('导出失败')
    }
  }

  const deleteAccount = async () => {
    const confirmation = prompt('删除账户是不可逆的操作。请输入 "DELETE" 来确认删除账户：')
    if (confirmation !== 'DELETE') return
    
    try {
      await SettingsService.deleteAccount()
      toast.success('账户删除请求已提交')
    } catch (error) {
      toast.error('删除失败')
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900">安全设置</h3>
        <p className="mt-1 text-sm text-gray-600">
          管理您的账户安全和隐私设置
        </p>
      </div>

      {/* 密码修改 */}
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="text-md font-medium text-gray-900 mb-4">修改密码</h4>
        <form onSubmit={handlePasswordSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">
              当前密码
            </label>
            <div className="mt-1 relative">
              <input
                type={showPasswords.current ? 'text' : 'password'}
                value={passwordForm.current_password}
                onChange={(e) => setPasswordForm(prev => ({ ...prev, current_password: e.target.value }))}
                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 pr-10"
                required
              />
              <button
                type="button"
                className="absolute inset-y-0 right-0 pr-3 flex items-center"
                onClick={() => togglePasswordVisibility('current')}
              >
                {showPasswords.current ? (
                  <EyeSlashIcon className="h-5 w-5 text-gray-400" />
                ) : (
                  <EyeIcon className="h-5 w-5 text-gray-400" />
                )}
              </button>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">
              新密码
            </label>
            <div className="mt-1 relative">
              <input
                type={showPasswords.new ? 'text' : 'password'}
                value={passwordForm.new_password}
                onChange={(e) => setPasswordForm(prev => ({ ...prev, new_password: e.target.value }))}
                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 pr-10"
                minLength={8}
                required
              />
              <button
                type="button"
                className="absolute inset-y-0 right-0 pr-3 flex items-center"
                onClick={() => togglePasswordVisibility('new')}
              >
                {showPasswords.new ? (
                  <EyeSlashIcon className="h-5 w-5 text-gray-400" />
                ) : (
                  <EyeIcon className="h-5 w-5 text-gray-400" />
                )}
              </button>
            </div>
            <p className="mt-1 text-sm text-gray-500">
              密码长度至少8位，建议包含字母、数字和特殊字符
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">
              确认新密码
            </label>
            <div className="mt-1 relative">
              <input
                type={showPasswords.confirm ? 'text' : 'password'}
                value={passwordForm.confirm_password}
                onChange={(e) => setPasswordForm(prev => ({ ...prev, confirm_password: e.target.value }))}
                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 pr-10"
                required
              />
              <button
                type="button"
                className="absolute inset-y-0 right-0 pr-3 flex items-center"
                onClick={() => togglePasswordVisibility('confirm')}
              >
                {showPasswords.confirm ? (
                  <EyeSlashIcon className="h-5 w-5 text-gray-400" />
                ) : (
                  <EyeIcon className="h-5 w-5 text-gray-400" />
                )}
              </button>
            </div>
          </div>

          <div className="flex justify-end">
            <Button 
              type="submit" 
              disabled={isChangingPassword}
              className="inline-flex items-center"
            >
              {isChangingPassword && <LoadingSpinner className="w-4 h-4 mr-2" />}
              修改密码
            </Button>
          </div>
        </form>
      </div>

      {/* 会话管理 */}
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="text-md font-medium text-gray-900 mb-4">会话管理</h4>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-700">
              登出所有设备
            </p>
            <p className="text-sm text-gray-500">
              强制登出所有已登录的设备，您需要重新登录
            </p>
          </div>
          <Button
            variant="outline"
            onClick={handleLogoutAllDevices}
          >
            登出所有设备
          </Button>
        </div>
      </div>

      {/* 数据管理 */}
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="text-md font-medium text-gray-900 mb-4">数据管理</h4>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-700">
                导出账户数据
              </p>
              <p className="text-sm text-gray-500">
                下载您的所有数据副本
              </p>
            </div>
            <Button
              variant="outline"
              onClick={downloadAccountData}
            >
              导出数据
            </Button>
          </div>

          <div className="flex items-center justify-between pt-4 border-t border-gray-200">
            <div>
              <p className="text-sm font-medium text-red-700">
                删除账户
              </p>
              <p className="text-sm text-gray-500">
                永久删除您的账户和所有数据，此操作不可逆
              </p>
            </div>
            <Button
              variant="outline"
              onClick={deleteAccount}
              className="text-red-600 hover:text-red-700 hover:bg-red-50 border-red-300"
            >
              删除账户
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}