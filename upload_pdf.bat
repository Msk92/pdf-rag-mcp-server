@echo off
REM PDF Upload Script for Windows
REM Usage: upload_pdf.bat "path\to\your\file.pdf"

if "%~1"=="" (
    echo Usage: upload_pdf.bat "path\to\your\file.pdf"
    echo Example: upload_pdf.bat "C:\Documents\my_book.pdf"
    pause
    exit /b 1
)

REM Change to the script directory
cd /d "%~dp0"

REM Check if the PDF file exists
if not exist "%~1" (
    echo Error: File not found: %~1
    pause
    exit /b 1
)

REM Run the Python upload script
echo Starting PDF upload and processing...
uv run upload_pdf.py "%~1"

REM Check if the command was successful
if %ERRORLEVEL% EQU 0 (
    echo.
    echo PDF upload completed successfully!
) else (
    echo.
    echo PDF upload failed!
)

pause