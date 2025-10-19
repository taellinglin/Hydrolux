@echo off
echo Welcome! What would you like to run?
echo.
echo 1. Talking Clock
echo 2. Cool Tune
echo 3. Annoyance Fish
echo 4. Dragon
echo.
choice /c 1234 /m "Please enter your choice (1,2, or 3):"

if %errorlevel% equ 1 (
    echo Starting Talking Clock...
    call python comet.py
) else if %errorlevel% equ 2 (
    echo Starting Cool Tune...
    call python star.py
) else if %errorlevel% equ 3 (
    echo Starting Cool Tune...
    call python ocean.py
) else if %errorlevel% equ 4 (
    echo Starting Cool Tune...
    call python ocean.py
)