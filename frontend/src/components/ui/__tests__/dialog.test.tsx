import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import { 
  Dialog, 
  DialogContent, 
  DialogDescription, 
  DialogFooter, 
  DialogHeader, 
  DialogTitle, 
  DialogTrigger 
} from '../dialog'

describe('Dialog Components', () => {
  describe('Dialog', () => {
    it('should render trigger and open dialog', () => {
      render(
        <Dialog>
          <DialogTrigger>Open Dialog</DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Test Dialog</DialogTitle>
              <DialogDescription>This is a test dialog</DialogDescription>
            </DialogHeader>
            <div>Dialog content</div>
            <DialogFooter>
              <button>Close</button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )
      
      const trigger = screen.getByText('Open Dialog')
      expect(trigger).toBeInTheDocument()
      
      fireEvent.click(trigger)
      
      expect(screen.getByText('Test Dialog')).toBeInTheDocument()
      expect(screen.getByText('This is a test dialog')).toBeInTheDocument()
      expect(screen.getByText('Dialog content')).toBeInTheDocument()
    })

    it('should handle controlled state', () => {
      const TestComponent = () => {
        const [open, setOpen] = React.useState(false)
        
        return (
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger>Open Dialog</DialogTrigger>
            <DialogContent>
              <DialogTitle>Controlled Dialog</DialogTitle>
              <button onClick={() => setOpen(false)}>Close Dialog</button>
            </DialogContent>
          </Dialog>
        )
      }
      
      render(<TestComponent />)
      
      const trigger = screen.getByText('Open Dialog')
      fireEvent.click(trigger)
      
      expect(screen.getByText('Controlled Dialog')).toBeInTheDocument()
      
      const closeButton = screen.getByText('Close Dialog')
      fireEvent.click(closeButton)
      
      expect(screen.queryByText('Controlled Dialog')).not.toBeInTheDocument()
    })
  })

  describe('DialogTrigger', () => {
    it('should render trigger button', () => {
      render(
        <Dialog>
          <DialogTrigger data-testid="dialog-trigger">Trigger</DialogTrigger>
          <DialogContent>Content</DialogContent>
        </Dialog>
      )
      
      const trigger = screen.getByTestId('dialog-trigger')
      expect(trigger).toBeInTheDocument()
      expect(trigger).toHaveTextContent('Trigger')
    })

    it('should apply custom props', () => {
      render(
        <Dialog>
          <DialogTrigger className="custom-trigger" aria-label="Custom trigger">
            Custom Trigger
          </DialogTrigger>
          <DialogContent>Content</DialogContent>
        </Dialog>
      )
      
      const trigger = screen.getByLabelText('Custom trigger')
      expect(trigger).toHaveClass('custom-trigger')
    })
  })

  describe('DialogContent', () => {
    it('should render content with proper attributes', () => {
      render(
        <Dialog defaultOpen>
          <DialogContent data-testid="dialog-content">
            <DialogTitle>Content Title</DialogTitle>
            Content body
          </DialogContent>
        </Dialog>
      )
      
      const content = screen.getByTestId('dialog-content')
      expect(content).toBeInTheDocument()
      expect(content).toHaveTextContent('Content body')
    })

    it('should apply custom className', () => {
      render(
        <Dialog defaultOpen>
          <DialogContent className="custom-content" data-testid="dialog-content">
            <DialogTitle>Title</DialogTitle>
            Content
          </DialogContent>
        </Dialog>
      )
      
      const content = screen.getByTestId('dialog-content')
      expect(content).toHaveClass('custom-content')
    })
  })

  describe('DialogHeader', () => {
    it('should render header content', () => {
      render(
        <Dialog defaultOpen>
          <DialogContent>
            <DialogHeader data-testid="dialog-header">
              <DialogTitle>Header Title</DialogTitle>
              <DialogDescription>Header Description</DialogDescription>
            </DialogHeader>
          </DialogContent>
        </Dialog>
      )
      
      const header = screen.getByTestId('dialog-header')
      expect(header).toBeInTheDocument()
      expect(header).toHaveTextContent('Header Title')
      expect(header).toHaveTextContent('Header Description')
    })
  })

  describe('DialogTitle', () => {
    it('should render title with proper semantics', () => {
      render(
        <Dialog defaultOpen>
          <DialogContent>
            <DialogTitle data-testid="dialog-title">Test Title</DialogTitle>
          </DialogContent>
        </Dialog>
      )
      
      const title = screen.getByTestId('dialog-title')
      expect(title).toBeInTheDocument()
      expect(title).toHaveTextContent('Test Title')
    })
  })

  describe('DialogDescription', () => {
    it('should render description', () => {
      render(
        <Dialog defaultOpen>
          <DialogContent>
            <DialogTitle>Title</DialogTitle>
            <DialogDescription data-testid="dialog-description">
              Test Description
            </DialogDescription>
          </DialogContent>
        </Dialog>
      )
      
      const description = screen.getByTestId('dialog-description')
      expect(description).toBeInTheDocument()
      expect(description).toHaveTextContent('Test Description')
    })
  })

  describe('DialogFooter', () => {
    it('should render footer content', () => {
      render(
        <Dialog defaultOpen>
          <DialogContent>
            <DialogTitle>Title</DialogTitle>
            <DialogFooter data-testid="dialog-footer">
              <button>Cancel</button>
              <button>Confirm</button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )
      
      const footer = screen.getByTestId('dialog-footer')
      expect(footer).toBeInTheDocument()
      expect(screen.getByText('Cancel')).toBeInTheDocument()
      expect(screen.getByText('Confirm')).toBeInTheDocument()
    })
  })
})