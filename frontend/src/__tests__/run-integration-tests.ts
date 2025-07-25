/**
 * Integration Test Runner
 * 
 * This script runs comprehensive integration tests for the API services
 * and generates detailed reports.
 */

import { execSync } from 'child_process'
import fs from 'fs'
import path from 'path'

interface TestResult {
  testSuite: string
  passed: number
  failed: number
  skipped: number
  duration: number
  coverage?: {
    lines: number
    functions: number
    branches: number
    statements: number
  }
}

interface TestReport {
  timestamp: string
  totalTests: number
  totalPassed: number
  totalFailed: number
  totalSkipped: number
  totalDuration: number
  overallCoverage?: {
    lines: number
    functions: number
    branches: number
    statements: number
  }
  testResults: TestResult[]
  errors: string[]
}

class IntegrationTestRunner {
  private testReport: TestReport = {
    timestamp: new Date().toISOString(),
    totalTests: 0,
    totalPassed: 0,
    totalFailed: 0,
    totalSkipped: 0,
    totalDuration: 0,
    testResults: [],
    errors: []
  }

  async runAllTests(): Promise<void> {
    console.log('🚀 Starting API Integration Tests...\n')

    const testSuites = [
      'auth.test.ts',
      'data-sources.test.ts',
      'templates.test.ts',
      // Add more test suites as they are created
    ]

    for (const testSuite of testSuites) {
      await this.runTestSuite(testSuite)
    }

    await this.generateReport()
    this.printSummary()
  }

  private async runTestSuite(testSuite: string): Promise<void> {
    console.log(`📋 Running ${testSuite}...`)
    
    const startTime = Date.now()
    
    try {
      const result = execSync(
        `npx jest src/__tests__/api/${testSuite} --json --coverage`,
        { 
          encoding: 'utf8',
          cwd: process.cwd()
        }
      )

      const testResult = JSON.parse(result)
      const duration = Date.now() - startTime

      const suiteResult: TestResult = {
        testSuite,
        passed: testResult.numPassedTests || 0,
        failed: testResult.numFailedTests || 0,
        skipped: testResult.numPendingTests || 0,
        duration,
        coverage: this.extractCoverage(testResult)
      }

      this.testReport.testResults.push(suiteResult)
      this.updateTotals(suiteResult)

      console.log(`✅ ${testSuite} completed in ${duration}ms`)
      console.log(`   Passed: ${suiteResult.passed}, Failed: ${suiteResult.failed}, Skipped: ${suiteResult.skipped}\n`)

    } catch (error) {
      const duration = Date.now() - startTime
      const errorMessage = error instanceof Error ? error.message : String(error)
      
      console.log(`❌ ${testSuite} failed in ${duration}ms`)
      console.log(`   Error: ${errorMessage}\n`)

      this.testReport.errors.push(`${testSuite}: ${errorMessage}`)
      
      const suiteResult: TestResult = {
        testSuite,
        passed: 0,
        failed: 1,
        skipped: 0,
        duration
      }

      this.testReport.testResults.push(suiteResult)
      this.updateTotals(suiteResult)
    }
  }

  private extractCoverage(testResult: any): TestResult['coverage'] {
    if (!testResult.coverageMap) return undefined

    const coverage = testResult.coverageMap
    const totals = coverage.getCoverageSummary?.() || {}

    return {
      lines: totals.lines?.pct || 0,
      functions: totals.functions?.pct || 0,
      branches: totals.branches?.pct || 0,
      statements: totals.statements?.pct || 0
    }
  }

  private updateTotals(suiteResult: TestResult): void {
    this.testReport.totalTests += suiteResult.passed + suiteResult.failed + suiteResult.skipped
    this.testReport.totalPassed += suiteResult.passed
    this.testReport.totalFailed += suiteResult.failed
    this.testReport.totalSkipped += suiteResult.skipped
    this.testReport.totalDuration += suiteResult.duration
  }

  private async generateReport(): Promise<void> {
    // Calculate overall coverage
    if (this.testReport.testResults.some(r => r.coverage)) {
      const coverageResults = this.testReport.testResults
        .filter(r => r.coverage)
        .map(r => r.coverage!)

      this.testReport.overallCoverage = {
        lines: this.calculateAverageCoverage(coverageResults, 'lines'),
        functions: this.calculateAverageCoverage(coverageResults, 'functions'),
        branches: this.calculateAverageCoverage(coverageResults, 'branches'),
        statements: this.calculateAverageCoverage(coverageResults, 'statements')
      }
    }

    // Generate JSON report
    const reportPath = path.join(process.cwd(), 'test-reports', 'integration-test-report.json')
    const reportDir = path.dirname(reportPath)

    if (!fs.existsSync(reportDir)) {
      fs.mkdirSync(reportDir, { recursive: true })
    }

    fs.writeFileSync(reportPath, JSON.stringify(this.testReport, null, 2))

    // Generate HTML report
    await this.generateHtmlReport(reportPath.replace('.json', '.html'))

    console.log(`📊 Test report generated: ${reportPath}`)
  }

