'use client'

import React from 'react'
import { AppLayout } from '@/components/layout/AppLayout'
import { PageHeader } from '@/components/layout/PageHeader'
import UnifiedAgentInsights from '@/components/system/UnifiedAgentInsights'

export default function SystemInsightsPage() {
  return (
    <AppLayout>
      <div className="space-y-6">
        <PageHeader
          title="系统洞察"
          description="统一AI代理架构的性能监控和配置管理"
        />
        
        <UnifiedAgentInsights />
      </div>
    </AppLayout>
  )
}