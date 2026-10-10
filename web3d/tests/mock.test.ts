import { describe, it, expect, beforeAll, afterAll } from 'vitest'
import { spawn, type ChildProcess } from 'node:child_process'
import WebSocket from 'ws'

const PORT = 18765
let proc: ChildProcess
const base = `http://127.0.0.1:${PORT}`
const wait = (ms: number) => new Promise(r => setTimeout(r, ms))
const post = (body: unknown) =>
  fetch(base + '/control/pause', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) })

beforeAll(async () => {
  proc = spawn('node', ['scripts/mock_stream.mjs', '--port', String(PORT), '--speed', '20'], { stdio: 'ignore' })
  for (let i = 0; i < 50; i++) { try { await fetch(base + '/snapshot'); return } catch { await wait(100) } }
})
afterAll(() => { proc.kill() })

describe('mock server', () => {
  it('serves a snapshot with 9 bots', async () => {
    const s = await (await fetch(base + '/snapshot')).json()
    expect(Object.keys(s.bots)).toHaveLength(9)
    expect(typeof s.last_seq).toBe('number')
  })
  it('serves history candles, levels and 404 for an unknown ticker', async () => {
    await wait(600)
    const h = await (await fetch(base + '/history?ticker=QQQ')).json()
    expect(h.ticker).toBe('QQQ')
    expect(h.bars.length).toBeGreaterThan(1)
    expect(h.bars[0]).toMatchObject({ open: expect.any(Number), high: expect.any(Number), low: expect.any(Number), close: expect.any(Number) })
    expect(h.bars[0].high).toBeGreaterThanOrEqual(h.bars[0].low)
    expect(h.levels.length).toBe(h.bars.length)
    expect((await fetch(base + '/history?ticker=ZZZ')).status).toBe(404)
  })
  it('serves days and a day of events for replay', async () => {
    await wait(300)
    const d = await (await fetch(base + '/days')).json()
    expect(d.days[0].events).toBeGreaterThan(0)
    const day = await (await fetch(base + '/day?day=2026-10-08&mode=mock')).json()
    expect(day.events.length).toBeGreaterThan(0); expect(typeof day.events[0].seq).toBe('number')
  })
  it('streams snapshot then events with increasing seq', async () => {
    const msgs: any[] = []
    await new Promise<void>(res => {
      const ws = new WebSocket(`ws://127.0.0.1:${PORT}/ws`)
      ws.on('message', d => { msgs.push(JSON.parse(String(d))); if (msgs.length >= 20) { ws.close(); res() } })
    })
    expect(msgs[0].type).toBe('snapshot')
    const seqs = msgs.slice(1).map(m => m.event.seq)
    expect(seqs.every((v: number, i: number) => i === 0 || v > seqs[i - 1])).toBe(true)
  })
  it('pause: 404 for unknown bot, ok + control event for known bot', async () => {
    expect((await post({ bot: 'NOPE', paused: true })).status).toBe(404)
    const seen: any[] = []
    const ws = new WebSocket(`ws://127.0.0.1:${PORT}/ws`)
    ws.on('message', d => seen.push(JSON.parse(String(d))))
    await wait(200)
    expect((await post({ bot: 'QQQ-VWAP', paused: true })).status).toBe(200)
    await wait(300)
    expect(seen.some(m => m.type === 'event' && m.event.kind === 'control' && m.event.bot === 'QQQ-VWAP' && m.event.paused === true)).toBe(true)
    ws.close()
  })
})
