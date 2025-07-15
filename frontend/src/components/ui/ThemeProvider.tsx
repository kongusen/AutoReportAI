"use client"

import { createContext, useContext, useEffect, useState } from 'react'

type Theme = 'light' | 'dark' | 'auto'
type Language = 'zh-CN' | 'en-US'

interface ThemeContextType {
  theme: Theme
  language: Language
  setTheme: (theme: Theme) => void
  setLanguage: (lang: Language) => void
  isDark: boolean
  t: (key: string) => string
}

// 简单的翻译映射
const translations = {
  'zh-CN': {
    'settings': '设置',
    'theme': '主题',
    'language': '语言',
    'notifications': '通知',
    'dark': '深色',
    'light': '浅色',
    'auto': '自动'
  },
  'en-US': {
    'settings': 'Settings',
    'theme': 'Theme',
    'language': 'Language',
    'notifications': 'Notifications',
    'dark': 'Dark',
    'light': 'Light',
    'auto': 'Auto'
  }
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<Theme>('light')
  const [language, setLanguage] = useState<Language>('zh-CN')
  const [isDark, setIsDark] = useState(false)

  const t = (key: string) => {
    return translations[language][key as keyof typeof translations['zh-CN']] || key
  }

  useEffect(() => {
    // 从localStorage加载设置
    const savedTheme = localStorage.getItem('theme') as Theme
    const savedLanguage = localStorage.getItem('language') as Language
    
    if (savedTheme) setTheme(savedTheme)
    if (savedLanguage) setLanguage(savedLanguage)
  }, [])

  useEffect(() => {
    // 保存设置到localStorage
    localStorage.setItem('theme', theme)
    localStorage.setItem('language', language)
    
    // 应用主题
    const root = document.documentElement
    const isDarkMode = theme === 'dark' || 
      (theme === 'auto' && window.matchMedia('(prefers-color-scheme: dark)').matches)
    
    setIsDark(isDarkMode)
    root.classList.toggle('dark', isDarkMode)
  }, [theme, language])

  const handleSetTheme = (newTheme: Theme) => {
    setTheme(newTheme)
  }

  const handleSetLanguage = (newLang: Language) => {
    setLanguage(newLang)
  }

  return (
    <ThemeContext.Provider value={{
      theme,
      language,
      setTheme: handleSetTheme,
      setLanguage: handleSetLanguage,
      isDark,
      t
    }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}
