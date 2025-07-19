import React from 'react'
import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle, CardAction } from '../card'

describe('Card Components', () => {
  describe('Card', () => {
    it('should render with default props', () => {
      render(<Card data-testid="card">Card content</Card>)
      
      const card = screen.getByTestId('card')
      expect(card).toBeInTheDocument()
      expect(card).toHaveTextContent('Card content')
    })

    it('should apply custom className', () => {
      render(<Card className="custom-card" data-testid="card">Content</Card>)
      
      const card = screen.getByTestId('card')
      expect(card).toHaveClass('custom-card')
    })

    it('should forward other props', () => {
      render(<Card data-testid="card" role="region" aria-label="Test card">Content</Card>)
      
      const card = screen.getByTestId('card')
      expect(card).toHaveAttribute('role', 'region')
      expect(card).toHaveAttribute('aria-label', 'Test card')
    })
  })

  describe('CardHeader', () => {
    it('should render with default props', () => {
      render(<CardHeader data-testid="card-header">Header content</CardHeader>)
      
      const header = screen.getByTestId('card-header')
      expect(header).toBeInTheDocument()
      expect(header).toHaveTextContent('Header content')
    })

    it('should apply custom className', () => {
      render(<CardHeader className="custom-header" data-testid="card-header">Content</CardHeader>)
      
      const header = screen.getByTestId('card-header')
      expect(header).toHaveClass('custom-header')
    })
  })

  describe('CardTitle', () => {
    it('should render with default props', () => {
      render(<CardTitle data-testid="card-title">Title content</CardTitle>)
      
      const title = screen.getByTestId('card-title')
      expect(title).toBeInTheDocument()
      expect(title).toHaveTextContent('Title content')
    })

    it('should apply custom className', () => {
      render(<CardTitle className="custom-title" data-testid="card-title">Content</CardTitle>)
      
      const title = screen.getByTestId('card-title')
      expect(title).toHaveClass('custom-title')
    })
  })

  describe('CardDescription', () => {
    it('should render with default props', () => {
      render(<CardDescription data-testid="card-description">Description content</CardDescription>)
      
      const description = screen.getByTestId('card-description')
      expect(description).toBeInTheDocument()
      expect(description).toHaveTextContent('Description content')
    })

    it('should apply custom className', () => {
      render(<CardDescription className="custom-description" data-testid="card-description">Content</CardDescription>)
      
      const description = screen.getByTestId('card-description')
      expect(description).toHaveClass('custom-description')
    })
  })

  describe('CardContent', () => {
    it('should render with default props', () => {
      render(<CardContent data-testid="card-content">Content</CardContent>)
      
      const content = screen.getByTestId('card-content')
      expect(content).toBeInTheDocument()
      expect(content).toHaveTextContent('Content')
    })

    it('should apply custom className', () => {
      render(<CardContent className="custom-content" data-testid="card-content">Content</CardContent>)
      
      const content = screen.getByTestId('card-content')
      expect(content).toHaveClass('custom-content')
    })
  })

  describe('CardAction', () => {
    it('should render with default props', () => {
      render(<CardAction data-testid="card-action">Action content</CardAction>)
      
      const action = screen.getByTestId('card-action')
      expect(action).toBeInTheDocument()
      expect(action).toHaveTextContent('Action content')
    })

    it('should apply custom className', () => {
      render(<CardAction className="custom-action" data-testid="card-action">Content</CardAction>)
      
      const action = screen.getByTestId('card-action')
      expect(action).toHaveClass('custom-action')
    })
  })

  describe('CardFooter', () => {
    it('should render with default props', () => {
      render(<CardFooter data-testid="card-footer">Footer content</CardFooter>)
      
      const footer = screen.getByTestId('card-footer')
      expect(footer).toBeInTheDocument()
      expect(footer).toHaveTextContent('Footer content')
    })

    it('should apply custom className', () => {
      render(<CardFooter className="custom-footer" data-testid="card-footer">Content</CardFooter>)
      
      const footer = screen.getByTestId('card-footer')
      expect(footer).toHaveClass('custom-footer')
    })
  })

  describe('Card Composition', () => {
    it('should render complete card structure', () => {
      render(
        <Card data-testid="complete-card">
          <CardHeader>
            <CardTitle>Test Title</CardTitle>
            <CardDescription>Test Description</CardDescription>
          </CardHeader>
          <CardContent>
            <p>Test content</p>
          </CardContent>
          <CardFooter>
            <button>Test Button</button>
          </CardFooter>
        </Card>
      )
      
      const card = screen.getByTestId('complete-card')
      expect(card).toBeInTheDocument()
      
      expect(screen.getByText('Test Title')).toBeInTheDocument()
      expect(screen.getByText('Test Description')).toBeInTheDocument()
      expect(screen.getByText('Test content')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Test Button' })).toBeInTheDocument()
    })
  })
})