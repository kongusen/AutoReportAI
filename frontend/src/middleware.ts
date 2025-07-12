import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// Rate limiting storage (in production, use Redis or external storage)
const rateLimitMap = new Map<string, { count: number; lastReset: number }>()

// Security configuration
const RATE_LIMIT_REQUESTS = 100 // requests per window
const RATE_LIMIT_WINDOW = 15 * 60 * 1000 // 15 minutes in milliseconds

function getRateLimitKey(request: NextRequest): string {
  // Use IP address for rate limiting
  const forwarded = request.headers.get('x-forwarded-for')
  const realIp = request.headers.get('x-real-ip')
  const ip = forwarded ? forwarded.split(',')[0] : realIp || 'unknown'
  return `rate_limit:${ip}`
}

function checkRateLimit(key: string): boolean {
  const now = Date.now()
  const record = rateLimitMap.get(key)

  if (!record || now - record.lastReset > RATE_LIMIT_WINDOW) {
    // Reset the counter
    rateLimitMap.set(key, { count: 1, lastReset: now })
    return true
  }

  if (record.count >= RATE_LIMIT_REQUESTS) {
    return false // Rate limit exceeded
  }

  record.count++
  return true
}

function validateSecurityHeaders(request: NextRequest): boolean {
  // Check for suspicious patterns in headers
  const userAgent = request.headers.get('user-agent') || ''
  const origin = request.headers.get('origin')

  // Block requests with suspicious user agents
  const suspiciousPatterns = [
    /bot/i,
    /crawler/i,
    /spider/i,
    /scan/i,
    /curl/i,
    /wget/i,
    /python/i,
    /php/i,
  ]

  // Allow legitimate browsers and development tools
  const allowedPatterns = [
    /mozilla/i,
    /chrome/i,
    /safari/i,
    /firefox/i,
    /edge/i,
    /postman/i, // Allow Postman for development
    /insomnia/i, // Allow Insomnia for development
  ]

  const isSuspicious = suspiciousPatterns.some((pattern) =>
    pattern.test(userAgent)
  )
  const isAllowed = allowedPatterns.some((pattern) => pattern.test(userAgent))

  if (isSuspicious && !isAllowed) {
    return false
  }

  // Validate origin for sensitive operations
  if (
    request.method === 'POST' ||
    request.method === 'PUT' ||
    request.method === 'DELETE'
  ) {
    const allowedOrigins = [
      'http://localhost:3000',
      'https://localhost:3000',
      process.env.NEXT_PUBLIC_APP_URL,
    ].filter(Boolean)

    if (origin && !allowedOrigins.includes(origin)) {
      // Allow requests without origin header (direct API calls)
      // but be suspicious of mismatched origins
      console.warn(`Suspicious origin detected: ${origin}`)
    }
  }

  return true
}

export function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname

  // Skip middleware for static assets and Next.js internals
  if (
    pathname.startsWith('/_next/') ||
    pathname.startsWith('/api/_next/') ||
    pathname.includes('.')
  ) {
    return NextResponse.next()
  }

  // Rate limiting
  const rateLimitKey = getRateLimitKey(request)
  if (!checkRateLimit(rateLimitKey)) {
    console.warn(`Rate limit exceeded for ${rateLimitKey}`)
    return new NextResponse('Too Many Requests', {
      status: 429,
      headers: {
        'Retry-After': '900', // 15 minutes
        'X-RateLimit-Limit': RATE_LIMIT_REQUESTS.toString(),
        'X-RateLimit-Remaining': '0',
        'X-RateLimit-Reset': new Date(
          Date.now() + RATE_LIMIT_WINDOW
        ).toISOString(),
      },
    })
  }

  // Security header validation
  if (!validateSecurityHeaders(request)) {
    const clientIp =
      request.headers.get('x-forwarded-for') ||
      request.headers.get('x-real-ip') ||
      'unknown'
    console.warn(`Suspicious request blocked from ${clientIp}`)
    return new NextResponse('Forbidden', { status: 403 })
  }

  // Add security headers to response
  const response = NextResponse.next()

  // Add additional security headers
  response.headers.set('X-Request-ID', crypto.randomUUID())
  response.headers.set('X-Timestamp', new Date().toISOString())

  // Log request for monitoring (in production, send to logging service)
  if (process.env.NODE_ENV === 'production') {
    const clientIp =
      request.headers.get('x-forwarded-for') ||
      request.headers.get('x-real-ip') ||
      'unknown'
    console.log({
      timestamp: new Date().toISOString(),
      method: request.method,
      url: request.url,
      userAgent: request.headers.get('user-agent'),
      ip: clientIp,
      origin: request.headers.get('origin'),
    })
  }

  return response
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
}
