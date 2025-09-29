import React, { useState, useEffect } from 'react'

interface InlineAnalysisProgressProps {
  isAnalyzing: boolean
  placeholderName: string
}

const progressStages = [
  { message: '正在获取数据库Schema信息...', duration: 5000 },
  { message: '正在生成SQL查询语句...', duration: 10000 },
  { message: '正在验证SQL语法和逻辑...', duration: 8000 },
  { message: '正在执行SQL测试...', duration: 7000 },
  { message: '正在保存分析结果...', duration: 3000 }
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
    <div className="bg-gray-50 border border-gray-200 rounded p-3">
      <div className="space-y-2">
        {/* 标题和状态 */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-800">
            正在分析占位符
          </span>
          <span className="text-xs text-gray-500">{Math.round(elapsedTime / 1000)}s</span>
        </div>

        {/* 当前阶段 */}
        <div className="text-xs text-gray-600">
          {currentStageInfo?.message || '处理中...'}
        </div>

        {/* 进度条 */}
        <div className="space-y-1">
          <div className="flex justify-between text-xs text-gray-500">
            <span>进度</span>
            <span>{Math.round(progress)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-1.5">
            <div
              className="bg-black h-1.5 rounded-full transition-all duration-500"
              style={{ width: `${progress}%` }}
            ></div>
          </div>
        </div>

        {/* 阶段指示器 */}
        <div className="flex justify-between">
          {progressStages.map((stage, index) => (
            <div
              key={index}
              className={`w-1.5 h-1.5 rounded-full ${
                index === currentStage
                  ? 'bg-black'
                  : index < currentStage
                  ? 'bg-gray-600'
                  : 'bg-gray-300'
              }`}
            ></div>
          ))}
        </div>

        {/* 提示信息 */}
        <div className="text-xs text-gray-500 text-center">
          这可能需要30-90秒，请耐心等待
        </div>
      </div>
    </div>
  )
}