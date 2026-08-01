@echo off
REM Self-audit scheduled runner - SHARED (canonical: shared-modules/selfaudit).
REM
REM Why a wrapper: schtasks /TR mishandles a quoted exe path with quoted args
REM (observed: a quoted bash.exe path with -lc args parsed as invalid).
REM A single .cmd entry point removes all quoting ambiguity.
REM
REM NOTE: this file must stay CRLF + ASCII-only. It was first written as
REM UTF-8/LF and cmd.exe mangled every line ('ocal' instead of 'setlocal').
REM
REM Usage: run-selfaudit.cmd <entry-script-relative-to-repo-root> [args...]
REM   e.g. run-selfaudit.cmd scripts/checks/run_selfaudit.sh --sweep
REM The entry script is passed in (not guessed) because each repo names it
REM differently; guessing would silently run the wrong thing.

setlocal
REM Engine lives at <repo>/scripts/checks/.shared-selfaudit/ -> repo root is 3 up.
set "PROJ=%~dp0..\..\.."
set "GITBASH=C:\Program Files\Git\bin\bash.exe"
set "ENTRY=%~1"

if "%ENTRY%"=="" (
  echo [selfaudit] missing entry script argument
  exit /b 2
)
if not exist "%GITBASH%" (
  echo [selfaudit] Git Bash not found: %GITBASH%
  exit /b 2
)

cd /d "%PROJ%" || exit /b 2
if not exist "%ENTRY%" (
  echo [selfaudit] entry script not found under %PROJ%: %ENTRY%
  exit /b 2
)
if not exist logs mkdir logs

shift
set "REST=%1 %2 %3"
"%GITBASH%" -lc "bash %ENTRY% %REST% >> logs/selfaudit.log 2>&1"
exit /b %ERRORLEVEL%
