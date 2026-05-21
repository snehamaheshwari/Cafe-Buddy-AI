/**
 * Ngrok tunnel — daunting-veto-snap.ngrok-free.dev (permanent fixed URL)
 * Port-443-only, auto-reconnects in seconds, no subdomain-reservation issues.
 */
const { spawn, execSync } = require('child_process')
const path = require('path')

const NGROK  = path.join(__dirname, '..', 'ngrok.exe')
const PORT   = 8000
const DOMAIN = 'daunting-veto-snap.ngrok-free.dev'

function ts()   { return new Date().toISOString().replace('T',' ').slice(0,19) }
function log(m) { console.log(`[${ts()}] [tunnel] ${m}`) }

log(`starting ngrok → https://${DOMAIN}`)

const proc = spawn(NGROK, [
  'http', String(PORT),
  '--url', DOMAIN,
  '--log', 'stdout',
  '--log-format', 'json',
], { stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true })

proc.stdout.on('data', (chunk) => {
  for (const line of chunk.toString().split('\n').filter(Boolean)) {
    try {
      const obj = JSON.parse(line)
      if (obj.msg === 'started tunnel') {
        log(`UP ✅  https://${DOMAIN}`)
      }
      if (obj.err && obj.err !== '<nil>') log(`error: ${obj.err}`)
      if (obj.lvl === 'error' && obj.msg)  log(`error: ${obj.msg}`)
    } catch (_) {}
  }
})

proc.stderr.on('data', d => log(`stderr: ${d.toString().trim()}`))

proc.on('error', (err) => {
  log(`failed to start: ${err.message}`)
  process.exit(1)
})

proc.on('exit', (code, signal) => {
  log(`ngrok exited (code=${code} signal=${signal}) — PM2 restarts in 5s`)
  process.exit(1)
})

function shutdown() {
  try { execSync(`taskkill /F /T /PID ${proc.pid} 2>nul`, { shell: true }) } catch (_) {}
  setTimeout(() => process.exit(0), 300)
}
process.on('SIGTERM', shutdown)
process.on('SIGINT',  shutdown)
