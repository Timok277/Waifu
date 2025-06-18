
@echo off
chcp 65001 > nul
echo.
echo ===============================================
echo      Updating Waifu to version 2.1.3.3
echo ===============================================
echo.
echo Please do not close this window.
echo The application will restart automatically.
echo.
echo --^> Waiting for application to exit (5 seconds)...
timeout /t 5 /nobreak > nul
echo --^> Step 1/3: Copying new files...
robocopy "update_temp" . /E /IS /IT /MOVE /NFL /NDL /NJH /NJS /nc /ns /np
if %errorlevel% geq 8 (
    echo.
    echo [ERROR] File copy failed. Update cannot continue.
    robocopy . "update_temp" /E /MOVE > nul
    pause
    exit /b %errorlevel%
)
echo --^> Step 2/3: Cleaning up...
rd /s /q "update_temp"
del "Client.zip"
echo --^> Step 3/3: Restarting application...
echo.
echo Update complete!
start "" "C:\dan\Waifu\.venv\Scripts\python.exe" main_app.py
del "%~f0"
