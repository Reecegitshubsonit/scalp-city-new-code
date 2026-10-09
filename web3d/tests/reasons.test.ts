import { describe, it, expect } from 'vitest'
import { plainReason } from '../src/model/reasons'

describe('plainReason', () => {
  it('translates known codes', () => {
    expect(plainReason('CHOP_SQUEEZE')).toMatch(/chop/i)
    expect(plainReason('DAILY_GOAL')).toMatch(/goal/i)
  })
  it('degrades to the code text for unknown or empty codes', () => {
    expect(plainReason('SOMETHING_NEW')).toBe('SOMETHING_NEW')
    expect(plainReason('')).toBe('-')
  })
})
