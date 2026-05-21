// Robust localtunnel with strict single-connection guarantee.
// Uses an 'isConnecting' mutex so error + close events never schedule
// two simultaneous reconnects (the original cause of random subdomains).
const localtunnel = require('C:/Users/HP/AppData/Roaming/npm/node_modules/localtunnel')

const PORT      = 8000
const SUBDOMAIN = 'cafebuddy-ai'
const URL       = `https://${SUBDOMAIN}.loca.lt`

const MIN_DELAY = 5000    // 5 s minimum between attempts
const MAX_DELAY = 60000   // 60 s maximum backoff

let activeTunnel  = null
let isConnecting  = false   // mutex — only one connect() in-flight at a time
let retryDelay    = MIN_DELAY
let retryTimer    = null

function log(msg) {
  const ts = new Date().toISOString().replace('T', ' ').slice(0, 19)
  console.log(`[${ts}] [tunnel] ${msg}`)
}

function scheduleReconnect() {
  // If already connecting or a timer is already pending, do nothing.
  if (isConnecting || retryTimer) return
  log(`reconnecting in ${retryDelay / 1000}s…`)
  retryTimer = setTimeout(() => {
    retryTimer = null
    connect()
  }, retryDelay)
  retryDelay = Math.min(retryDelay * 2, MAX_DELAY)
}

async function connect() {
  if (isConnecting) return          // strict mutex
  isConnecting = true

  log(`connecting → ${URL}`)
  try {
    const tunnel = await localtunnel({ port: PORT, subdomain: SUBDOMAIN })
    activeTunnel = tunnel
    retryDelay   = MIN_DELAY        // reset backoff on success
    isConnecting = false
    log(`UP — your url is: ${tunnel.url}`)

    if (tunnel.url !== URL) {
      // Subdomain was taken — close and retry so we always serve the right URL
      log(`wrong subdomain assigned (${tunnel.url}) — retrying to claim ${URL}`)
      tunnel.close()
      return                        // 'close' event will call scheduleReconnect
    }

    tunnel.on('error', (err) => {
      log(`error: ${err.message}`)
      // Do NOT call tunnel.close() here — that fires 'close' again.
      // Just let the tunnel die; 'close' will handle the reconnect.
    })

    tunnel.on('close', () => {
      activeTunnel = null
      log('connection closed')
      scheduleReconnect()
    })

  } catch (err) {
    isConnecting = false
    activeTunnel = null
    log(`failed: ${err.message}`)
    scheduleReconnect()
  }
}

// Periodic health-check — if backend stops responding, log a warning
// (don't kill the tunnel; the backend will restart on its own via PM2)
setInterval(async () => {
  if (!activeTunnel) return
  try {
    const http = require('http')
    await new Promise((resolve, reject) => {
      const req = http.get(`http://localhost:${PORT}/health`, { timeout: 4000 }, (res) => {
        res.resume(); resolve(res.statusCode)
      })
      req.on('error', reject)
      req.on('timeout', () => { req.destroy(); reject(new Error('timeout')) })
    })
  } catch {
    log('health-check failed — backend may be temporarily down')
  }
}, 60000)

// Graceful shutdown
function shutdown() {
  if (retryTimer) clearTimeout(retryTimer)
  if (activeTunnel) activeTunnel.close()
  process.exit(0)
}
process.on('SIGINT',  shutdown)
process.on('SIGTERM', shutdown)

// Start after a short delay to let the backend fully boot
setTimeout(connect, 4000)

// Keep the process alive
setInterval(() => {}, 1 << 30)
