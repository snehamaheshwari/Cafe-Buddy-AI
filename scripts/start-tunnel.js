// Cloudflare Quick Tunnel — no account needed, port-443-only, rock-solid.
// Much more reliable than localtunnel (which used random high ports that
// firewalls/ISPs block). Cloudflare only needs outbound port 443.
//
// The URL is a random *.trycloudflare.com subdomain that stays fixed for
// the lifetime of this process. On restart it gets a new URL — the log
// clearly prints it so teammates always know the current address.
//
// For a PERMANENT fixed URL: sign up free at ngrok.com, get a static domain,
// add authtoken, then switch the script to use ngrok.

const { spawn } = require('child_process')
const path      = require('path')

const PORT          = 8000
const CLOUDFLARED   = path.join(__dirname, '..', 'cloudflared.exe')

let proc        = null
let retryDelay  = 5000
let retryTimer  = null
let isStarting  = false

function log(msg) {
  const ts = new Date().toISOString().replace('T', ' ').slice(0, 19)
  console.log(`[${ts}] [tunnel] ${msg}`)
}

function scheduleReconnect(reason) {
  if (retryTimer || isStarting) return
  log(`${reason} — reconnecting in ${retryDelay / 1000}s`)
  retryTimer = setTimeout(() => { retryTimer = null; start() }, retryDelay)
  retryDelay = Math.min(retryDelay * 2, 60000)
}

function start() {
  if (isStarting) return
  isStarting = true

  log(`starting Cloudflare tunnel → localhost:${PORT}`)

  proc = spawn(CLOUDFLARED, [
    'tunnel', '--url', `http://localhost:${PORT}`,
    '--no-autoupdate',
  ], { stdio: ['ignore', 'pipe', 'pipe'] })

  let urlFound = false

  function parseLine(line) {
    // cloudflared prints the URL to stderr in a line like:
    //   https://xxxx-xxxx.trycloudflare.com
    const match = line.match(/https:\/\/[a-z0-9\-]+\.trycloudflare\.com/)
    if (match && !urlFound) {
      urlFound = true
      retryDelay = 5000   // reset backoff
      log(`\n  ┌─────────────────────────────────────────────────────┐`)
      log(`  │  🌐 PUBLIC URL: ${match[0].padEnd(35)} │`)
      log(`  │  Share this link with your team!                    │`)
      log(`  └─────────────────────────────────────────────────────┘`)
    }
    if (line.includes('ERR') || line.includes('error')) {
      log(`cloudflare: ${line.trim()}`)
    }
  }

  proc.stdout.on('data', d => d.toString().split('\n').filter(Boolean).forEach(parseLine))
  proc.stderr.on('data', d => d.toString().split('\n').filter(Boolean).forEach(parseLine))

  proc.on('spawn', () => {
    isStarting = false
    log('cloudflared process started — waiting for URL…')
  })

  proc.on('error', (err) => {
    isStarting = false
    proc = null
    log(`failed to start: ${err.message}`)
    scheduleReconnect('spawn error')
  })

  proc.on('exit', (code, signal) => {
    isStarting = false
    proc = null
    log(`exited (code=${code} signal=${signal})`)
    scheduleReconnect('process exited')
  })
}

function shutdown() {
  if (retryTimer) clearTimeout(retryTimer)
  if (proc) proc.kill()
  process.exit(0)
}
process.on('SIGINT',  shutdown)
process.on('SIGTERM', shutdown)

// Start after backend has had time to boot
setTimeout(start, 3000)

// Keep the process alive
setInterval(() => {}, 1 << 30)
