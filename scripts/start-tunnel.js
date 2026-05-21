/**
 * Tunnel keeper — cafebuddy-ai.loca.lt
 *
 * Windows fix: uses `taskkill /F /T /PID` to kill the ENTIRE process tree
 * (cmd.exe → lt node.exe) when PM2 stops/restarts this wrapper. Without
 * this, the inner lt process survives and holds the subdomain, causing the
 * next launch to get a random subdomain instead of cafebuddy-ai.
 */

const { spawn, execSync } = require('child_process')

const LT_CMD = 'C:/Users/HP/AppData/Roaming/npm/lt.cmd'
const PORT   = 8000
const SUB    = 'cafebuddy-ai'

function ts() { return new Date().toISOString().replace('T',' ').slice(0,19) }
function log(m) { console.log(`[${ts()}] [tunnel] ${m}`) }

// Kill any lingering lt processes from previous runs before claiming subdomain
function killAllLt() {
  try {
    execSync('taskkill /F /FI "WINDOWTITLE eq lt*" /T 2>nul', { shell: true })
  } catch (_) {}
  try {
    execSync('taskkill /F /FI "IMAGENAME eq lt.exe" /T 2>nul', { shell: true })
  } catch (_) {}
}

killAllLt()
log(`connecting → https://${SUB}.loca.lt`)

const lt = spawn(LT_CMD, ['--port', String(PORT), '--subdomain', SUB], {
  stdio: ['ignore', 'pipe', 'pipe'],
  shell: true,
  windowsHide: true,
  detached: false,
})

const ltPid = lt.pid

lt.stdout.on('data', d => { const s = d.toString().trim(); if(s) log(s) })
lt.stderr.on('data', d => { const s = d.toString().trim(); if(s) log(s) })

lt.on('error', err => log(`error: ${err.message}`))

lt.on('exit', (code, signal) => {
  log(`lt exited (code=${code} signal=${signal}) — PM2 restarts in 10s`)
  process.exit(1)
})

// SIGTERM from PM2: kill entire process tree, then exit
function shutdown(sig) {
  log(`received ${sig} — killing lt process tree (pid ${ltPid})`)
  try {
    execSync(`taskkill /F /T /PID ${ltPid} 2>nul`, { shell: true })
  } catch (_) {}
  setTimeout(() => process.exit(0), 300)
}
process.on('SIGTERM', () => shutdown('SIGTERM'))
process.on('SIGINT',  () => shutdown('SIGINT'))
