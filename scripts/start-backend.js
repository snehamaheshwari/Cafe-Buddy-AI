// Spawns uvicorn and forwards stdio — PM2 manages restart on exit
const { spawn } = require('child_process')
const path = require('path')

const cwd = path.join(__dirname, '..', 'backend')
const proc = spawn('python', [
  '-m', 'uvicorn', 'main:app',
  '--host', '0.0.0.0',
  '--port', '8000',
  '--timeout-keep-alive', '300',
], {
  cwd,
  stdio: 'inherit',
  shell: false,
})

proc.on('error', (err) => { console.error('[backend] spawn error:', err.message); process.exit(1) })
proc.on('exit',  (code) => { console.log(`[backend] exited with code ${code}`); process.exit(code ?? 1) })
