import { describe, it, expect } from 'vitest'
import { FIRE_SECONDS, fireFrame, fireText } from '../src/model/fire'

describe('fireFrame', () => {
  it('is inactive before the start and after the minimum display time', () => {
    expect(fireFrame(-1, false).active).toBe(false)
    expect(fireFrame(FIRE_SECONDS + 0.01, false).active).toBe(false)
    expect(fireFrame(FIRE_SECONDS - 0.01, false).active).toBe(true)
  })
  it('flashes brightest at the start and decays', () => {
    const a = fireFrame(0.02, false), b = fireFrame(0.8, false)
    expect(a.flash).toBeGreaterThan(0.8)
    expect(b.flash).toBeLessThan(a.flash)
    expect(b.beam.opacity).toBeLessThan(a.beam.opacity)
  })
  it('expands the disc and rings over time', () => {
    expect(fireFrame(0.9, false).disc.scale).toBeGreaterThan(fireFrame(0.1, false).disc.scale)
    expect(fireFrame(0.9, false).disc.scale).toBeGreaterThan(4)
  })
  it('shows the label for the whole display time, fading only at the end', () => {
    expect(fireFrame(0.5, false).label.opacity).toBeGreaterThan(0.95)
    expect(fireFrame(1.5, false).label.opacity).toBeGreaterThan(0.95)
    expect(fireFrame(FIRE_SECONDS - 0.05, false).label.opacity).toBeLessThan(0.3)
  })
  it('reduced motion: a static ring and label, no flash, no change over time', () => {
    const a = fireFrame(0.1, true), b = fireFrame(1.9, true)
    expect(a.flash).toBe(0); expect(b.flash).toBe(0)
    expect(a.disc).toEqual(b.disc); expect(a.label).toEqual(b.label)
    expect(a.beam.opacity).toBe(0)
    expect(a.ring1.opacity).toBeGreaterThan(0.5)
  })
})

describe('fireText', () => {
  it('names the side', () => {
    expect(fireText('CALL')).toBe('FIRE CALL')
    expect(fireText('PUT')).toBe('FIRE PUT')
    expect(fireText(null)).toBe('FIRE')
  })
})
