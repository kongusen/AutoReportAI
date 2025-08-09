'use client'

import { useState, useRef, useEffect } from 'react'
import { Editor } from '@monaco-editor/react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Tabs, TabPanel, useTabsContext } from '@/components/ui/Tabs'
import { Badge } from '@/components/ui/Badge'
import { useTemplateStore } from '@/features/templates/templateStore'
import { cn } from '@/utils'

interface TemplateEditorProps {
  content: string
  onChange: (content: string) => void
  variables?: Record<string, any>
  onVariablesChange?: (variables: Record<string, any>) => void
  height?: number
  readOnly?: boolean
}

export function TemplateEditor({
  content,
  onChange,
  variables = {},
  onVariablesChange,
  height = 400,
  readOnly = false,
}: TemplateEditorProps) {
  const { previewTemplate, previewContent, loading } = useTemplateStore()
  const [selectedVariables, setSelectedVariables] = useState<string[]>([])
  const [newVariableName, setNewVariableName] = useState('')
  const [newVariableValue, setNewVariableValue] = useState('')
  const [previewMode, setPreviewMode] = useState<'code' | 'preview'>('code')
  const editorRef = useRef<any>(null)

  // 从模板内容中提取变量占位符
  const extractVariables = (templateContent: string): string[] => {
    // Updated regex to match both {{ variable }} and {{统计:描述}} or {{图表:描述}} formats
    const variablePattern = /\{\{\s*([^}]+?)\s*\}\}/g
    const matches: string[] = []
    let match
    while ((match = variablePattern.exec(templateContent)) !== null) {
      const placeholder = match[1].trim();
      // For complex placeholders like {{统计:描述}}, we still want to track them
      if (!matches.includes(placeholder)) {
        matches.push(placeholder)
      }
    }
    return matches
  }

  const templateVariables = extractVariables(content)

  useEffect(() => {
    // 自动添加新发现的变量到变量列表
    templateVariables.forEach(varName => {
      // For complex placeholders, we don't automatically add them as variables
      // Only add simple variable names (no colons)
      if (!varName.includes(':') && !variables.hasOwnProperty(varName)) {
        const updatedVariables = { ...variables, [varName]: '' }
        onVariablesChange?.(updatedVariables)
      }
    })
  }, [templateVariables])

  const handlePreview = async () => {
    if (!content.trim()) return
    
    try {
      await previewTemplate(content, variables)
      setPreviewMode('preview')
    } catch (error) {
      // 错误处理在store中已处理
    }
  }

  const handleVariableChange = (varName: string, value: string) => {
    const updatedVariables = { ...variables, [varName]: value }
    onVariablesChange?.(updatedVariables)
  }

  const addVariable = () => {
    if (!newVariableName.trim()) return
    
    const updatedVariables = { ...variables, [newVariableName]: newVariableValue }
    onVariablesChange?.(updatedVariables)
    setNewVariableName('')
    setNewVariableValue('')
  }

  const removeVariable = (varName: string) => {
    const updatedVariables = { ...variables }
    delete updatedVariables[varName]
    onVariablesChange?.(updatedVariables)
  }

  const insertVariable = (varName: string) => {
    if (editorRef.current) {
      const editor = editorRef.current
      const position = editor.getPosition()
      const range = {
        startLineNumber: position.lineNumber,
        startColumn: position.column,
        endLineNumber: position.lineNumber,
        endColumn: position.column,
      }
      editor.executeEdits('insert-variable', [{
        range,
        text: `{{ ${varName} }}`,
      }])
      editor.focus()
    }
  }

  const insertComplexPlaceholder = (type: string) => {
    if (editorRef.current) {
      const editor = editorRef.current
      const position = editor.getPosition()
      const range = {
        startLineNumber: position.lineNumber,
        startColumn: position.column,
        endLineNumber: position.lineNumber,
        endColumn: position.column,
      }
      editor.executeEdits('insert-placeholder', [{
        range,
        text: `{{${type}:请在此处描述需要生成的内容}}`,
      }])
      editor.focus()
    }
  }

  const tabItems = [
    { key: 'editor', label: '编辑器' },
    { key: 'variables', label: '变量管理' },
    { key: 'help', label: '帮助' },
  ]

  return (
    <div className="space-y-4">
      {/* 工具栏 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Button
            variant={previewMode === 'code' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setPreviewMode('code')}
          >
            编辑
          </Button>
          <Button
            variant={previewMode === 'preview' ? 'default' : 'outline'}
            size="sm"
            onClick={handlePreview}
            loading={loading}
          >
            预览
          </Button>
        </div>
        
        <div className="flex items-center space-x-2">
          {templateVariables.length > 0 && (
            <Badge variant="secondary">
              {templateVariables.length} 个占位符
            </Badge>
          )}
          <span className="text-sm text-gray-500">
            行: {content.split('\n').length} | 字符: {content.length}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 主编辑区域 */}
        <div className="lg:col-span-2">
          <Card>
            <CardContent className="p-0">
              {previewMode === 'code' ? (
                <Editor
                  height={height}
                  defaultLanguage="markdown"
                  value={content}
                  onChange={(value) => onChange(value || '')}
                  onMount={(editor) => { editorRef.current = editor }}
                  options={{
                    readOnly,
                    minimap: { enabled: false },
                    fontSize: 14,
                    lineNumbers: 'on',
                    scrollBeyondLastLine: false,
                    automaticLayout: true,
                    wordWrap: 'on',
                    theme: 'vs-light',
                  }}
                />
              ) : (
                <div 
                  className="p-4 prose prose-sm max-w-none"
                  style={{ height, overflow: 'auto' }}
                  dangerouslySetInnerHTML={{ __html: previewContent }}
                />
              )}
            </CardContent>
          </Card>
        </div>

        {/* 侧边栏 */}
        <div className="lg:col-span-1">
          <Tabs items={tabItems} defaultActiveKey="variables">
            <TabPanel value="variables" activeValue={useTabsContext().activeKey}>
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">变量管理</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* 模板中的变量 */}
                  {templateVariables.length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-gray-700 mb-2">
                        模板占位符
                      </h4>
                      <div className="space-y-2">
                        {templateVariables.map((varName) => (
                          <div key={varName} className="space-y-1">
                            <label className="text-sm text-gray-600">
                              {varName}
                            </label>
                            {!varName.includes(':') && (
                              <Input
                                size={'sm' as any}
                                placeholder={`输入 ${varName} 的值`}
                                value={variables[varName] || ''}
                                onChange={(e) => handleVariableChange(varName, e.target.value)}
                              />
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 添加新变量 */}
                  <div>
                    <h4 className="text-sm font-medium text-gray-700 mb-2">
                      添加变量
                    </h4>
                    <div className="space-y-2">
                      <Input
                        size={'sm' as any}
                        placeholder="变量名"
                        value={newVariableName}
                        onChange={(e) => setNewVariableName(e.target.value)}
                      />
                      <Input
                        size={'sm' as any}
                        placeholder="默认值"
                        value={newVariableValue}
                        onChange={(e) => setNewVariableValue(e.target.value)}
                      />
                      <Button
                        size={'sm' as any}
                        className="w-full"
                        onClick={addVariable}
                        disabled={!newVariableName.trim()}
                      >
                        添加变量
                      </Button>
                    </div>
                  </div>

                  {/* 变量插入快捷按钮 */}
                  <div>
                    <h4 className="text-sm font-medium text-gray-700 mb-2">
                      快速插入
                    </h4>
                    <div className="flex flex-wrap gap-1">
                      {Object.keys(variables).map((varName) => (
                        <Button
                          key={varName}
                          size="sm"
                          variant="outline"
                          onClick={() => insertVariable(varName)}
                        >
                          {varName}
                        </Button>
                      ))}
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => insertComplexPlaceholder('统计')}
                      >
                        统计
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => insertComplexPlaceholder('图表')}
                      >
                        图表
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabPanel>

            <TabPanel value="help" activeValue={useTabsContext().activeKey}>
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">语法帮助</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <h4 className="text-sm font-medium text-gray-700 mb-2">
                      变量语法
                    </h4>
                    <div className="text-sm text-gray-600 space-y-1">
                      <p><code className="bg-gray-100 px-1 rounded">{'{{ variable_name }}'}</code></p>
                      <p className="text-xs">使用双大括号包围变量名</p>
                    </div>
                  </div>

                  <div>
                    <h4 className="text-sm font-medium text-gray-700 mb-2">
                      智能占位符语法
                    </h4>
                    <div className="text-sm text-gray-600 space-y-1">
                      <p><code className="bg-gray-100 px-1 rounded">{'{{统计:描述统计需求}}'}</code></p>
                      <p><code className="bg-gray-100 px-1 rounded">{'{{图表:描述图表需求}}'}</code></p>
                      <p className="text-xs">系统将根据描述自动生成统计分析或图表</p>
                    </div>
                  </div>

                  <div>
                    <h4 className="text-sm font-medium text-gray-700 mb-2">
                      Markdown支持
                    </h4>
                    <div className="text-sm text-gray-600 space-y-1">
                      <p><code className="bg-gray-100 px-1 rounded"># 标题</code></p>
                      <p><code className="bg-gray-100 px-1 rounded">**粗体**</code></p>
                      <p><code className="bg-gray-100 px-1 rounded">*斜体*</code></p>
                      <p><code className="bg-gray-100 px-1 rounded">[链接](url)</code></p>
                      <p><code className="bg-gray-100 px-1 rounded">- 列表项</code></p>
                    </div>
                  </div>

                  <div>
                    <h4 className="text-sm font-medium text-gray-700 mb-2">
                      表格语法
                    </h4>
                    <div className="text-sm text-gray-600">
                      <pre className="bg-gray-100 p-2 rounded text-xs">
{`| 列1 | 列2 |
|-----|-----|
| 值1 | 值2 |`}
                      </pre>
                    </div>
                  </div>

                  <div>
                    <h4 className="text-sm font-medium text-gray-700 mb-2">
                      常用变量
                    </h4>
                    <div className="text-xs text-gray-600 space-y-1">
                      <p>• date - 当前日期</p>
                      <p>• time - 当前时间</p>
                      <p>• user - 当前用户</p>
                      <p>• title - 报告标题</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabPanel>
          </Tabs>
        </div>
      </div>
    </div>
  )
}