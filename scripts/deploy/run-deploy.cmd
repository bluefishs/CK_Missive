@echo off
REM CK_Missive production deploy runner (scheduled).
REM
REM Why a .cmd wrapper: schtasks mishandles a quoted exe path with quoted
REM args. Same rationale as scripts/checks/.shared-selfaudit/run-selfaudit.cmd.
REM
REM NOTE: this file must stay CRLF + ASCII-only. run-selfaudit.cmd was first
REM written as UTF-8/LF and cmd.exe mangled every line.
REM
REM Usage: run-deploy.cmd [extra deploy-public.sh args]
REM Log:   backend/logs/deploy_*.log (persistent, container-mounted)

setlocal
set "PROJ=%~dp0..\.."
set "GITBASH=C:\Program Files\Git\bin\bash.exe"

if not exist "%GITBASH%" (
  echo [deploy] git bash not found at %GITBASH%
  exit /b 2
)

for /f "tokens=1-3 delims=/ " %%a in ("%DATE%") do set "D=%%a%%b%%c"
set "T=%TIME::=%"
set "T=%T: =0%"
set "LOG=%PROJ%\backend\logs\deploy_%D%_%T:~0,4%.log"

echo [deploy] start %DATE% %TIME% > "%LOG%"
"%GITBASH%" -lc "cd '%PROJ%' && bash scripts/deploy/deploy-public.sh %*" >> "%LOG%" 2>&1
set RC=%ERRORLEVEL%
echo [deploy] end %DATE% %TIME% rc=%RC% >> "%LOG%"

REM Exit code is preserved so Task Scheduler's LastTaskResult is truthful.
REM A non-zero rc means deploy-public.sh's own verification failed
REM (health / build identity / public 200 / four-layer post-deploy checks).
exit /b %RC%
