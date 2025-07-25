'use client'

import { 
  Skeleton, 
  CardSkeleton, 
  TableSkeleton, 
  ListSkeleton, 
  FormSkeleton,
  NavigationSkeleton,
  DashboardSkeleton 
} from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

// Dashboard Page Skeleton
export function DashboardPageSkeleton({ className }: { className?: string }) {
  return (
    <div className={cn('container mx-auto p-6', className)}>
      <DashboardSkeleton 
        showStats 
        showCharts 
        showRecentActivity 
      />
    </div>
  )
}

// Data Sources Page Skeleton
export function DataSourcesPageSkeleton({ className }: { className?: string }) {
  return (
    <div className={cn('container mx-auto p-6', className)}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="space-y-2">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-64" />
        </div>
        <Skeleton className="h-10 w-32" />
      </div>

      {/* Filters */}
      <div className="flex items-center space-x-4 mb-6">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-10 w-32" />
        <Skeleton className="h-10 w-24" />
      </div>

      {/* Data Sources Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {Array.from({ length: 6 }).map((_, index) => (
          <CardSkeleton
            key={index}
            showImage={false}
            showAvatar={false}
            titleLines={1}
            descriptionLines={2}
            showActions
          />
        ))}
      </div>
    </div>
  )
}

// Templates Page Skeleton
export function TemplatesPageSkeleton({ className }: { className?: string }) {
  return (
    <div className={cn('container mx-auto p-6', className)}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="space-y-2">
          <Skeleton className="h-8 w-40" />
          <Skeleton className="h-4 w-56" />
        </div>
        <div className="flex space-x-2">
          <Skeleton className="h-10 w-28" />
          <Skeleton className="h-10 w-24" />
        </div>
      </div>

      {/* Search and Filters */}
      <div className="flex items-center space-x-4 mb-6">
        <Skeleton className="h-10 flex-1 max-w-md" />
        <Skeleton className="h-10 w-32" />
        <Skeleton className="h-10 w-24" />
      </div>

      {/* Templates Table */}
      <div className="rounded-lg border bg-card">
        <TableSkeleton rows={8} columns={5} showHeader />
      </div>
    </div>
  )
}

