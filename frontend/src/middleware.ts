import { NextRequest, NextResponse } from 'next/server'

// Import configuration from the new i18n system
const SUPPORTED_LOCALES = ['zh-CN', 'en-US'] as const
const DEFAULT_LOCALE = 'zh-CN'
const FALLBACK_LOCALE = 'en-US'
const COOKIE_NAME = 'i18n-locale'

type SupportedLocale = typeof SUPPORTED_LOCALES[number]

interface LocaleDetectionResult {
  locale: SupportedLocale
  source: 'url' | 'cookie' | 'header' | 'default'
  confidence: number
}

/**
 * Enhanced locale detection with multiple sources and fallback mechanism
 */
function detectLocale(request: NextRequest): LocaleDetectionResult {
  const pathname = request.nextUrl.pathname
  
  // 1. Check URL path first (highest priority)
  const urlLocale = pathname.split('/')[1]
  if (SUPPORTED_LOCALES.includes(urlLocale as SupportedLocale)) {
    return {
      locale: urlLocale as SupportedLocale,
      source: 'url',
      confidence: 1.0
    }
  }
  
  // 2. Check cookie (high priority)
  const cookieLocale = request.cookies.get(COOKIE_NAME)?.value
  if (cookieLocale && SUPPORTED_LOCALES.includes(cookieLocale as SupportedLocale)) {
    return {
      locale: cookieLocale as SupportedLocale,
      source: 'cookie',
      confidence: 0.9
    }
  }
  
  // 3. Check Accept-Language header (medium priority)
  const acceptLanguage = request.headers.get('accept-language')
  if (acceptLanguage) {
    const headerLocale = parseAcceptLanguage(acceptLanguage)
    if (headerLocale) {
      return {
        locale: headerLocale,
        source: 'header',
        confidence: 0.7
      }
    }
  }
  
  // 4. Use default locale (lowest priority)
  return {
    locale: DEFAULT_LOCALE,
    source: 'default',
    confidence: 0.5
  }
}

/**
 * Parse Accept-Language header and find the best matching locale
 */
function parseAcceptLanguage(acceptLanguage: string): SupportedLocale | null {
  try {
    // Parse the Accept-Language header
    const languages = acceptLanguage
      .split(',')
      .map(lang => {
        const [locale, qValue] = lang.trim().split(';q=')
        return {
          locale: locale.trim(),
          quality: qValue ? parseFloat(qValue) : 1.0
        }
      })
      .sort((a, b) => b.quality - a.quality)
    
    // Find exact matches first
    for (const { locale } of languages) {
      if (SUPPORTED_LOCALES.includes(locale as SupportedLocale)) {
        return locale as SupportedLocale
      }
    }
    
    // Find language matches (e.g., 'zh' matches 'zh-CN')
    for (const { locale } of languages) {
      const langCode = locale.split('-')[0]
      const matchingLocale = SUPPORTED_LOCALES.find(supportedLocale => 
        supportedLocale.startsWith(langCode)
      )
      if (matchingLocale) {
        return matchingLocale
      }
    }
    
    return null
  } catch (error) {
    console.warn('Failed to parse Accept-Language header:', error)
    return null
  }
}

/**
 * Check if the pathname has a valid locale prefix
 */
function hasValidLocalePrefix(pathname: string): boolean {
  const segments = pathname.split('/')
  const firstSegment = segments[1]
  return SUPPORTED_LOCALES.includes(firstSegment as SupportedLocale)
}

/**
 * Extract locale from pathname
 */
function getLocaleFromPathname(pathname: string): SupportedLocale | null {
  const segments = pathname.split('/')
  const firstSegment = segments[1]
  return SUPPORTED_LOCALES.includes(firstSegment as SupportedLocale) 
    ? firstSegment as SupportedLocale 
    : null
}

/**
 * Remove locale prefix from pathname
 */
function removeLocalePrefix(pathname: string): string {
  const segments = pathname.split('/')
  if (segments.length > 1 && SUPPORTED_LOCALES.includes(segments[1] as SupportedLocale)) {
    return '/' + segments.slice(2).join('/')
  }
  return pathname
}

/**
 * Add locale prefix to pathname
 */
function addLocalePrefix(pathname: string, locale: SupportedLocale): string {
  const cleanPath = removeLocalePrefix(pathname)
  return `/${locale}${cleanPath === '/' ? '' : cleanPath}`
}

/**
 * Check if the request should be processed by the middleware
 */
function shouldProcessRequest(pathname: string): boolean {
  // Skip API routes
  if (pathname.startsWith('/api/')) {
    return false
  }
  
  // Skip Next.js internal paths
  if (pathname.startsWith('/_next/')) {
    return false
  }
  
  // Skip static files
  if (pathname.includes('.') && !pathname.endsWith('/')) {
    const extension = pathname.split('.').pop()?.toLowerCase()
    const staticExtensions = ['ico', 'png', 'jpg', 'jpeg', 'gif', 'svg', 'css', 'js', 'json', 'xml', 'txt']
    if (staticExtensions.includes(extension || '')) {
      return false
    }
  }
  
  return true
}

/**
 * Create response with locale cookie
 */
function createResponseWithCookie(
  response: NextResponse, 
  locale: SupportedLocale,
  maxAge: number = 365 * 24 * 60 * 60 // 1 year
): NextResponse {
  response.cookies.set(COOKIE_NAME, locale, {
    maxAge,
    path: '/',
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
  })
  return response
}

/**
 * Main middleware function
 */
export function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname
  
  // Skip processing for certain paths
  if (!shouldProcessRequest(pathname)) {
    return NextResponse.next()
  }
  
  // Check if pathname already has a valid locale
  if (hasValidLocalePrefix(pathname)) {
    const currentLocale = getLocaleFromPathname(pathname)!
    
    // Ensure cookie is set for the current locale
    const response = NextResponse.next()
    const cookieLocale = request.cookies.get(COOKIE_NAME)?.value
    
    if (cookieLocale !== currentLocale) {
      return createResponseWithCookie(response, currentLocale)
    }
    
    return response
  }
  
  // Detect the best locale for the user
  const detection = detectLocale(request)
  const targetLocale = detection.locale
  
  // Create redirect URL with locale prefix
  const redirectUrl = new URL(addLocalePrefix(pathname, targetLocale), request.url)
  
  // Preserve query parameters
  redirectUrl.search = request.nextUrl.search
  
  // Create redirect response with locale cookie
  const response = NextResponse.redirect(redirectUrl)
  return createResponseWithCookie(response, targetLocale)
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public files with extensions
     */
    '/((?!api|_next/static|_next/image|favicon.ico|.*\\..*).*)',
  ],
}

// Export types and utilities for testing
export type { SupportedLocale, LocaleDetectionResult }
export { 
  detectLocale, 
  parseAcceptLanguage, 
  hasValidLocalePrefix, 
  getLocaleFromPathname,
  removeLocalePrefix,
  addLocalePrefix,
  shouldProcessRequest,
  SUPPORTED_LOCALES,
  DEFAULT_LOCALE,
  FALLBACK_LOCALE,
  COOKIE_NAME
}
