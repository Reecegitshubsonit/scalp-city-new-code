// Mock of the Scalp City engine API (snapshot, websocket stream, pause). Synthetic data only.
import http from 'node:http'
import { WebSocketServer } from 'ws'

const args = process.argv.slice(2)
const opt = (n, d) => { const i = args.indexOf('--' + n); return i >= 0 ? args[i + 1] : d }
const PORT = +opt('port', 8000)
const SPEED = +opt('speed', 1)
const WITH_SIDE = !args.includes('--no-side')
const BAR_MS = 2000 / SPEED
let rs = +opt('seed', 1)
const rand = () => { rs |= 0; rs = (rs + 0x6d2b79f5) | 0; let t = Math.imul(rs ^ (rs >>> 15), 1 | rs); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296 }
const gauss = () => Math.sqrt(-2 * Math.log(rand() || 1e-9)) * Math.cos(2 * Math.PI * rand())

const TK = { QQQ: { p: 620, vol: 0.25 }, SPY: { p: 690, vol: 0.3 }, IWM: { p: 240, vol: 0.15 } }
for (const t of Object.values(TK)) Object.assign(t, { vwap: t.p, ema9: t.p, ema21: t.p, ema50: t.p })
const TRIGGERS = ['VWAP', 'EMA50', 'RANGE']
const OUTCOMES = ['win', 'loss', 'win', 'win', 'loss', 'time']
let seq = 0, bar = 0, down = false

const bots = {}
let idx = 0
for (const ticker of Object.keys(TK)) for (const trigger of TRIGGERS) {
  const id = `${ticker}-${trigger}`
  bots[id] = {
    bot: id, ticker, trigger, state: 'idle', reason_code: 'NO_DATA', reason_text: 'no events yet', charge: null, side: null,
    inputs: {}, time: null, realised: 0, trades: 0, paused: false, stale: false,
    phase: trigger === 'RANGE' ? 'pre' : 'watch', t: 0, watchLen: 3 + ((idx * 2) % 7), pos: null, outcomeIdx: idx % OUTCOMES.length,
    rejectFirst: id === 'SPY-EMA50', lockedFor: 0,
  }
  idx++
}

const iso = b => { const m = 571 + (b % 390); return `2026-10-08T${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}:00-04:00` }
const pnlDay = b => +(b.realised + (b.pos ? b.pos.pnl : 0)).toFixed(2)

const wss = new WebSocketServer({ noServer: true })
const send = (ws, o) => { if (ws.readyState === 1) ws.send(JSON.stringify(o)) }

function inputsFor(b) {
  const t = TK[b.ticker]
  const atr = +(t.vol * 1.4).toFixed(3)
  const i = { price: +t.p.toFixed(2), vwap: +t.vwap.toFixed(2), ema9: +t.ema9.toFixed(2), ema21: +t.ema21.toFixed(2), ema50: +t.ema50.toFixed(2), atr }
  let level = b.trigger === 'VWAP' ? i.vwap : b.trigger === 'EMA50' ? i.ema50 : null
  if (b.phase === 'forming' && level != null) {
    // keep price on the side of the level that matches the pending cross: CALL = price below level
    const gap = (1 - b.charge / 100) * atr * 1.2 + 0.01
    level = +(b.side === 'CALL' ? i.price + gap : i.price - gap).toFixed(2)
    if (b.trigger === 'VWAP') i.vwap = level; else i.ema50 = level
  }
  i.distance_atr = level != null ? +(Math.abs(i.price - level) / atr).toFixed(3) : +(rand() * 1.5).toFixed(3)
  return i
}

function emit(b, kind, extra = {}) {
  const ev = {
    seq: ++seq, time: iso(bar), mode: 'mock', bot: b.bot, ticker: b.ticker, kind, state: b.state,
    reason_code: b.reason_code, reason_text: b.reason_text, inputs: (b.inputs = inputsFor(b)), charge_pct: b.charge,
    pnl_day: pnlDay(b), trades: b.trades, paused: b.paused, ...extra,
  }
  if (WITH_SIDE && (kind === 'tick' || kind === 'state_change')) ev.side = b.side
  b.time = ev.time
  for (const c of wss.clients) send(c, { type: 'event', event: ev })
  return ev
}

const set = (b, state, code, text, charge = null) => { b.state = state; b.reason_code = code; b.reason_text = text; b.charge = charge }
const row = b => ({
  bot: b.bot, ticker: b.ticker, state: b.state, reason_code: b.reason_code, reason_text: b.reason_text, charge_pct: b.charge,
  inputs: b.inputs, time: b.time, pnl_day: pnlDay(b), trades: b.trades, paused: b.paused, ...(WITH_SIDE ? { side: b.side } : {}),
})
const snapshot = () => ({ bots: Object.fromEntries(Object.values(bots).map(b => [b.bot, row(b)])), last_seq: seq })

