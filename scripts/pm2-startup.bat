@echo off
:: Wait 15 seconds for network to be ready after boot
timeout /t 15 /nobreak > nul

:: Start all PM2 processes
cd /d "C:\Users\HP\cafe-buddy"
npx pm2 resurrect
npx pm2 start ecosystem.config.js

:: Save state
npx pm2 save
