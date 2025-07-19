/**
 * Basic setup test to verify Jest and testing environment
 */

describe('Test Environment Setup', () => {
  it('should have Jest configured correctly', () => {
    expect(true).toBe(true)
  })

  it('should have testing-library/jest-dom matchers available', () => {
    const element = document.createElement('div')
    element.textContent = 'Hello World'
    document.body.appendChild(element)
    
    expect(element).toBeInTheDocument()
    expect(element).toHaveTextContent('Hello World')
    
    document.body.removeChild(element)
  })

  it('should support ES6 modules and TypeScript', () => {
    const testObject = { name: 'test', value: 42 }
    const { name, value } = testObject
    
    expect(name).toBe('test')
    expect(value).toBe(42)
  })
})