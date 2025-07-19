'use client'

import React, { useState, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { 
  MessageSquare,
  Send,
  Bot,
  User,
  Lightbulb,
  HelpCircle,
  Zap,
  RefreshCw,
  ThumbsUp,
  ThumbsDown,
  Copy,
  Loader2
} from 'lucide-react'
import { Textarea } from '@/components/ui/textarea'
import apiClient from '@/lib/api-client'

// Types
interface Message {
  id: string
  type: 'user' | 'assistant'
  content: string
  timestamp: Date
  metadata?: {
    suggestions?: string[]
    confidence?: number
    context?: string
  }
}

interface AIAssistantProps {
  context?: {
    templateId?: string
    dataSourceId?: number
    placeholders?: any[]
    currentTask?: string
  }
  onSuggestionApply?: (suggestion: string) => void
}

export function AIAssistant({ context, onSuggestionApply }: AIAssistantProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputMessage, setInputMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isTyping, setIsTyping] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Predefined quick questions
  const quickQuestions = [
    "如何优化占位符的匹配准确率？",
    "这个数据源适合什么类型的报告？",
    "如何处理字段匹配置信度较低的情况？",
    "推荐的模板结构是什么？"
  ]

  // Initialize with welcome message
  useEffect(() => {
    const welcomeMessage: Message = {
      id: 'welcome',
      type: 'assistant',
      content: '您好！我是智能占位符助手。我可以帮助您：\n\n• 优化占位符匹配\n• 解释字段映射结果\n• 提供模板建议\n• 解答技术问题\n\n有什么我可以帮助您的吗？',
      timestamp: new Date(),
      metadata: {
        suggestions: quickQuestions
      }
    }
    setMessages([welcomeMessage])
  }, [])

  // Auto scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Send message
  const sendMessage = async (content?: string) => {
    const messageContent = content || inputMessage.trim()
    if (!messageContent) return

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: messageContent,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInputMessage('')
    setIsLoading(true)
    setIsTyping(true)

    try {
      // Simulate AI response (replace with actual API call)
      await new Promise(resolve => setTimeout(resolve, 1500))
      
      const assistantResponse = await generateAIResponse(messageContent, context)
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: assistantResponse.content,
        timestamp: new Date(),
        metadata: assistantResponse.metadata
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      console.error('Failed to get AI response:', error)
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: '抱歉，我暂时无法回答您的问题。请稍后再试。',
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
      setIsTyping(false)
    }
  }

  // Generate AI response (mock implementation)
  const generateAIResponse = async (userMessage: string, context?: any) => {
    // This would be replaced with actual AI API call
    const responses = {
      "如何优化占位符的匹配准确率？": {
        content: "要优化占位符匹配准确率，建议：\n\n1. **完善占位符描述**：使用清晰、具体的描述，避免歧义\n2. **提供充足上下文**：确保占位符前后有足够的上下文信息\n3. **选择合适的数据源**：确保数据源包含相关字段\n4. **调整置信度阈值**：根据实际需求调整匹配阈值\n5. **使用标准化格式**：遵循{{类型:描述}}的标准格式",
        metadata: {
          suggestions: [
            "调整置信度阈值到0.8",
            "启用上下文分析",
            "检查数据源字段完整性"
          ],
          confidence: 0.95
        }
      },
      "这个数据源适合什么类型的报告？": {
        content: "基于当前数据源的结构分析，它适合生成：\n\n• **统计分析报告**：包含数值统计和趋势分析\n• **区域分布报告**：地理位置相关的数据分析\n• **时间序列报告**：基于时间维度的数据变化\n\n建议使用包含统计类型占位符的模板，如{{统计:总数}}、{{区域:主要地区}}等。",
        metadata: {
          suggestions: [
            "创建统计分析模板",
            "添加区域分析占位符",
            "设置时间维度筛选"
          ],
          confidence: 0.88
        }
      }
    }

    // Default response for unrecognized questions
    const defaultResponse = {
      content: `我理解您的问题："${userMessage}"。\n\n基于当前上下文，我建议：\n\n1. 检查占位符格式是否正确\n2. 确认数据源连接状态\n3. 验证字段映射关系\n\n如果问题持续存在，请提供更多详细信息，我会为您提供更精确的帮助。`,
      metadata: {
        suggestions: [
          "检查占位符格式",
          "测试数据源连接",
          "查看详细错误日志"
        ],
        confidence: 0.7
      }
    }

    return responses[userMessage as keyof typeof responses] || defaultResponse
  }

  // Handle key press
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  // Copy message content
  const copyMessage = (content: string) => {
    navigator.clipboard.writeText(content)
    // Could add a toast notification here
  }

  // Rate message
  const rateMessage = (messageId: string, rating: 'up' | 'down') => {
    // This would send feedback to improve AI responses
    console.log(`Message ${messageId} rated: ${rating}`)
  }

  return (
    <Card className="h-[600px] flex flex-col">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center">
          <Bot className="w-5 h-5 mr-2 text-blue-600" />
          AI智能助手
        </CardTitle>
        <CardDescription>
          获取智能占位符处理的专业建议和帮助
        </CardDescription>
      </CardHeader>
      
      <CardContent className="flex-1 flex flex-col p-0">
        {/* Messages Area */}
        <ScrollArea className="flex-1 px-4">
          <div className="space-y-4 pb-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div className={`max-w-[80%] ${message.type === 'user' ? 'order-2' : 'order-1'}`}>
                  <div className="flex items-start space-x-2">
                    {message.type === 'assistant' && (
                      <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
                        <Bot className="w-4 h-4 text-blue-600" />
                      </div>
                    )}
                    
                    <div className={`rounded-lg p-3 ${
                      message.type === 'user' 
                        ? 'bg-blue-600 text-white' 
                        : 'bg-gray-100 text-gray-900'
                    }`}>
                      <div className="whitespace-pre-wrap text-sm">
                        {message.content}
                      </div>
                      
                      {/* Message metadata */}
                      {message.metadata?.confidence && (
                        <div className="mt-2 flex items-center space-x-2">
                          <Badge variant="outline" className="text-xs">
                            置信度: {(message.metadata.confidence * 100).toFixed(0)}%
                          </Badge>
                        </div>
                      )}
                      
                      {/* Suggestions */}
                      {message.metadata?.suggestions && (
                        <div className="mt-3 space-y-1">
                          <p className="text-xs font-medium opacity-75">建议操作:</p>
                          {message.metadata.suggestions.map((suggestion, index) => (
                            <Button
                              key={index}
                              variant="outline"
                              size="sm"
                              className="text-xs h-6 mr-1 mb-1"
                              onClick={() => onSuggestionApply?.(suggestion)}
                            >
                              <Zap className="w-3 h-3 mr-1" />
                              {suggestion}
                            </Button>
                          ))}
                        </div>
                      )}
                      
                      {/* Message actions */}
                      {message.type === 'assistant' && (
                        <div className="mt-2 flex items-center space-x-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 px-2 text-xs"
                            onClick={() => copyMessage(message.content)}
                          >
                            <Copy className="w-3 h-3" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 px-2 text-xs"
                            onClick={() => rateMessage(message.id, 'up')}
                          >
                            <ThumbsUp className="w-3 h-3" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 px-2 text-xs"
                            onClick={() => rateMessage(message.id, 'down')}
                          >
                            <ThumbsDown className="w-3 h-3" />
                          </Button>
                        </div>
                      )}
                    </div>
                    
                    {message.type === 'user' && (
                      <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center flex-shrink-0">
                        <User className="w-4 h-4 text-gray-600" />
                      </div>
                    )}
                  </div>
                  
                  <div className={`text-xs text-gray-500 mt-1 ${
                    message.type === 'user' ? 'text-right' : 'text-left ml-10'
                  }`}>
                    {message.timestamp.toLocaleTimeString()}
                  </div>
                </div>
              </div>
            ))}
            
            {/* Typing indicator */}
            {isTyping && (
              <div className="flex justify-start">
                <div className="flex items-start space-x-2">
                  <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                    <Bot className="w-4 h-4 text-blue-600" />
                  </div>
                  <div className="bg-gray-100 rounded-lg p-3">
                    <div className="flex space-x-1">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                    </div>
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>
        
        {/* Quick Questions */}
        {messages.length === 1 && (
          <div className="px-4 py-2 border-t">
            <p className="text-sm font-medium mb-2">常见问题:</p>
            <div className="flex flex-wrap gap-2">
              {quickQuestions.map((question, index) => (
                <Button
                  key={index}
                  variant="outline"
                  size="sm"
                  className="text-xs h-7"
                  onClick={() => sendMessage(question)}
                >
                  <HelpCircle className="w-3 h-3 mr-1" />
                  {question}
                </Button>
              ))}
            </div>
          </div>
        )}
        
        {/* Input Area */}
        <div className="p-4 border-t">
          <div className="flex space-x-2">
            <Textarea
              ref={inputRef}
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="输入您的问题..."
              className="flex-1 min-h-[40px] max-h-[120px] resize-none"
              disabled={isLoading}
            />
            <Button
              onClick={() => sendMessage()}
              disabled={!inputMessage.trim() || isLoading}
              className="px-3"
            >
              {isLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </Button>
          </div>
          
          <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
            <span>按 Enter 发送，Shift + Enter 换行</span>
            {context && (
              <Badge variant="outline" className="text-xs">
                上下文: {context.templateId ? '模板' : ''} {context.dataSourceId ? '数据源' : ''}
              </Badge>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}