function setPaused(b, paused) {
  b.paused = paused
  b.side = null
  if (paused) set(b, 'paused', 'PAUSED', 'paused by user')
  else { b.pos = null; b.phase = 'watch'; b.t = 0; set(b, 'idle', 'WATCHING', 'resumed, watching') }
  emit(b, 'control')
}

function startTrade(b) {
  const tk = TK[b.ticker]
  if (b.rejectFirst) {
    b.rejectFirst = false
    set(b, 'idle', 'ORDER_FAILED', 'entry order rejected by broker'); b.side = null
    emit(b, 'order_rejected'); b.phase = 'watch'; b.t = 0; b.watchLen = 4
    return
  }
  const outcome = OUTCOMES[b.outcomeIdx++ % OUTCOMES.length]
  b.pos = { pnl: 0, outcome, len: 6 + Math.floor(rand() * 5) }
  set(b, 'fired', 'SIGNAL', `${b.side} signal at ${tk.p.toFixed(2)}`, 100)
  emit(b, 'state_change')
  emit(b, 'order_sent', { contract: `${b.ticker}261009${b.side === 'CALL' ? 'C' : 'P'}00${Math.round(tk.p)}000`, qty: 10 })
  b.reason_code = 'ENTRY_FILL'; b.reason_text = 'entry filled'
  emit(b, 'fill', { fill_price: +(tk.p + 0.02).toFixed(2), fill_source: rand() > 0.5 ? 'broker' : 'modeled', qty: 10 })
  b.phase = 'managing'; b.t = 0
}

function finishTrade(b) {
  const o = b.pos.outcome
  const final = o === 'win' ? 180 + rand() * 300 : o === 'loss' ? -(60 + rand() * 60) : 20 + rand() * 40
  const code = o === 'win' ? (rand() > 0.5 ? 'EXIT_TARGET' : 'EXIT_LOCK') : o === 'loss' ? 'EXIT_STOP' : 'EXIT_TIME'
  b.pos.pnl = +final.toFixed(2)
  set(b, 'exiting', code, `${code.toLowerCase().replace('_', ' ')}, P&L ${b.pos.pnl}`)
  emit(b, 'state_change')
  emit(b, 'order_sent', { qty: 10 })
  b.reason_code = 'EXIT_FILL'; b.reason_text = 'exit filled'
  emit(b, 'fill', { fill_price: +TK[b.ticker].p.toFixed(2), fill_source: 'modeled', qty: 10 })
  b.realised = +(b.realised + b.pos.pnl).toFixed(2); b.trades++
  const pnl = b.pos.pnl; b.pos = null
  emit(b, 'trade_closed', { pnl })
  b.side = null
  if (b.bot === 'QQQ-EMA50' && b.trades >= 2) {
    b.lockedFor = 25; b.phase = 'locked'; b.t = 0
    set(b, 'locked', 'DAILY_GOAL', 'daily goal reached, done for today')
  } else { b.phase = 'cooldown'; b.t = 0; set(b, 'cooldown', 'COOLDOWN', 'cooling down after trade') }
  emit(b, 'state_change')
}

