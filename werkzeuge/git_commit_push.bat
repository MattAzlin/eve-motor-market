@echo off
REM Alles Geaenderte committen und pushen - fragt nach der Commit-Nachricht.
REM Fassung 1 (19.09.2026). Bericht: berichte\git_bericht.txt
setlocal
cd /d "%~dp0.."
if not exist "berichte" mkdir "berichte"
set B=berichte\git_bericht.txt
echo Fassung 1 - %DATE% %TIME% > "%B%"
where git >nul 2>&1 || (echo git nicht im PATH >> "%B%" & type "%B%" & pause & exit /b 1)
echo -- Geaendert: >> "%B%"
git status --porcelain >> "%B%" 2>&1
git status --short
echo.
set /p MSG=Commit-Nachricht: 
if "%MSG%"=="" set MSG=Aenderungen
git add -A >> "%B%" 2>&1
git commit -m "%MSG%" >> "%B%" 2>&1
git push >> "%B%" 2>&1
if errorlevel 1 (echo FEHLER beim Push >> "%B%") else (echo Commit + Push fertig: %MSG% >> "%B%")
type "%B%"
pause
