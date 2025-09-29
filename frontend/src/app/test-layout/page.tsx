'use client'

import { PageHeader } from '@/components/layout/PageHeader'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'

export default function TestLayoutPage() {
  return (
    <>
      <PageHeader
        title="布局测试页面"
        description="用于测试移动端和桌面端的布局是否正常"
        actions={
          <div className="flex space-x-2">
            <Button variant="outline" size="sm">
              测试按钮1
            </Button>
            <Button size="sm">
              测试按钮2
            </Button>
          </div>
        }
      />

      {/* 测试内容区域 */}
      <div className="space-y-6">
        {/* 测试卡片网格 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                测试卡片 1
                <Badge variant="success">正常</Badge>
              </CardTitle>
              <CardDescription>
                这是第一个测试卡片，用于检查响应式布局
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-gray-600">
                内容区域测试文本。这里应该在不同屏幕尺寸下正确显示。
              </p>
              <div className="mt-4">
                <Button variant="outline" size="sm" className="w-full">
                  测试操作
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                测试卡片 2
                <Badge variant="warning">待机</Badge>
              </CardTitle>
              <CardDescription>
                这是第二个测试卡片，检查多列布局
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-gray-600">
                在移动端，这些卡片应该垂直堆叠。在桌面端，应该水平排列。
              </p>
              <div className="mt-4">
                <Button variant="outline" size="sm" className="w-full">
                  另一个操作
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                测试卡片 3
                <Badge variant="destructive">错误</Badge>
              </CardTitle>
              <CardDescription>
                第三个测试卡片，完整网格测试
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-gray-600">
                这个卡片测试三列布局在大屏幕上的显示效果。
              </p>
              <div className="mt-4">
                <Button variant="outline" size="sm" className="w-full">
                  第三个操作
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* 测试布局问题指示器 */}
        <Card>
          <CardHeader>
            <CardTitle>布局问题检查清单</CardTitle>
            <CardDescription>
              请在不同设备上检查以下项目是否正常
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm">移动端顶部导航栏不遮挡内容</span>
                <Badge variant="default">待检查</Badge>
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm">页面标题在移动端正确显示</span>
                <Badge variant="default">待检查</Badge>
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm">操作按钮在移动端垂直堆叠</span>
                <Badge variant="default">待检查</Badge>
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm">侧边栏在桌面端正确显示</span>
                <Badge variant="default">待检查</Badge>
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm">内容区域有正确的左边距</span>
                <Badge variant="default">待检查</Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 测试长内容滚动 */}
        <Card>
          <CardHeader>
            <CardTitle>滚动测试</CardTitle>
            <CardDescription>
              测试长内容的滚动是否正常
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {Array.from({ length: 10 }, (_, i) => (
                <div key={i} className="p-4 bg-gray-50 rounded-lg">
                  <h3 className="font-medium">测试内容块 {i + 1}</h3>
                  <p className="text-sm text-gray-600 mt-2">
                    这是用于测试滚动的内容块。每个块都有相同的结构，
                    用于验证在长页面中滚动是否平滑，以及固定元素是否正确工作。
                    在移动端，需要确保顶部导航栏始终固定在顶部，
                    而内容可以在其下方正常滚动。
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </>
  )
}