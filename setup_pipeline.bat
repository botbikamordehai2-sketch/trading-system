@echo off
REM ============================================================
REM  Commoti AI — Automated Pipeline Setup (Task Scheduler)
REM  Creates 4 daily tasks. Run ONCE as Administrator.
REM  Date: 02/05/2026
REM ============================================================
chcp 65001 >nul
echo ============================================================
echo   Commoti AI — Pipeline Setup
echo   Creating 4 daily tasks in Windows Task Scheduler
echo ============================================================
echo.

set PYTHON=C:\Users\gfdh5555\AppData\Local\Programs\Python\Python312\python.exe
set PROJ=C:\Users\gfdh5555\Desktop\projects\trading-system

REM --- Task 1: NASDAQ Scanner (07:55 daily) ---
echo [1/4] NASDAQ Scanner — 07:55 daily
schtasks /create /tn "CommotiAI_NASDAQ_Scanner" /tr "%PYTHON% %PROJ%\nasdaq_scanner.py" /sc daily /st 07:55 /f
if %errorlevel% equ 0 (echo   ^✅ Created) else (echo   ^⚠️ May already exist)

REM --- Task 2: AI Daily Bias (08:00 daily) ---
echo [2/4] AI Daily Bias — 08:00 daily
schtasks /create /tn "CommotiAI_DailyBias" /tr "%PYTHON% %PROJ%\daily_bias_ai.py" /sc daily /st 08:00 /f
if %errorlevel% equ 0 (echo   ^✅ Created) else (echo   ^⚠️ May already exist)

REM --- Task 3: Research Scanner (08:40 daily) ---
echo [3/4] Research Scanner — 08:40 daily
schtasks /create /tn "CommotiAI_ResearchScanner" /tr "%PYTHON% %PROJ%\research_scanner.py" /sc daily /st 08:40 /f
if %errorlevel% equ 0 (echo   ^✅ Created) else (echo   ^⚠️ May already exist)

REM --- Task 4: Daily Review (20:30 daily) ---
echo [4/4] Daily Review — 20:30 daily
schtasks /create /tn "CommotiAI_DailyReview" /tr "%PYTHON% %PROJ%\daily_review.py" /sc daily /st 20:30 /f
if %errorlevel% equ 0 (echo   ^✅ Created) else (echo   ^⚠️ May already exist)

echo.
echo ============================================================
echo   ✅ Pipeline Setup Complete
echo.
echo   Schedule:
echo     07:55 — NASDAQ Scanner (DXY, VIX, NDX, SPX, 10Y)
echo     08:00 — AI Daily Bias (Claude API → bias.json)
echo     08:40 — Research Scanner (10 academic papers)
echo     20:30 — Daily Review (P^&L report → Telegram)
echo.
echo   To verify: taskschd.msc → Task Scheduler Library
echo ============================================================
pause