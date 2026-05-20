// Pings localhost every 4 minutes to prevent tunnel idle-timeout
// Also pings the public tunnel URL every 8 minutes to keep loca.lt warm
const http  = require('http')
const https = require('https')

const LOCAL_URL  = 'http://localhost:8000/health'
const PUBLIC_URL = 'https://cafebuddy-ai.loca.lt/health'

function ping(url) {
  const lib = url.startsWith('https') ? https : http
  const req = lib.get(url, { headers: { 'bypass-tunnel-reminder': 'true' } }, (res) => {
    res.resume()
    console.log(`[keepalive] ${url} → ${res.statusCode}`)
  })
  req.on('error', (e) => console.warn(`[keepalive] ${url} → ${e.message}`))
  req.setTimeout(8000, () => { req.destroy(); console.warn(`[keepalive] ${url} → timeout`) })
}

// Ping local every 4 min (keeps uvicorn warm, prevents OS from suspending)
setInterval(() => ping(LOCAL_URL),  4 * 60 * 1000)

// Ping public tunnel every 8 min (prevents loca.lt from dropping idle tunnel)
setInterval(() => ping(PUBLIC_URL), 8 * 60 * 1000)

// First pings immediately
ping(LOCAL_URL)
setTimeout(() => ping(PUBLIC_URL), 10000)

console.log('[keepalive] running — local ping every 4 min, tunnel ping every 8 min')
