'use client'

import { useI18n } from '@/components/providers/I18nProvider'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Globe, Check, Loader2 } from 'lucide-react'
import { useState, useCallback, useMemo } from 'react'
import { cn } from '@/lib/utils'

interface Language {
  code: 'zh-CN' | 'en-US'
  name: string
  nativeName: string
  flag: string
  rtl: boolean
}

export function LanguageSwitcher() {
  const { currentLocale, setLocale, t } = useI18n()
  const [isChanging, setIsChanging] = useState(false)
  const [pendingLanguage, setPendingLanguage] = useState<string | null>(null)

  // Memoize currentLocales to prevent unnecessary re-renders
  const currentLocales = useMemo<Language[]>(() => [
    { 
      code: 'zh-CN', 
      name: t('currentLocale.zh-CN'), 
      nativeName: '中文',
      flag: '🇨🇳',
      rtl: false
    },
    { 
      code: 'en-US', 
      name: t('currentLocale.en-US'), 
      nativeName: 'English',
      flag: '🇺🇸',
      rtl: false
    },
  ], [t])

  // Get current currentLocale info
  const currentLanguage = useMemo(() => 
    currentLocales.find(lang => lang.code === currentLocale),
    [currentLocales, currentLocale]
  )

  // Optimized currentLocale change handler with loading state
  const handleLanguageChange = useCallback(async (langCode: 'zh-CN' | 'en-US') => {
    if (langCode === currentLocale || isChanging) {
      return
    }

    setIsChanging(true)
    setPendingLanguage(langCode)

    try {
      // Add a small delay to show loading state for better UX
      await new Promise(resolve => setTimeout(resolve, 150))
      
      // Change currentLocale
      await setLocale(langCode)
      
      // Add another small delay for smooth transition
      await new Promise(resolve => setTimeout(resolve, 100))
    } catch (error) {
      console.error('Failed to change currentLocale:', error)
    } finally {
      setIsChanging(false)
      setPendingLanguage(null)
    }
  }, [currentLocale, setLocale, isChanging])

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button 
          variant="ghost" 
          size="sm" 
          className={cn(
            "w-9 px-0 transition-all duration-200 hover:scale-105",
            isChanging && "opacity-75 cursor-not-allowed"
          )}
          disabled={isChanging}
        >
          {isChanging ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <div className="relative">
              <Globe className={cn(
                "h-4 w-4 transition-transform duration-200",
                isChanging && "scale-90"
              )} />
              {currentLanguage && (
                <span 
                  className="absolute -bottom-1 -right-1 text-xs leading-none"
                  aria-hidden="true"
                >
                  {currentLanguage.flag}
                </span>
              )}
            </div>
          )}
          <span className="sr-only">
            {isChanging ? t('common.loading') : t('currentLocale.switch')}
          </span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent 
        align="end" 
        className="min-w-[160px] animate-in fade-in-0 zoom-in-95 duration-200"
      >
        {currentLocales.map((lang) => {
          const isSelected = currentLocale === lang.code
          const isPending = pendingLanguage === lang.code
          
          return (
            <DropdownMenuItem
              key={lang.code}
              onClick={() => handleLanguageChange(lang.code)}
              className={cn(
                "flex items-center justify-between cursor-pointer transition-all duration-150",
                "hover:bg-accent hover:text-accent-foreground",
                "focus:bg-accent focus:text-accent-foreground",
                isSelected && "bg-accent/50",
                (isChanging && !isPending) && "opacity-50 cursor-not-allowed",
                isPending && "bg-accent"
              )}
              disabled={isChanging && !isPending}
            >
              <div className="flex items-center space-x-3">
                <span 
                  className={cn(
                    "text-lg transition-transform duration-150",
                    isPending && "scale-110"
                  )}
                  role="img"
                  aria-label={`${lang.name} flag`}
                >
                  {lang.flag}
                </span>
                <div className="flex flex-col">
                  <span className="text-sm font-medium">
                    {lang.name}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {lang.nativeName}
                  </span>
                </div>
              </div>
              <div className="flex items-center space-x-1">
                {isPending && (
                  <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
                )}
                {isSelected && !isPending && (
                  <Check className={cn(
                    "h-4 w-4 text-primary transition-all duration-200",
                    "animate-in zoom-in-50"
                  )} />
                )}
              </div>
            </DropdownMenuItem>
          )
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