// Tasks Page Skeleton
export function TasksPageSkeleton({ className }: { className?: string }) {
  return (
    <div className={cn('container mx-auto p-6', className)}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="space-y-2">
          <Skeleton className="h-8 w-32" />
          <Skeleton className="h-4 w-48" />
        </div>
        <Skeleton className="h-10 w-28" />
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="p-4 rounded-lg border bg-card">
            <div className="flex items-center justify-between">
              <div className="space-y-2">
                <Skeleton className="h-4 w-16" />
                <Skeleton className="h-6 w-12" />
              </div>
              <Skeleton className="h-6 w-6 rounded-full" />
            </div>
          </div>
        ))}
      </div>

      {/* Tasks List */}
      <div className="space-y-4">
        {Array.from({ length: 5 }).map((_, index) => (
          <div key={index} className="p-4 rounded-lg border bg-card">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4 flex-1">
                <Skeleton className="h-5 w-5 rounded" />
                <div className="space-y-2 flex-1">
                  <Skeleton className="h-5 w-48" />
                  <div className="flex items-center space-x-4">
                    <Skeleton className="h-4 w-24" />
                    <Skeleton className="h-4 w-32" />
                    <Skeleton className="h-4 w-20" />
                  </div>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <Skeleton className="h-6 w-16 rounded-full" />
                <Skeleton className="h-8 w-8" />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// History Page Skeleton
export function HistoryPageSkeleton({ className }: { className?: string }) {
  return (
    <div className={cn('container mx-auto p-6', className)}>
      {/* Header */}
      <div className="space-y-2 mb-6">
        <Skeleton className="h-8 w-40" />
        <Skeleton className="h-4 w-64" />
      </div>

      {/* Filters */}
      <div className="flex items-center space-x-4 mb-6">
        <Skeleton className="h-10 w-48" />
        <Skeleton className="h-10 w-32" />
        <Skeleton className="h-10 w-28" />
        <Skeleton className="h-10 w-24" />
      </div>

      {/* History Table */}
      <div className="rounded-lg border bg-card">
        <TableSkeleton rows={10} columns={6} showHeader />
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between mt-6">
        <Skeleton className="h-4 w-32" />
        <div className="flex items-center space-x-2">
          <Skeleton className="h-8 w-8" />
          <Skeleton className="h-8 w-8" />
          <Skeleton className="h-8 w-8" />
          <Skeleton className="h-8 w-8" />
          <Skeleton className="h-8 w-8" />
        </div>
      </div>
    </div>
  )
}

// Form Page Skeleton (Create/Edit)
export function FormPageSkeleton({ 
  className,
  title = 'Form',
  sections = 3 
}: { 
  className?: string
  title?: string
  sections?: number
}) {
  return (
    <div className={cn('container mx-auto p-6', className)}>
      {/* Header */}
      <div className="space-y-2 mb-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-64" />
      </div>

      {/* Form */}
      <div className="max-w-2xl">
        <div className="space-y-8">
          {Array.from({ length: sections }).map((_, sectionIndex) => (
            <div key={sectionIndex} className="space-y-6">
              {/* Section Title */}
              <div className="space-y-2">
                <Skeleton className="h-6 w-32" />
                <Skeleton className="h-4 w-48" />
              </div>

              {/* Section Fields */}
              <FormSkeleton 
                fields={4} 
                showTitle={false} 
                showSubmitButton={false}
              />
            </div>
          ))}

          {/* Submit Buttons */}
          <div className="flex items-center space-x-4 pt-6 border-t">
            <Skeleton className="h-10 w-24" />
            <Skeleton className="h-10 w-20" />
          </div>
        </div>
      </div>
    </div>
  )
}

// Settings Page Skeleton
export function SettingsPageSkeleton({ className }: { className?: string }) {
  return (
    <div className={cn('container mx-auto p-6', className)}>
      {/* Header */}
      <div className="space-y-2 mb-6">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-4 w-56" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sidebar Navigation */}
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, index) => (
            <Skeleton key={index} className="h-10 w-full" />
          ))}
        </div>

        {/* Settings Content */}
        <div className="lg:col-span-3 space-y-6">
          {Array.from({ length: 3 }).map((_, sectionIndex) => (
            <div key={sectionIndex} className="p-6 rounded-lg border bg-card">
              <div className="space-y-4">
                <div className="space-y-2">
                  <Skeleton className="h-6 w-40" />
                  <Skeleton className="h-4 w-64" />
                </div>
                <FormSkeleton 
                  fields={3} 
                  showTitle={false} 
                  showSubmitButton
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// Profile Page Skeleton
export function ProfilePageSkeleton({ className }: { className?: string }) {
  return (
    <div className={cn('container mx-auto p-6', className)}>
      {/* Header */}
      <div className="space-y-2 mb-6">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-4 w-48" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Profile Card */}
        <div className="p-6 rounded-lg border bg-card">
          <div className="flex flex-col items-center space-y-4">
            <Skeleton className="h-24 w-24 rounded-full" />
            <div className="text-center space-y-2">
              <Skeleton className="h-6 w-32" />
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-4 w-28" />
            </div>
            <Skeleton className="h-10 w-28" />
          </div>
        </div>

        {/* Profile Form */}
        <div className="lg:col-span-2">
          <div className="p-6 rounded-lg border bg-card">
            <div className="space-y-2 mb-6">
              <Skeleton className="h-6 w-40" />
              <Skeleton className="h-4 w-56" />
            </div>
            <FormSkeleton 
              fields={6} 
              showTitle={false} 
              showSubmitButton
            />
          </div>
        </div>
      </div>
    </div>
  )
}

// Generic List Page Skeleton
export function ListPageSkeleton({ 
  className,
  showFilters = true,
  showStats = false,
  itemCount = 8
}: { 
  className?: string
  showFilters?: boolean
  showStats?: boolean
  itemCount?: number
}) {
  return (
    <div className={cn('container mx-auto p-6', className)}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="space-y-2">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-64" />
        </div>
        <Skeleton className="h-10 w-32" />
      </div>

      {/* Stats */}
      {showStats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="p-4 rounded-lg border bg-card">
              <div className="space-y-2">
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-8 w-16" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
      {showFilters && (
        <div className="flex items-center space-x-4 mb-6">
          <Skeleton className="h-10 w-64" />
          <Skeleton className="h-10 w-32" />
          <Skeleton className="h-10 w-24" />
        </div>
      )}

      {/* List */}
      <ListSkeleton 
        items={itemCount} 
        variant="detailed" 
        showAvatar 
      />
    </div>
  )
}