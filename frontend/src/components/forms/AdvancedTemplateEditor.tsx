'use client'

import React, { useState, useEffect, useRef, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Switch } from '@/components/ui/switch'
import { ScrollArea } from '@/components/ui/scroll-area'
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle, 
  DialogTrigger,
  DialogFooter 
} from '@/components/ui/dialog'
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { 
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { 
  Save, 
  Plus, 
  Trash2, 
  FileText, 
  Code, 
  Settings,
  Download,
  Upload,
  Copy,
  Undo,
  Redo,
  Search,
  Replace,
  Palette,
  Layout,
  Type,
  Image,
  BarChart3,
  Calendar,
  Hash,
  AlignLeft,
  Eye,
  EyeOff,
  Maximize2,
  Minimize2
} from 'lucide-react'
import api from '@/lib/api'

interface AdvancedPlaceholder {
  id: string
  name: string
  type: 'text' | 'number' | 'date' | 'table' | 'chart' | 'image' | 'formula' | 'conditional'
  description?: string
  default_value?: string
  required: boolean
  format?: string
  validation?: {
    min?: number
    max?: number
    pattern?: string
    options?: string[]
  }
  conditional_logic?: {
    condition: string
    show_if: string
    hide_if: string
  }
  styling?: {
    font_size?: string
    font_weight?: string
    color?: string
    background_color?: string
    alignment?: 'left' | 'center' | 'right'
  }
}

interface TemplateVersion {
  id: string
  version: number
  content: string
  placeholders: AdvancedPlaceholder[]
  created_at: string
  description?: string
}

interface AdvancedTemplateEditorProps {
  templateId?: string
  onSave?: (template: unknown) => void
  onCancel?: () => void
}

export function AdvancedTemplateEditor({ templateId, onSave, onCancel }: AdvancedTemplateEditorProps) {
  const [template, setTemplate] = useState({
    id: '',
    name: '',
    description: '',
    content: '',
    template_type: 'docx',
    placeholders: [] as AdvancedPlaceholder[],
    is_public: false,
    created_at: new Date().toISOString(),
    versions: [] as TemplateVersion[]
  })
  
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [previewMode, setPreviewMode] = useState(false)
  const [fullscreenMode, setFullscreenMode] = useState(false)
  const [showPlaceholderPanel, setShowPlaceholderPanel] = useState(true)
  const [selectedPlaceholder, setSelectedPlaceholder] = useState<AdvancedPlaceholder | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [replaceTerm, setReplaceTerm] = useState('')
  const [undoStack, setUndoStack] = useState<string[]>([])
  const [redoStack, setRedoStack] = useState<string[]>([])
  
  const editorRef = useRef<HTMLTextAreaElement>(null)
  const [cursorPosition, setCursorPosition] = useState(0)

  // 自动保存功能
  useEffect(() => {
    const autoSaveInterval = setInterval(() => {
      if (template.content && !saving) {
        handleAutoSave()
      }
    }, 30000) // 每30秒自动保存

    return () => clearInterval(autoSaveInterval)
  }, [template.content, saving])

  const handleAutoSave = async () => {
    try {
      await api.post('/templates/auto-save', {
        id: templateId,
        content: template.content,
        placeholders: template.placeholders
      })
    } catch (error) {
      console.error('Auto-save failed:', error)
    }
  }

  const handleUndo = () => {
    if (undoStack.length > 0) {
      const previousContent = undoStack[undoStack.length - 1]
      setRedoStack(prev => [...prev, template.content])
      setUndoStack(prev => prev.slice(0, -1))
      setTemplate(prev => ({ ...prev, content: previousContent }))
    }
  }

  const handleRedo = () => {
    if (redoStack.length > 0) {
      const nextContent = redoStack[redoStack.length - 1]
      setUndoStack(prev => [...prev, template.content])
      setRedoStack(prev => prev.slice(0, -1))
      setTemplate(prev => ({ ...prev, content: nextContent }))
    }
  }

  const handleContentChange = (newContent: string) => {
    // 添加到撤销栈
    if (template.content !== newContent) {
      setUndoStack(prev => [...prev.slice(-19), template.content]) // 保留最近20个状态
      setRedoStack([]) // 清空重做栈
    }
    
    setTemplate(prev => ({ ...prev, content: newContent }))
  }

  return (
    <div className={`${fullscreenMode ? 'fixed inset-0 z-50 bg-white' : ''}`}>
      <div className="space-y-6 p-6">
        {/* 工具栏 */}
        <div className="flex items-center justify-between border-b pb-4">
          <div className="flex items-center space-x-2">
            <h1 className="text-2xl font-bold">
              {templateId ? 'Edit Template' : 'Create Template'}
            </h1>
            <Badge variant="outline">{template.template_type}</Badge>
          </div>
          
          <div className="flex items-center space-x-2">
            {/* 撤销/重做 */}
            <Button
              variant="outline"
              size="sm"
              onClick={handleUndo}
              disabled={undoStack.length === 0}
            >
              <Undo className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRedo}
              disabled={redoStack.length === 0}
            >
              <Redo className="h-4 w-4" />
            </Button>
            
            {/* 查找替换 */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm">
                  <Search className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent className="w-80">
                <div className="p-4 space-y-3">
                  <div>
                    <Label>Search</Label>
                    <Input
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      placeholder="Find in template..."
                    />
                  </div>
                  <div>
                    <Label>Replace</Label>
                    <Input
                      value={replaceTerm}
                      onChange={(e) => setReplaceTerm(e.target.value)}
                      placeholder="Replace with..."
                    />
                  </div>
                  <div className="flex space-x-2">
                    <Button size="sm" variant="outline">Find</Button>
                    <Button size="sm" variant="outline">Replace</Button>
                    <Button size="sm" variant="outline">Replace All</Button>
                  </div>
                </div>
              </DropdownMenuContent>
            </DropdownMenu>
            
            {/* 视图控制 */}
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPreviewMode(!previewMode)}
            >
              {previewMode ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </Button>
            
            <Button
              variant="outline"
              size="sm"
              onClick={() => setFullscreenMode(!fullscreenMode)}
            >
              {fullscreenMode ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
            </Button>
            
            {/* 保存按钮 */}
            <Button onClick={() => {}} disabled={saving}>
              <Save className="w-4 h-4 mr-2" />
              {saving ? 'Saving...' : 'Save'}
            </Button>
            
            {onCancel && (
              <Button variant="outline" onClick={onCancel}>
                Cancel
              </Button>
            )}
          </div>
        </div>

        {/* 主编辑区域 */}
        <div className="grid grid-cols-12 gap-6 h-[calc(100vh-200px)]">
          {/* 左侧面板 - 占位符管理 */}
          {showPlaceholderPanel && (
            <div className="col-span-3">
              <Card className="h-full">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">Placeholders</CardTitle>
                    <Button size="sm" variant="outline">
                      <Plus className="h-4 w-4" />
                    </Button>
                  </div>
                </CardHeader>
                <CardContent className="p-0">
                  <ScrollArea className="h-[calc(100vh-300px)]">
                    <div className="p-4 space-y-3">
                      {template.placeholders.map((placeholder) => (
                        <div
                          key={placeholder.id}
                          className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                            selectedPlaceholder?.id === placeholder.id
                              ? 'border-blue-500 bg-blue-50'
                              : 'hover:bg-gray-50'
                          }`}
                          onClick={() => setSelectedPlaceholder(placeholder)}
                        >
                          <div className="flex items-center justify-between mb-2">
                            <Badge variant="outline" className="text-xs">
                              {placeholder.type}
                            </Badge>
                            {placeholder.required && (
                              <Badge variant="destructive" className="text-xs">
                                Required
                              </Badge>
                            )}
                          </div>
                          <p className="font-medium text-sm">{placeholder.name}</p>
                          {placeholder.description && (
                            <p className="text-xs text-gray-500 mt-1">
                              {placeholder.description}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                </CardContent>
              </Card>
            </div>
          )}

          {/* 中间编辑器 */}
          <div className={showPlaceholderPanel ? 'col-span-6' : 'col-span-9'}>
            <Card className="h-full">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg">Template Content</CardTitle>
                  <div className="flex items-center space-x-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setShowPlaceholderPanel(!showPlaceholderPanel)}
                    >
                      <Layout className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="p-0">
                {previewMode ? (
                  <ScrollArea className="h-[calc(100vh-300px)]">
                    <div className="p-4 prose max-w-none">
                      <div dangerouslySetInnerHTML={{ __html: template.content }} />
                    </div>
                  </ScrollArea>
                ) : (
                  <Textarea
                    ref={editorRef}
                    value={template.content}
                    onChange={(e) => handleContentChange(e.target.value)}
                    className="h-[calc(100vh-300px)] resize-none border-0 focus:ring-0 font-mono text-sm"
                    placeholder="Enter your template content here..."
                    onSelect={(e) => {
                      const target = e.target as HTMLTextAreaElement
                      setCursorPosition(target.selectionStart)
                    }}
                  />
                )}
              </CardContent>
            </Card>
          </div>

          {/* 右侧面板 - 属性和设置 */}
          <div className="col-span-3">
            <Card className="h-full">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg">Properties</CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[calc(100vh-300px)]">
                  <Tabs defaultValue="template" className="w-full">
                    <TabsList className="grid w-full grid-cols-2">
                      <TabsTrigger value="template">Template</TabsTrigger>
                      <TabsTrigger value="placeholder">Placeholder</TabsTrigger>
                    </TabsList>
                    
                    <TabsContent value="template" className="space-y-4 mt-4">
                      <div>
                        <Label>Template Name</Label>
                        <Input
                          value={template.name}
                          onChange={(e) => setTemplate(prev => ({ ...prev, name: e.target.value }))}
                          placeholder="Enter template name"
                        />
                      </div>
                      
                      <div>
                        <Label>Description</Label>
                        <Textarea
                          value={template.description}
                          onChange={(e) => setTemplate(prev => ({ ...prev, description: e.target.value }))}
                          placeholder="Template description"
                          className="h-20"
                        />
                      </div>
                      
                      <div>
                        <Label>Template Type</Label>
                        <Select
                          value={template.template_type}
                          onValueChange={(value) => setTemplate(prev => ({ ...prev, template_type: value }))}
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="docx">Word Document</SelectItem>
                            <SelectItem value="html">HTML</SelectItem>
                            <SelectItem value="markdown">Markdown</SelectItem>
                            <SelectItem value="pdf">PDF</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      
                      <div className="flex items-center space-x-2">
                        <Switch
                          checked={template.is_public}
                          onCheckedChange={(checked) => setTemplate(prev => ({ ...prev, is_public: checked }))}
                        />
                        <Label>Public Template</Label>
                      </div>
                    </TabsContent>
                    
                    <TabsContent value="placeholder" className="space-y-4 mt-4">
                      {selectedPlaceholder ? (
                        <div className="space-y-4">
                          <div>
                            <Label>Placeholder Name</Label>
                            <Input
                              value={selectedPlaceholder.name}
                              onChange={(e) => {
                                const updated = { ...selectedPlaceholder, name: e.target.value }
                                setSelectedPlaceholder(updated)
                                setTemplate(prev => ({
                                  ...prev,
                                  placeholders: prev.placeholders.map(p => 
                                    p.id === updated.id ? updated : p
                                  )
                                }))
                              }}
                            />
                          </div>
                          
                          <div>
                            <Label>Type</Label>
                            <Select
                              value={selectedPlaceholder.type}
                              onValueChange={(value: unknown) => {
                                const updated = { ...selectedPlaceholder, type: value as AdvancedPlaceholder['type'] }
                                setSelectedPlaceholder(updated)
                                setTemplate(prev => ({
                                  ...prev,
                                  placeholders: prev.placeholders.map(p => 
                                    p.id === updated.id ? updated : p
                                  )
                                }))
                              }}
                            >
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="text">Text</SelectItem>
                                <SelectItem value="number">Number</SelectItem>
                                <SelectItem value="date">Date</SelectItem>
                                <SelectItem value="table">Table</SelectItem>
                                <SelectItem value="chart">Chart</SelectItem>
                                <SelectItem value="image">Image</SelectItem>
                                <SelectItem value="formula">Formula</SelectItem>
                                <SelectItem value="conditional">Conditional</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                          
                          <div>
                            <Label>Description</Label>
                            <Textarea
                              value={selectedPlaceholder.description || ''}
                              onChange={(e) => {
                                const updated = { ...selectedPlaceholder, description: e.target.value }
                                setSelectedPlaceholder(updated)
                                setTemplate(prev => ({
                                  ...prev,
                                  placeholders: prev.placeholders.map(p => 
                                    p.id === updated.id ? updated : p
                                  )
                                }))
                              }}
                              className="h-16"
                            />
                          </div>
                          
                          <div className="flex items-center space-x-2">
                            <Switch
                              checked={selectedPlaceholder.required}
                              onCheckedChange={(checked) => {
                                const updated = { ...selectedPlaceholder, required: checked }
                                setSelectedPlaceholder(updated)
                                setTemplate(prev => ({
                                  ...prev,
                                  placeholders: prev.placeholders.map(p => 
                                    p.id === updated.id ? updated : p
                                  )
                                }))
                              }}
                            />
                            <Label>Required Field</Label>
                          </div>
                        </div>
                      ) : (
                        <div className="text-center text-gray-500 py-8">
                          <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                          <p>Select a placeholder to edit its properties</p>
                        </div>
                      )}
                    </TabsContent>
                  </Tabs>
                </ScrollArea>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}