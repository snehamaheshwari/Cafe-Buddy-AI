@echo off
REM ============================================================================
REM  Jenkins Local Setup Script for Windows
REM  Cafe Buddy AI — CI/CD Automation
REM  Prerequisites: Java 11+ already installed (verified: java 11.0.15)
REM ============================================================================

echo.
echo ============================================================
echo  Step 1: Download Jenkins (Latest LTS)
echo ============================================================

set JENKINS_DIR=%USERPROFILE%\jenkins
set JENKINS_JAR=%JENKINS_DIR%\jenkins.war
set JENKINS_PORT=8090

if not exist "%JENKINS_DIR%" mkdir "%JENKINS_DIR%"

echo Downloading Jenkins LTS to %JENKINS_JAR% ...
powershell -Command "Invoke-WebRequest -Uri 'https://get.jenkins.io/war-stable/latest/jenkins.war' -OutFile '%JENKINS_JAR%'"
if errorlevel 1 (
    echo [ERROR] Download failed. Check internet connection.
    pause
    exit /b 1
)

echo [OK] Jenkins downloaded.

echo.
echo ============================================================
echo  Step 2: Start Jenkins
echo ============================================================

echo Starting Jenkins on http://localhost:%JENKINS_PORT%
echo Jenkins home: %JENKINS_DIR%
echo.
echo NOTE: First start takes 1-2 minutes. Watch for:
echo   "Jenkins is fully up and running"
echo.

start "Jenkins" java -jar "%JENKINS_JAR%" ^
  --httpPort=%JENKINS_PORT% ^
  --JENKINS_HOME="%JENKINS_DIR%\home"

echo Jenkins starting... waiting 20 seconds for it to initialize.
timeout /t 20 /nobreak

echo Opening Jenkins in browser...
start http://localhost:%JENKINS_PORT%

echo.
echo ============================================================
echo  Step 3: First-time Setup Instructions
echo ============================================================
echo.
echo 1. Get your initial admin password:
echo    type "%JENKINS_DIR%\home\secrets\initialAdminPassword"
echo.
echo 2. In the browser:
echo    - Paste the password to unlock Jenkins
echo    - Click "Install suggested plugins"
echo    - Create your admin account
echo.
echo 3. Install additional plugins (Manage Jenkins ^> Plugins):
echo    - Blue Ocean (modern UI)
echo    - NodeJS Plugin
echo    - HTML Publisher (for Playwright reports)
echo    - GitHub Integration
echo    - Pipeline
echo.
echo 4. Configure NodeJS (Manage Jenkins ^> Tools ^> NodeJS):
echo    - Name: NodeJS-22
echo    - Version: 22.x
echo    - Check "Install automatically"
echo.
echo 5. Add credentials (Manage Jenkins ^> Credentials ^> Global):
echo    - Kind: Secret text
echo    - ID: impasto-cafe-password
echo    - Secret: ImpastoCafe@123
echo.
echo    - Kind: Secret text
echo    - ID: system-admin-password
echo    - Secret: cafe123
echo.
echo 6. Create the Pipeline job:
echo    - New Item ^> Pipeline
echo    - Name: cafe-buddy-e2e
echo    - Pipeline Definition: Pipeline script from SCM
echo    - SCM: Git
echo    - Repository URL: https://github.com/snehamaheshwari/Cafe-Buddy-AI
echo    - Script Path: e2e/Jenkinsfile
echo.
echo ============================================================
echo  To stop Jenkins later:
echo    taskkill /F /FI "WINDOWTITLE eq Jenkins"
echo ============================================================
echo.
pause
