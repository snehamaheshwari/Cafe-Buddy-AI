// Localtunnel with auto-reconnect — keeps cafebuddy-ai.loca.lt permanently.
// Uses the programmatic API so it reconnects without PM2 needing to restart.
const localtunnel = require('C:/Users/HP/AppData/Roaming/npm/node_modules/localtunnel')

const PORT      = 8000
const SUBDOMAIN = 'cafebuddy-ai'
const URL       = `https://${SUBDOMAIN}.loca.lt`

let retryDelay  = 3000   // starts at 3 s, backs off to 30 s max
let activeTunnel = null

function log(msg) {
  const ts = new Date().toISOString().replace('T', ' ').slice(0, 19)
  console.log(`[${ts}] [tunnel] ${msg}`)
}

async function connect() {
  log(`connecting → ${URL}`)
  try {
    const tunnel = await localtunnel({ port: PORT, subdomain: SUBDOMAIN })
    activeTunnel = tunnel
    retryDelay   = 3000   // reset backoff on success
    log(`UP — your url is: ${tunnel.url}`)

    tunnel.on('error', (err) => {
      log(`error: ${err.message} — reconnecting in ${retryDelay / 1000}s`)
      tunnel.close()
    })

    tunnel.on('close', () => {
      activeTunnel = null
      log(`closed — reconnecting in ${retryDelay / 1000}s`)
      setTimeout(connect, retryDelay)
      retryDelay = Math.min(retryDelay * 2, 30000)
    })

  } catch (err) {
    log(`failed to connect: ${err.message} — retrying in ${retryDelay / 1000}s`)
    setTimeout(connect, retryDelay)
    retryDelay = Math.min(retryDelay * 2, 30000)
  }
}

// Health-check: if tunnel is open but loca.lt starts returning 503/offline,
// force a reconnect so the subdomain is re-claimed.
setInterval(async () => {
  if (!activeTunnel) return
  try {
    const http = require('http')
    await new Promise((resolve, reject) => {
      const req = http.get(`http://localhost:${PORT}/api/health`, { timeout: 4000 }, (res) => {
        res.resume()
        resolve(res.statusCode)
      })
      req.on('error', reject)
      req.on('timeout', () => { req.destroy(); reject(new Error('timeout')) })
    })
  } catch {
    log('health-check failed — backend may be down; keeping tunnel open')
  }
}, 60000)

// Brief delay on first start so the backend is ready
setTimeout(connect, 3000)

// Keep the process alive (the tunnel callbacks above manage the lifecycle)
process.on('SIGINT',  () => { if (activeTunnel) activeTunnel.close(); process.exit(0) })
process.on('SIGTERM', () => { if (activeTunnel) activeTunnel.close(); process.exit(0) })
