@echo off
cd /d "%~dp0"

echo ==============================
echo Starting stock price update...
echo ==============================
echo.

call .venv\Scripts\activate.bat
python scripts\update_stock_data.py

echo.
echo ==============================
echo Done. Press any key to close.
echo ==============================
pause >nul
