@echo off
REM UI self-audit scheduled runner (2026-07-31)
REM
REM Why a wrapper: schtasks /TR mishandles a quoted exe path with quoted args
REM (observed: a quoted bash.exe path with -lc args parsed as invalid).
REM A single .cmd entry point removes all quoting ambiguity.
REM
REM NOTE: this file must stay CRLF + ASCII-only. It was first written as
REM UTF-8/LF and cmd.exe mangled every line ('ocal' instead of 'setlocal').
REM
REM Usage: run-ui-smoke.cmd            -> flow checks (depth)
REM        run-ui-smoke.cmd --sweep    -> page sweep (breadth)

setlocal
set "PROJ=%~dp0..\.."
set "BASH=C:\Program Files\Git\bin\bash.exe"

if not exist "%BASH%" (
  echo [ui-smoke] Git Bash not found: %BASH%
  exit /b 1
)

cd /d "%PROJ%" || exit /b 1
if not exist logs mkdir logs

"%BASH%" -lc "bash scripts/checks/run_ui_smoke.sh %* >> logs/ui_smoke.log 2>&1"
exit /b %ERRORLEVEL%
