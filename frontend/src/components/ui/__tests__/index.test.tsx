import React from 'react'
import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'

// Test that all UI components can be imported without errors
describe('UI Components Index', () => {
  it('should export all UI components without errors', async () => {
    // Test that we can import all components
    const { Button } = await import('../button')
    const { Input } = await import('../input')
    const { Card, CardContent, CardHeader, CardTitle } = await import('../card')
    const { Badge } = await import('../badge')
    
    expect(Button).toBeDefined()
    expect(Input).toBeDefined()
    expect(Card).toBeDefined()
    expect(CardContent).toBeDefined()
    expect(CardHeader).toBeDefined()
    expect(CardTitle).toBeDefined()
    expect(Badge).toBeDefined()
  })

  it('should render basic UI components', () => {
    const TestComponent = () => {
      const { Button } = require('../button')
      const { Input } = require('../input')
      const { Card, CardContent, CardHeader, CardTitle } = require('../card')
      
      return (
        <div>
          <Button>Test Button</Button>
          <Input placeholder="Test Input" />
          <Card>
            <CardHeader>
              <CardTitle>Test Card</CardTitle>
            </CardHeader>
            <CardContent>Test Content</CardContent>
          </Card>
        </div>
      )
    }

    render(<TestComponent />)
    
    expect(screen.getByText('Test Button')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Test Input')).toBeInTheDocument()
    expect(screen.getByText('Test Card')).toBeInTheDocument()
    expect(screen.getByText('Test Content')).toBeInTheDocument()
  })
})