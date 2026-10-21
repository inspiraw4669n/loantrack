@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
    echo Python tidak dijumpai.
    echo Sila pasang Python 3.10 atau lebih baharu, atau gunakan LoanTrack.exe.
    pause
    exit /b 1
)

echo Memulakan LoanTrack...
python loan_tracker.py
if errorlevel 1 (
    echo.
    echo Aplikasi berhenti dengan ralat. Semak mesej di atas.
    pause
)
exit /b 0
