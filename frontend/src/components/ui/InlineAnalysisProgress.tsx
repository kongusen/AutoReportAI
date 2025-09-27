import React, { useState, useEffect } from 'react'
import { BeakerIcon, ClockIcon } from '@heroicons/react/24/outline'

interface InlineAnalysisProgressProps {
  isAnalyzing: boolean
  placeholderName: string
}

const progressStages = [
  { message: '正在获取数据库Schema信息...', duration: 5000, icon: '🔍' },
  { message: '正在生成SQL查询语句...', duration: 10000, icon: '⚙️' },
  { message: '正在验证SQL语法和逻辑...', duration: 8000, icon: '✅' },
  { message: '正在执行SQL测试...', duration: 7000, icon: '🚀' },
  { message: '正在保存分析结果...', duration: 3000, icon: '💾' }
]

export const InlineAnalysisProgress: React.FC<InlineAnalysisProgressProps> = ({
  isAnalyzing,
  placeholderName
}) => {
  const [currentStage, setCurrentStage] = useState(0)
  const [progress, setProgress] = useState(0)
  const [elapsedTime, setElapsedTime] = useState(0)

  useEffect(() => {
    if (!isAnalyzing) {
      setCurrentStage(0)
      setProgress(0)
      setElapsedTime(0)
      return
    }

    const startTime = Date.now()
    let stageIndex = 0
    let stageStartTime = startTime

    const interval = setInterval(() => {
      const now = Date.now()
      const totalElapsed = now - startTime
      const stageElapsed = now - stageStartTime

      setElapsedTime(totalElapsed)

      // 检查是否需要切换到下一阶段
      if (stageIndex < progressStages.length - 1 &&
          stageElapsed >= progressStages[stageIndex].duration) {
        stageIndex++
        stageStartTime = now
        setCurrentStage(stageIndex)
      }

      // 计算总进度
      const stageProgress = Math.min(
        (stageElapsed / progressStages[stageIndex].duration) * 100,
        100
      )
      const baseProgress = (stageIndex / progressStages.length) * 100
      const totalProgress = baseProgress + (stageProgress / progressStages.length)

      setProgress(Math.min(totalProgress, 95)) // 最多到95%，留5%给实际完成
    }, 500)

    return () => clearInterval(interval)
  }, [isAnalyzing])

  if (!isAnalyzing) return null

  const currentStageInfo = progressStages[currentStage]

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
      <div className="space-y-3">
        {/* 标题和状态 */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <BeakerIcon className="w-4 h-4 text-blue-600 animate-bounce" />
            <span className="text-sm font-medium text-blue-800">
              正在分析占位符
            </span>
          </div>
          <div className="flex items-center space-x-1 text-xs text-blue-600">
            <ClockIcon className="w-3 h-3" />
            <span>{Math.round(elapsedTime / 1000)}s</span>
          </div>
        </div>

        {/* 当前阶段 */}
        <div className="flex items-center space-x-2">
          <span className="text-lg">{currentStageInfo?.icon || '⏳'}</span>
          <span className="text-sm text-blue-700">
            {currentStageInfo?.message || '处理中...'}
          </span>
        </div>

        {/* 进度条 */}
        <div className="space-y-2">
          <div className="flex justify-between text-xs text-blue-600">
            <span>进度</span>
            <span>{Math.round(progress)}%</span>
          </div>
          <div className="w-full bg-blue-100 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-500 relative overflow-hidden"
              style={{ width: `${progress}%` }}
            >
              {/* 动态光效 */}
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white to-transparent opacity-30 animate-pulse"></div>
            </div>
          </div>
        </div>

        {/* 阶段指示器 */}
        <div className="flex justify-between">
          {progressStages.map((stage, index) => (
            <div
              key={index}
              className={`flex flex-col items-center space-y-1 ${
                index <= currentStage ? 'text-blue-600' : 'text-gray-400'
              }`}
            >
              <div
                className={`w-2 h-2 rounded-full ${
                  index === currentStage
                    ? 'bg-blue-600 animate-pulse'
                    : index < currentStage
                    ? 'bg-blue-600'
                    : 'bg-gray-300'
                }`}
              ></div>
              <span className="text-xs hidden sm:block">
                {stage.icon}
              </span>
            </div>
          ))}
        </div>

        {/* 提示信息 */}
        <div className="text-xs text-blue-600 text-center bg-blue-100 rounded px-2 py-1">
          💡 这可能需要30-90秒，请耐心等待...
        </div>
      </div>
    </div>
  )
}