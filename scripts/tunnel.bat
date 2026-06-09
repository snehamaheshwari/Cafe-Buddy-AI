@echo off
:loop
echo [%DATE% %TIME%] [tunnel] killing any existing lt processes...
taskkill /F /FI "IMAGENAME eq node.exe" /FI "WINDOWTITLE eq lt*" /T 2>nul
timeout /t 8 /nobreak > nul

echo [%DATE% %TIME%] [tunnel] connecting to https://cafebuddy-ai.loca.lt
lt --port 8000 --subdomain cafebuddy-ai

echo [%DATE% %TIME%] [tunnel] lt exited, waiting 10s before retry...
timeout /t 10 /nobreak > nul
goto loop
