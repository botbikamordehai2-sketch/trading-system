@echo off
echo Starting MT5 instances...

start "" "C:\Program Files\FTMO Global Markets MT5 Terminal\terminal64.exe"
timeout /t 3 /nobreak >nul

start "" "C:\Program Files\Blueberry Markets SVG MT5 Terminal\terminal64.exe"
timeout /t 3 /nobreak >nul

start "" "C:\Program Files\MetaTrader 5\terminal64.exe"

echo.
echo Done. 3 windows should open.
echo.
echo Account 1 (FTMO)      = s1_classic
echo Account 2 (Blueberry) = s2_aggressive
echo Account 3 (MetaTrader)= s3_momentum
pause
