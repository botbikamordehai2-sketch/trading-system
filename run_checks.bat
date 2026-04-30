@echo off
chcp 65001 >nul
echo ============================================================
echo 🔍 PRE-FLIGHT CHECKS — אל תריץ על כסף אמיתי בלי ירוק!
echo ============================================================
echo.

echo [1/3] 🧪 Unit Tests...
cd /d "%~dp0"
python test_entry_monitor.py
if %errorlevel% neq 0 (
    echo ❌ TESTS FAILED — תקן באגים לפני הרצה!
    pause
    exit /b 1
)
echo.

echo [2/3] 🔍 Linting (Ruff)...
ruff check . --quiet 2>&1
if %errorlevel% neq 0 (
    echo ⚠️ LINTING WARNINGS — מומלץ לתקן
) else (
    echo ✅ Lint clean
)
echo.

echo [3/3] 📋 Type Check (Mypy)...
mypy entry_monitor.py daily_review.py --no-error-summary 2>&1
if %errorlevel% neq 0 (
    echo ⚠️ TYPE WARNINGS — מומלץ לתקן
) else (
    echo ✅ Types clean
)
echo.

echo ============================================================
echo ✅ READY FOR LIVE — כל הבדיקות עברו
echo ============================================================
pause