function stepBot(b) {
  if (b.paused || b.stale) { emit(b, 'tick'); return }
  b.t++
  switch (b.phase) {
    case 'pre':
      set(b, 'idle', 'OUTSIDE_WINDOW', 'before trading window')
      if (b.t >= 4) { b.phase = 'rangeform'; b.t = 0 }
      break
    case 'rangeform':
      set(b, 'idle', 'RANGE_FORMING', 'opening range still forming')
      if (b.t >= 4) { b.phase = 'watch'; b.t = 0; b.watchLen = 3 }
      break
    case 'watch':
      if (b.trigger === 'VWAP' && b.t === 2) set(b, 'idle', 'CHOP_SQUEEZE', 'EMA9/EMA21 squeezed, skipping VWAP cross')
      else set(b, 'idle', 'WATCHING', 'watching for a signal', b.trigger === 'RANGE' ? null : Math.round(5 + rand() * 10))
      if (b.t >= b.watchLen) { b.phase = 'forming'; b.t = 0; b.side = rand() > 0.5 ? 'CALL' : 'PUT' }
      break
    case 'forming': {
      const c = Math.min(100, 15 + b.t * 11)
      set(b, 'forming', 'WATCHING', `${c}% charged`, c)
      if (b.t >= 8) { b.charge = 100; startTrade(b) }
      break
    }
    case 'managing': {
      const o = b.pos.outcome, k = b.t / b.pos.len
      b.pos.pnl = +((o === 'loss' ? -90 : o === 'win' ? 250 : 40) * k + gauss() * 15).toFixed(2)
      set(b, 'managing', 'HOLDING', `holding ${b.side}, open P&L ${b.pos.pnl}`)
      if (b.t >= b.pos.len) finishTrade(b)
      break
    }
    case 'cooldown':
      set(b, 'cooldown', 'COOLDOWN', 'cooling down after trade')
      if (b.t >= 4) { b.phase = 'watch'; b.t = 0; b.watchLen = 5 + (b.trades % 4); set(b, 'idle', 'WATCHING', 'watching for a signal'); emit(b, 'state_change') }
      break
    case 'locked':
      set(b, 'locked', 'DAILY_GOAL', 'daily goal reached, done for today')
      if (--b.lockedFor <= 0) { b.phase = 'watch'; b.t = 0; b.watchLen = 4; b.realised = 0; b.trades = 0; set(b, 'idle', 'WATCHING', 'new session, watching'); emit(b, 'state_change') }
      break
  }
  emit(b, 'tick')
}

function scripted() {
  const m = bar % 120
  const sv = bots['SPY-VWAP']
  if (m === 50) { sv.stale = true; sv.side = null; set(sv, 'stale', 'STALE_DATA', 'no quotes for 60 s'); emit(sv, 'feed_stale'); emit(sv, 'state_change') }
  if (m === 58) { sv.stale = false; sv.pos = null; sv.phase = 'watch'; sv.t = 0; set(sv, 'idle', 'WATCHING', 'feed fresh again'); emit(sv, 'feed_fresh'); emit(sv, 'state_change') }
  const ie = bots['IWM-EMA50']
  if (m === 20 && !ie.paused) setPaused(ie, true)
  if (m === 35 && ie.paused) setPaused(ie, false)
  if (m === 90) goDown()
}

function goDown() {
  down = true
  for (const c of wss.clients) c.terminate()
  console.log('mock: simulated disconnect for 4 s')
  setTimeout(() => { down = false; console.log('mock: back up') }, 4000)
}

function advance() {
  bar++
  for (const t of Object.values(TK)) {
    t.p = +(t.p + gauss() * t.vol * 0.4).toFixed(3)
    t.vwap += (t.p - t.vwap) * 0.02; t.ema9 += (t.p - t.ema9) * 0.2; t.ema21 += (t.p - t.ema21) * 0.09; t.ema50 += (t.p - t.ema50) * 0.04
  }
  scripted()
  for (const b of Object.values(bots)) stepBot(b)
}
setInterval(advance, BAR_MS)

const readBody = req => new Promise(res => { let d = ''; req.on('data', c => (d += c)); req.on('end', () => res(d)) })
const server = http.createServer(async (req, res) => {
  const h = { 'content-type': 'application/json', 'access-control-allow-origin': '*', 'access-control-allow-headers': 'content-type' }
  if (down) { res.writeHead(503, h); return res.end('{"error":"down"}') }
  if (req.method === 'OPTIONS') { res.writeHead(204, h); return res.end() }
  if (req.method === 'GET' && req.url === '/snapshot') { res.writeHead(200, h); return res.end(JSON.stringify(snapshot())) }
  if (req.method === 'POST' && req.url === '/control/pause') {
    let body
    try { body = JSON.parse(await readBody(req)) } catch { res.writeHead(400, h); return res.end('{"error":"bad json"}') }
    const b = bots[body.bot]
    if (!b || typeof body.paused !== 'boolean') { res.writeHead(404, h); return res.end('{"detail":"unknown bot"}') }
    setPaused(b, body.paused)
    res.writeHead(200, h); return res.end(JSON.stringify({ ok: true, bot: body.bot, paused: body.paused }))
  }
  res.writeHead(404, h); res.end('{}')
})
server.on('upgrade', (req, socket, head) => {
  if (down || req.url !== '/ws') return socket.destroy()
  wss.handleUpgrade(req, socket, head, ws => { wss.emit('connection', ws); send(ws, { type: 'snapshot', ...snapshot() }) })
})
server.listen(PORT, '127.0.0.1', () => console.log(`mock stream on http://127.0.0.1:${PORT}  speed x${SPEED}  side=${WITH_SIDE}`))
