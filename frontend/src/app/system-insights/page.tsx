'use client'

import React from 'react'
import AppLayout from '@/components/layout/AppLayout'
import PageHeader from '@/components/layout/PageHeader'
import ReactAgentInsights from '@/components/system/ReactAgentInsights'

export default function SystemInsightsPage() {
  return (
    <AppLayout>
      <div className="space-y-6">
        <PageHeader
          title="系统洞察"
          description="React Agent 智能系统的性能监控和配置管理"
        />
        
        <ReactAgentInsights />
      </div>
    </AppLayout>
  )
}