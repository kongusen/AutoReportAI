import React from 'react'
import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import { Badge } from '../badge'

describe('Badge Component', () => {
  it('should render with default props', () => {
    render(<Badge>Default Badge</Badge>)
    
    const badge = screen.getByText('Default Badge')
    expect(badge).toBeInTheDocument()
  })

  it('should apply variant classes correctly', () => {
    const { rerender } = render(<Badge variant="default">Default</Badge>)
    
    let badge = screen.getByText('Default')
    expect(badge).toHaveClass('bg-primary')
    
    rerender(<Badge variant="secondary">Secondary</Badge>)
    badge = screen.getByText('Secondary')
    expect(badge).toHaveClass('bg-secondary')
    
    rerender(<Badge variant="destructive">Destructive</Badge>)
    badge = screen.getByText('Destructive')
    expect(badge).toHaveClass('bg-destructive')
    
    rerender(<Badge variant="outline">Outline</Badge>)
    badge = screen.getByText('Outline')
    expect(badge).toHaveClass('border')
  })

  it('should apply custom className', () => {
    render(<Badge className="custom-badge">Custom</Badge>)
    
    const badge = screen.getByText('Custom')
    expect(badge).toHaveClass('custom-badge')
  })

  it('should forward other props', () => {
    render(<Badge data-testid="test-badge" aria-label="Test badge">Test</Badge>)
    
    const badge = screen.getByTestId('test-badge')
    expect(badge).toHaveAttribute('aria-label', 'Test badge')
  })

  it('should render as different HTML elements', () => {
    render(<Badge as="span" data-testid="span-badge">Span Badge</Badge>)
    
    const badge = screen.getByTestId('span-badge')
    expect(badge.tagName).toBe('SPAN')
  })
})