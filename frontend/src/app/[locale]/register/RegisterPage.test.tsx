import { render, screen, fireEvent } from '@testing-library/react'
import RegisterPage from './page'
import React from 'react'

describe('RegisterPage', () => {
  it('renders registration form', () => {
    render(<RegisterPage />)
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
  })

  it('validates required fields', async () => {
    render(<RegisterPage />)
    fireEvent.click(screen.getByText(/create account|注册/i))
    expect(await screen.findByText(/required|必填/i)).toBeInTheDocument()
  })
}) 