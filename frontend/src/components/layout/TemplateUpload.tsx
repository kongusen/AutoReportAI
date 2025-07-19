"use client"

import { useState, DragEvent } from 'react'
import { Upload, FileText, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'

interface TemplateUploadProps {
  onUpload: (file: File, name: string, description: string, isPublic: boolean) => void
}

export function TemplateUpload({ onUpload }: TemplateUploadProps) {
  const [file, setFile] = useState<File | null>(null)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [isPublic, setIsPublic] = useState(false)
  const [isDragActive, setIsDragActive] = useState(false)

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragActive(false)
    
    const files = Array.from(e.dataTransfer.files)
    const acceptedFiles = files.filter(file => {
      const extension = file.name.toLowerCase().split('.').pop()
      return ['docx', 'doc', 'html', 'md'].includes(extension || '')
    })
    
    if (acceptedFiles.length > 0) {
      setFile(acceptedFiles[0])
      if (!name) {
        setName(acceptedFiles[0].name.replace(/\.[^/.]+$/, ""))
      }
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files.length > 0) {
      setFile(files[0])
      if (!name) {
        setName(files[0].name.replace(/\.[^/.]+$/, ""))
      }
    }
  }

  const handleSubmit = () => {
    if (file && name) {
      onUpload(file, name, description, isPublic)
    }
  }

  const removeFile = () => {
    setFile(null)
    setName('')
    setDescription('')
  }

  return (
    <Card className="border-gray-200 dark:border-gray-700">
      <CardHeader>
        <CardTitle className="text-gray-900 dark:text-gray-100">上传模板</CardTitle>
        <CardDescription className="text-gray-600 dark:text-gray-400">
          支持 DOCX、HTML、Markdown 格式
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* 文件上传区域 */}
        {!file ? (
          <div
            onDrop={handleDrop}
            onDragOver={(e) => {
              e.preventDefault()
              setIsDragActive(true)
            }}
            onDragLeave={() => setIsDragActive(false)}
            className={`
              border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
              ${isDragActive 
                ? 'border-gray-400 bg-gray-50 dark:bg-gray-800' 
                : 'border-gray-300 dark:border-gray-600 hover:border-gray-400'
              }
            `}
          >
            <Upload className="mx-auto h-12 w-12 text-gray-400 mb-4" />
            <p className="text-gray-600 dark:text-gray-400">
              {isDragActive ? '释放文件...' : '拖拽文件到此处，或点击选择'}
            </p>
            <input
              type="file"
              accept=".docx,.doc,.html,.md"
              onChange={handleFileSelect}
              className="hidden"
              id="file-upload"
            />
            <label htmlFor="file-upload" className="mt-2 inline-block">
              <Button variant="outline" size="sm" className="cursor-pointer">
                选择文件
              </Button>
            </label>
          </div>
        ) : (
          <div className="border rounded-lg p-4 bg-gray-50 dark:bg-gray-800">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <FileText className="h-8 w-8 text-gray-600 dark:text-gray-400" />
                <div>
                  <p className="font-medium text-gray-900 dark:text-gray-100">{file.name}</p>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {(file.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={removeFile}
                className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}

        {/* 表单字段 */}
        <div className="space-y-4">
          <div className="space-y-2">
            <Label className="text-gray-700 dark:text-gray-300">模板名称</Label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="输入模板名称"
              className="bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600"
            />
          </div>

          <div className="space-y-2">
            <Label className="text-gray-700 dark:text-gray-300">模板描述</Label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="描述模板的用途和内容"
              rows={3}
              className="bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600"
            />
          </div>

          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              id="public"
              checked={isPublic}
              onChange={(e) => setIsPublic(e.target.checked)}
              className="rounded border-gray-300"
            />
            <Label htmlFor="public" className="text-gray-700 dark:text-gray-300">
              设为公开模板
            </Label>
          </div>
        </div>

        {/* 提交按钮 */}
        <Button
          onClick={handleSubmit}
          disabled={!file || !name}
          className="w-full bg-gray-900 hover:bg-gray-800 text-white dark:bg-gray-100 dark:hover:bg-gray-200 dark:text-gray-900"
        >
          上传模板
        </Button>
      </CardContent>
    </Card>
  )
}
