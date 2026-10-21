@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
    echo Python tidak dijumpai. Pasang Python 3.10 atau lebih baharu dahulu.
    pause
    exit /b 1
)

echo ============================================
echo  Membina LoanTrack.exe
echo ============================================
echo.

python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo Memasang PyInstaller...
    python -m pip install pyinstaller
    if errorlevel 1 goto :error
)

python -m PyInstaller --noconfirm --clean --onefile --windowed --name LoanTrack --icon "assets\icon.ico" --add-data "assets;assets" loan_tracker.py
if errorlevel 1 goto :error

copy /Y "dist\LoanTrack.exe" "LoanTrack.exe" >nul
if errorlevel 1 goto :error
if exist build rmdir /S /Q build
if exist dist rmdir /S /Q dist
if exist LoanTrack.spec del /Q LoanTrack.spec

echo.
echo Siap! Fail LoanTrack.exe telah dikemas kini.
pause
exit /b 0

:error
echo.
echo Pembinaan gagal. Semak mesej di atas.
pause
exit /b 1
