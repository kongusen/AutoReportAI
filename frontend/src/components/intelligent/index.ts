/**
 * Intelligent Components
 * 
 * This module exports all AI-powered and intelligent functionality components.
 */

// Main intelligent components
export { IntelligentPlaceholderManager } from './IntelligentPlaceholderManager'
export { IntelligentReportGenerator } from './IntelligentReportGenerator'

// Modular sub-components
export { PlaceholderAnalyzer } from './PlaceholderAnalyzer'
export { FieldMatcher } from './FieldMatcher'
export { AIAssistant } from './AIAssistant'
export { ReportGenerator } from './ReportGenerator'
export { ErrorBoundary } from './ErrorBoundary'

// Utility components and hooks
export { useErrorHandler, withErrorBoundary } from './ErrorBoundary'