  private calculateAverageCoverage(
    coverageResults: NonNullable<TestResult['coverage']>[],
    metric: keyof NonNullable<TestResult['coverage']>
  ): number {
    if (coverageResults.length === 0) return 0
    
    const sum = coverageResults.reduce((acc, coverage) => acc + coverage[metric], 0)
    return Math.round(sum / coverageResults.length * 100) / 100
  }

  private async generateHtmlReport(htmlPath: string): Promise<void> {
    const html = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>API Integration Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { text-align: center; margin-bottom: 30px; }
        .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .summary-card { background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }
        .summary-card h3 { margin: 0 0 10px 0; color: #333; }
        .summary-card .value { font-size: 2em; font-weight: bold; margin: 10px 0; }
        .passed { color: #28a745; }
        .failed { color: #dc3545; }
        .skipped { color: #ffc107; }
        .coverage { color: #17a2b8; }
        .test-results { margin-top: 30px; }
        .test-suite { background: #f8f9fa; margin: 10px 0; padding: 15px; border-radius: 8px; border-left: 4px solid #007bff; }
        .test-suite.failed { border-left-color: #dc3545; }
        .test-suite h4 { margin: 0 0 10px 0; }
        .test-metrics { display: flex; gap: 20px; flex-wrap: wrap; }
        .metric { background: white; padding: 10px; border-radius: 4px; }
        .errors { margin-top: 30px; }
        .error { background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; padding: 10px; margin: 5px 0; border-radius: 4px; }
        .timestamp { color: #666; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>API Integration Test Report</h1>
            <p class="timestamp">Generated on ${new Date(this.testReport.timestamp).toLocaleString()}</p>
        </div>

        <div class="summary">
            <div class="summary-card">
                <h3>Total Tests</h3>
                <div class="value">${this.testReport.totalTests}</div>
            </div>
            <div class="summary-card">
                <h3>Passed</h3>
                <div class="value passed">${this.testReport.totalPassed}</div>
            </div>
            <div class="summary-card">
                <h3>Failed</h3>
                <div class="value failed">${this.testReport.totalFailed}</div>
            </div>
            <div class="summary-card">
                <h3>Skipped</h3>
                <div class="value skipped">${this.testReport.totalSkipped}</div>
            </div>
            <div class="summary-card">
                <h3>Duration</h3>
                <div class="value">${(this.testReport.totalDuration / 1000).toFixed(2)}s</div>
            </div>
            ${this.testReport.overallCoverage ? `
            <div class="summary-card">
                <h3>Coverage</h3>
                <div class="value coverage">${this.testReport.overallCoverage.lines.toFixed(1)}%</div>
            </div>
            ` : ''}
        </div>

        <div class="test-results">
            <h2>Test Suite Results</h2>
            ${this.testReport.testResults.map(result => `
                <div class="test-suite ${result.failed > 0 ? 'failed' : ''}">
                    <h4>${result.testSuite}</h4>
                    <div class="test-metrics">
                        <div class="metric">
                            <strong>Passed:</strong> <span class="passed">${result.passed}</span>
                        </div>
                        <div class="metric">
                            <strong>Failed:</strong> <span class="failed">${result.failed}</span>
                        </div>
                        <div class="metric">
                            <strong>Skipped:</strong> <span class="skipped">${result.skipped}</span>
                        </div>
                        <div class="metric">
                            <strong>Duration:</strong> ${(result.duration / 1000).toFixed(2)}s
                        </div>
                        ${result.coverage ? `
                        <div class="metric">
                            <strong>Coverage:</strong> ${result.coverage.lines.toFixed(1)}%
                        </div>
                        ` : ''}
                    </div>
                </div>
            `).join('')}
        </div>

        ${this.testReport.errors.length > 0 ? `
        <div class="errors">
            <h2>Errors</h2>
            ${this.testReport.errors.map(error => `
                <div class="error">${error}</div>
            `).join('')}
        </div>
        ` : ''}
    </div>
</body>
</html>
    `

    fs.writeFileSync(htmlPath, html)
  }

  private printSummary(): void {
    console.log('\n📊 Test Summary:')
    console.log('================')
    console.log(`Total Tests: ${this.testReport.totalTests}`)
    console.log(`Passed: ${this.testReport.totalPassed}`)
    console.log(`Failed: ${this.testReport.totalFailed}`)
    console.log(`Skipped: ${this.testReport.totalSkipped}`)
    console.log(`Duration: ${(this.testReport.totalDuration / 1000).toFixed(2)}s`)
    
    if (this.testReport.overallCoverage) {
      console.log(`Coverage: ${this.testReport.overallCoverage.lines.toFixed(1)}%`)
    }

    if (this.testReport.totalFailed > 0) {
      console.log('\n❌ Some tests failed. Check the report for details.')
      process.exit(1)
    } else {
      console.log('\n✅ All tests passed!')
    }
  }
}

// Run tests if this script is executed directly
if (require.main === module) {
  const runner = new IntegrationTestRunner()
  runner.runAllTests().catch(error => {
    console.error('Test runner failed:', error)
    process.exit(1)
  })
}

export { IntegrationTestRunner }