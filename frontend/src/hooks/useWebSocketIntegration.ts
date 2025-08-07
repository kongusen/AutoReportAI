'use client'

import { useEffect } from 'react'
import { useWebSocket } from '@/components/providers/WebSocketProvider'
import { useTaskStore } from '@/stores/taskStore'
import { useReportStore } from '@/stores/reportStore'
import { TaskProgress, SystemNotificationMessage, ReportCompletedMessage } from '@/types'
import toast from 'react-hot-toast'

export function useWebSocketIntegration() {
  const { wsManager, isConnected, connectionState } = useWebSocket()
  const { updateTaskProgress } = useTaskStore()
  const { addReport, updateReportStatus } = useReportStore()

  useEffect(() => {
    if (!wsManager) return

    // 注册任务进度更新处理器
    const handleTaskProgress = (progress: TaskProgress) => {
      updateTaskProgress(progress)
      
      // 显示进度通知
      if (progress.status === 'completed') {
        toast.success(`任务 "${progress.task_id}" 执行完成`)
      } else if (progress.status === 'failed') {
        toast.error(`任务 "${progress.task_id}" 执行失败`)
      }
    }

    // 注册系统通知处理器
    const handleSystemNotification = (notification: SystemNotificationMessage['payload']) => {
      switch (notification.level) {
        case 'success':
          toast.success(notification.message)
          break
        case 'error':
          toast.error(notification.message)
          break
        case 'warning':
          toast((t) => (
            <div className="flex items-center">
              <div className="flex-1">
                <p className="font-medium">{notification.title}</p>
                <p className="text-sm text-gray-600">{notification.message}</p>
              </div>
              {notification.action && (
                <a
                  href={notification.action.url}
                  className="ml-3 text-sm font-medium text-blue-600 hover:text-blue-500"
                  onClick={() => toast.dismiss(t.id)}
                >
                  {notification.action.label}
                </a>
              )}
            </div>
          ), {
            duration: 6000,
            style: {
              background: '#fef3c7',
              color: '#92400e',
              border: '1px solid #fcd34d',
            },
          })
          break
        default:
          toast(notification.message)
      }
    }

    // 注册报告完成处理器
    const handleReportCompleted = (report: ReportCompletedMessage['payload']) => {
      // 添加到报告列表
      addReport(report)
      
      // 显示完成通知
      toast.success(
        (t) => (
          <div className="flex items-center">
            <div className="flex-1">
              <p className="font-medium">报告生成完成</p>
              <p className="text-sm text-gray-600">{report.name}</p>
            </div>
            <button
              className="ml-3 text-sm font-medium text-blue-600 hover:text-blue-500"
              onClick={() => {
                toast.dismiss(t.id)
                window.location.href = `/reports/${report.id}`
              }}
            >
              查看
            </button>
          </div>
        ),
        {
          duration: 8000,
        }
      )
    }

    // 注册消息处理器
    wsManager.on('task_progress', handleTaskProgress)
    wsManager.on('system_notification', handleSystemNotification)
    wsManager.on('report_completed', handleReportCompleted)

    // 清理函数
    return () => {
      wsManager.off('task_progress')
      wsManager.off('system_notification')
      wsManager.off('report_completed')
    }
  }, [wsManager, updateTaskProgress, addReport, updateReportStatus])

  return {
    isConnected,
    connectionState,
  }
}