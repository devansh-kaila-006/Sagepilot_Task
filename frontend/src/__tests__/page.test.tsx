import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import Dashboard from '@/app/page'

// Mock the API calls
vi.mock('@/lib/api', () => ({
  getRuns: vi.fn().mockResolvedValue([
    {
      id: 'run-1',
      order_id: 'ORD-123',
      status: 'active',
      created_at: new Date().toISOString()
    }
  ]),
  getSupervisors: vi.fn().mockResolvedValue([
    {
      id: 1,
      name: 'Test Supervisor',
      base_instruction: 'Test instructions'
    }
  ]),
  createRun: vi.fn().mockResolvedValue({}),
  createSupervisor: vi.fn().mockResolvedValue({})
}))

describe('Dashboard Page', () => {
  it('renders loading state initially', () => {
    render(<Dashboard />)
    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  it('renders supervisors and runs after loading', async () => {
    render(<Dashboard />)
    
    await waitFor(() => {
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
    })
    
    expect(screen.getByText('Order Supervisor Platform')).toBeInTheDocument()
    expect(screen.getByText('Test Supervisor')).toBeInTheDocument()
    expect(screen.getByText('ORD-123')).toBeInTheDocument()
  })
})
