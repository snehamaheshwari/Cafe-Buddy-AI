module.exports = {
  apps: [
    {
      name: 'cafe-backend',
      script: './scripts/start-backend.js',
      cwd: 'C:/Users/HP/cafe-buddy',
      watch: false,
      autorestart: true,
      restart_delay: 2000,         // wait 2s before restart
      max_restarts: 999,
      exp_backoff_restart_delay: 100,
      log_file: 'C:/Users/HP/cafe-buddy/logs/backend.log',
      error_file: 'C:/Users/HP/cafe-buddy/logs/backend-err.log',
      merge_logs: true,
      time: true,
    },
    {
      name: 'cafe-tunnel',
      script: './scripts/start-tunnel.js',
      cwd: 'C:/Users/HP/cafe-buddy',
      watch: false,
      autorestart: true,
      restart_delay: 4000,         // wait 4s so loca.lt releases the subdomain
      max_restarts: 999,
      exp_backoff_restart_delay: 200,
      log_file: 'C:/Users/HP/cafe-buddy/logs/tunnel.log',
      error_file: 'C:/Users/HP/cafe-buddy/logs/tunnel-err.log',
      merge_logs: true,
      time: true,
    },
    {
      name: 'cafe-keepalive',
      script: './scripts/keepalive.js',
      cwd: 'C:/Users/HP/cafe-buddy',
      watch: false,
      autorestart: true,
      restart_delay: 5000,
      max_restarts: 999,
      log_file: 'C:/Users/HP/cafe-buddy/logs/keepalive.log',
      merge_logs: true,
      time: true,
    },
  ],
}
