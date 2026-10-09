import { describe, it, expect } from 'vitest'
import { backoffDelay } from '../src/net/socket'

describe('backoffDelay', () => {
  it('grows and caps at 15 s', () => {
    expect(backoffDelay(0, () => 1)).toBe(1000)
    expect(backoffDelay(1, () => 1)).toBe(2000)
    expect(backoffDelay(3, () => 1)).toBe(8000)
    expect(backoffDelay(10, () => 1)).toBe(15000)
  })
  it('jitters down to half', () => {
    expect(backoffDelay(2, () => 0)).toBe(2000)
  })
  it('never below 500 ms', () => {
    expect(backoffDelay(0, () => 0)).toBe(500)
  })
})
