import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { App } from './App'

describe('App', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input)
        const json = () => {
          if (url.includes('/profile/me')) {
            return Promise.resolve({
              id: 'profile-1',
              email: 'demo@poopr.local',
              display_name: 'Demo',
              avatar_url: null,
              timezone: 'America/Los_Angeles',
            })
          }
          if (url.includes('/poop-logs')) return Promise.resolve([])
          if (url.includes('/reports/me')) {
            return Promise.resolve({
              total_count: 0,
              current_streak_days: 0,
              average_per_week: 0,
              daily_counts: [],
              hourly_distribution: [],
            })
          }
          if (url.includes('/groups')) return Promise.resolve([])
          return Promise.resolve({})
        }
        return { ok: true, status: 200, json } as Response
      }),
    )
  })

  it('renders the mobile-first log action', async () => {
    render(<App />)
    expect(screen.getByRole('button', { name: /log poop now/i })).toBeTruthy()
  })
})

