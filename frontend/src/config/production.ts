/**
 * Production Environment Configuration
 * 
 * This file contains configuration settings optimized for production deployment.
 */

export const productionConfig = {
  // API Configuration
  api: {
    baseUrl: process.env.NEXT_PUBLIC_API_BASE_URL || 'https://api.autoreportai.com',
    timeout: 30000, // 30 seconds for production
    retryAttempts: 3,
    retryDelay: 1000,
  },

  // Authentication Configuration
  auth: {
    tokenRefreshThreshold: 5 * 60 * 1000, // 5 minutes
    sessionTimeout: 24 * 60 * 60 * 1000, // 24 hours
    rememberMeDuration: 30 * 24 * 60 * 60 * 1000, // 30 days
  },

  // Logging Configuration
  logging: {
    level: 'error', // Only log errors in production
    enableConsoleLogging: false,
    enableServerLogging: true,
    maxLogEntries: 100,
  },

  // Performance Configuration
  performance: {
    enableMonitoring: true,
    enableMetrics: true,
    metricsInterval: 60000, // 1 minute
    maxMetrics: 500,
    enableWebVitals: true,
  },

  // Error Handling Configuration
  errorHandling: {
    enableErrorReporting: true,
    enableUserNotifications: true,
    maxErrorsInMemory: 50,
    errorReportingEndpoint: '/api/v1/errors/report',
  },

  // Cache Configuration
  cache: {
    enableApiCache: true,
    defaultTTL: 5 * 60 * 1000, // 5 minutes
    maxCacheSize: 100,
    enablePersistentCache: true,
  },

  // Security Configuration
  security: {
    enableCSP: true,
    enableHSTS: true,
    enableXSSProtection: true,
    enableFrameOptions: true,
    enableContentTypeOptions: true,
  },

  // Feature Flags
  features: {
    enableDarkMode: true,
    enableOfflineMode: false,
    enablePushNotifications: true,
    enableAnalytics: true,
    enableA11y: true,
    enablePWA: true,
  },

  // Health Check Configuration
  healthCheck: {
    enableHealthChecks: true,
    checkInterval: 5 * 60 * 1000, // 5 minutes
    enableHealthEndpoint: true,
    healthEndpoint: '/api/health',
  },

  // Build Configuration
  build: {
    enableMinification: true,
    enableCompression: true,
    enableTreeShaking: true,
    enableCodeSplitting: true,
    enableSourceMaps: false, // Disable in production for security
    enableBundleAnalysis: false,
  },

  // CDN Configuration
  cdn: {
    enableCDN: true,
    cdnUrl: process.env.NEXT_PUBLIC_CDN_URL || 'https://cdn.autoreportai.com',
    enableImageOptimization: true,
    enableAssetOptimization: true,
  },

  // Analytics Configuration
  analytics: {
    enableGoogleAnalytics: true,
    googleAnalyticsId: process.env.NEXT_PUBLIC_GA_ID,
    enableUserTracking: true,
    enablePerformanceTracking: true,
    enableErrorTracking: true,
  },

  // Notification Configuration
  notifications: {
    enablePushNotifications: true,
    enableEmailNotifications: true,
    enableInAppNotifications: true,
    notificationTimeout: 5000,
  },

  // Deployment Configuration
  deployment: {
    environment: 'production',
    version: process.env.NEXT_PUBLIC_APP_VERSION || '1.0.0',
    buildId: process.env.NEXT_PUBLIC_BUILD_ID || 'unknown',
    deploymentDate: process.env.NEXT_PUBLIC_DEPLOYMENT_DATE || new Date().toISOString(),
  },
}

// Environment-specific optimizations
export const optimizations = {
  // React optimizations
  react: {
    enableStrictMode: false, // Disable in production
    enableConcurrentFeatures: true,
    enableSuspense: true,
    enableErrorBoundaries: true,
  },

  // Next.js optimizations
  nextjs: {
    enableImageOptimization: true,
    enableFontOptimization: true,
    enableScriptOptimization: true,
    enableStaticGeneration: true,
    enableIncrementalStaticRegeneration: true,
  },

  // Bundle optimizations
  bundle: {
    enableCodeSplitting: true,
    enableDynamicImports: true,
    enableTreeShaking: true,
    enableDeadCodeElimination: true,
    enableMinification: true,
  },

  // Network optimizations
  network: {
    enableHTTP2: true,
    enableCompression: true,
    enableCaching: true,
    enablePrefetching: true,
    enablePreloading: true,
  },
}

// Security headers for production
export const securityHeaders = {
  'Content-Security-Policy': [
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://www.googletagmanager.com",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com",
    "img-src 'self' data: https:",
    "connect-src 'self' https://api.autoreportai.com wss://api.autoreportai.com",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
  ].join('; '),
  
  'Strict-Transport-Security': 'max-age=31536000; includeSubDomains; preload',
  'X-Frame-Options': 'DENY',
  'X-Content-Type-Options': 'nosniff',
  'X-XSS-Protection': '1; mode=block',
  'Referrer-Policy': 'strict-origin-when-cross-origin',
  'Permissions-Policy': [
    'camera=()',
    'microphone=()',
    'geolocation=()',
    'payment=()',
    'usb=()',
  ].join(', '),
}

// Performance budgets
export const performanceBudgets = {
  // Core Web Vitals targets
  coreWebVitals: {
    largestContentfulPaint: 2500, // 2.5 seconds
    firstInputDelay: 100, // 100ms
    cumulativeLayoutShift: 0.1, // 0.1 score
  },

  // Bundle size budgets
  bundleSize: {
    maxInitialBundle: 250 * 1024, // 250KB
    maxAsyncChunk: 100 * 1024, // 100KB
    maxTotalBundle: 1024 * 1024, // 1MB
  },

  // Network budgets
  network: {
    maxRequests: 50,
    maxResponseTime: 1000, // 1 second
    maxTotalTransferSize: 2 * 1024 * 1024, // 2MB
  },

  // Memory budgets
  memory: {
    maxHeapSize: 50 * 1024 * 1024, // 50MB
    maxMemoryUsage: 100 * 1024 * 1024, // 100MB
  },
}

// Monitoring configuration
export const monitoring = {
  // Error monitoring
  errors: {
    enableErrorBoundaries: true,
    enableGlobalErrorHandler: true,
    enableUnhandledRejectionHandler: true,
    maxErrorReports: 10,
    errorReportingInterval: 60000, // 1 minute
  },

  // Performance monitoring
  performance: {
    enablePerformanceObserver: true,
    enableResourceTiming: true,
    enableNavigationTiming: true,
    enableUserTiming: true,
    performanceReportingInterval: 300000, // 5 minutes
  },

  // User monitoring
  user: {
    enableUserSessionTracking: true,
    enableUserInteractionTracking: true,
    enablePageViewTracking: true,
    sessionTimeout: 30 * 60 * 1000, // 30 minutes
  },
}

// Export default configuration
export default productionConfig