@echo off
setlocal
REM Run one scrape per re-thinkingthefuture page (pages 2-10).
REM Each run uses --url so one run = one page. Waits 30s between runs.

cd /d "%~dp0.."
set BASE=https://www.re-thinkingthefuture.com/top-architects/top-architecture-firms-architects-in-new-york
set WAIT=30

echo Re-thinkingthefuture batch: pages 2-10, %WAIT%s between runs.
echo.

for %%p in (2 3 4 5 6 7 8 9 10) do (
  echo === Page %%p ===
  ".\venv\Scripts\python.exe" main.py --sources rethinkingthefuture --url "%BASE%/%%p/"
  if %%p LSS 10 (
    echo Waiting %WAIT%s before next page...
    timeout /t %WAIT% /nobreak >nul
  )
)

echo.
echo Batch finished.
endlocal
