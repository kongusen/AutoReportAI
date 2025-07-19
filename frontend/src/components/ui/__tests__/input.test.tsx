import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import { Input } from '../input'

describe('Input Component', () => {
  it('should render with default props', () => {
    render(<Input placeholder="Enter text" />)
    
    const input = screen.getByPlaceholderText('Enter text')
    expect(input).toBeInTheDocument()
    expect(input).toHaveAttribute('data-slot', 'input')
    expect(input).toHaveAttribute('type', 'text')
  })

  it('should handle value changes', () => {
    const handleChange = jest.fn()
    render(<Input onChange={handleChange} />)
    
    const input = screen.getByRole('textbox')
    fireEvent.change(input, { target: { value: 'test value' } })
    
    expect(handleChange).toHaveBeenCalledTimes(1)
    expect(input).toHaveValue('test value')
  })

  it('should support different input types', () => {
    const { rerender } = render(<Input type="email" />)
    
    let input = screen.getByRole('textbox')
    expect(input).toHaveAttribute('type', 'email')
    
    rerender(<Input type="password" />)
    input = screen.getByDisplayValue('')
    expect(input).toHaveAttribute('type', 'password')
    
    rerender(<Input type="number" />)
    input = screen.getByRole('spinbutton')
    expect(input).toHaveAttribute('type', 'number')
  })

  it('should be disabled when disabled prop is true', () => {
    render(<Input disabled />)
    
    const input = screen.getByRole('textbox')
    expect(input).toBeDisabled()
    expect(input).toHaveClass('disabled:pointer-events-none', 'disabled:opacity-50')
  })

  it('should apply custom className', () => {
    render(<Input className="custom-input" />)
    
    const input = screen.getByRole('textbox')
    expect(input).toHaveClass('custom-input')
  })

  it('should forward other props', () => {
    render(<Input data-testid="test-input" aria-label="Test input" maxLength={10} />)
    
    const input = screen.getByTestId('test-input')
    expect(input).toHaveAttribute('aria-label', 'Test input')
    expect(input).toHaveAttribute('maxLength', '10')
  })

  it('should handle focus and blur events', () => {
    const handleFocus = jest.fn()
    const handleBlur = jest.fn()
    render(<Input onFocus={handleFocus} onBlur={handleBlur} />)
    
    const input = screen.getByRole('textbox')
    
    fireEvent.focus(input)
    expect(handleFocus).toHaveBeenCalledTimes(1)
    
    fireEvent.blur(input)
    expect(handleBlur).toHaveBeenCalledTimes(1)
  })

  it('should handle keyboard events', () => {
    const handleKeyDown = jest.fn()
    render(<Input onKeyDown={handleKeyDown} />)
    
    const input = screen.getByRole('textbox')
    fireEvent.keyDown(input, { key: 'Enter' })
    
    expect(handleKeyDown).toHaveBeenCalledTimes(1)
  })

  it('should support controlled input', () => {
    const TestComponent = () => {
      const [value, setValue] = React.useState('')
      return (
        <Input 
          value={value} 
          onChange={(e) => setValue(e.target.value)}
          data-testid="controlled-input"
        />
      )
    }
    
    render(<TestComponent />)
    
    const input = screen.getByTestId('controlled-input')
    fireEvent.change(input, { target: { value: 'controlled value' } })
    
    expect(input).toHaveValue('controlled value')
  })

  it('should apply focus-visible styles', () => {
    render(<Input />)
    
    const input = screen.getByRole('textbox')
    expect(input).toHaveClass('focus-visible:border-ring', 'focus-visible:ring-ring/50')
  })

  it('should apply aria-invalid styles', () => {
    render(<Input aria-invalid />)
    
    const input = screen.getByRole('textbox')
    expect(input).toHaveClass('aria-invalid:ring-destructive/20', 'aria-invalid:border-destructive')
  })
})