import React, { useState, useEffect } from 'react'

interface AnalysisProgressProps {
  isAnalyzing: boolean
  onCancel?: () => void
}

const progressStages = [
  { message: '正在获取数据库Schema信息...', duration: 5000 },
  { message: '正在生成SQL查询语句...', duration: 10000 },
  { message: '正在验证SQL语法和逻辑...', duration: 8000 },
  { message: '正在执行SQL测试...', duration: 7000 },
  { message: '正在保存分析结果...', duration: 3000 }
]

export const AnalysisProgress: React.FC<AnalysisProgressProps> = ({
  isAnalyzing,
  onCancel
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

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>

          <h3 className="text-lg font-medium text-gray-900 mb-2">
            正在分析占位符
          </h3>

          <p className="text-sm text-gray-600 mb-4">
            {progressStages[currentStage]?.message || '处理中...'}
          </p>

          {/* 进度条 */}
          <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-500"
              style={{ width: `${progress}%` }}
            ></div>
          </div>

          <div className="flex justify-between text-xs text-gray-500 mb-4">
            <span>{Math.round(progress)}%</span>
            <span>{Math.round(elapsedTime / 1000)}s</span>
          </div>

          <p className="text-xs text-gray-400 mb-4">
            这可能需要30-60秒，请耐心等待...
          </p>

          {onCancel && (
            <button
              onClick={onCancel}
              className="text-gray-400 hover:text-gray-600 text-sm"
            >
              取消分析
            </button>
          )}
        </div>
      </div>
    </div>
  )
}