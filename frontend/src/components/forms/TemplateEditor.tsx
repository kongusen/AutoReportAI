'use client'

import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { FileText } from 'lucide-react'

export function TemplateEditor() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Template Editor</h1>
          <p className="text-gray-600">Edit and manage your templates</p>
        </div>
      </div>
      
      <Card>
        <CardHeader>
          <CardTitle>Template Editor</CardTitle>
          <CardDescription>
            This is a placeholder for the template editor. The original component will be restored when the JSX parsing issue is resolved.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-500">Template Editor is temporarily unavailable.</p>
            <Button className="mt-4" onClick={() => window.location.reload()}>
              Reload Page
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default TemplateEditor
