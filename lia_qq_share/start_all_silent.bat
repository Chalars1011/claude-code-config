@echo off
set FS=%SystemRoot%\System32\findstr.exe
set NS=%SystemRoot%\System32\netstat.exe
%NS% -ano | %FS% ":3001" | %FS% LISTENING >nul 2>&1
if %errorlevel%==0 goto napcat_ok
echo [1/2] Starting NapCat...
start "NapCat" /min cmd /c "cd /d D:\Tool\AI_qq && node.exe index.js"
set /a n=0
:wait
%NS% -ano | %FS% ":3001" | %FS% LISTENING >nul 2>&1
if not errorlevel 1 goto napcat_ok
set /a n+=1
if %n% GEQ 30 goto giveup
ping -n 2 127.0.0.1 >nul
goto wait
:giveup
echo [NapCat] not ready in 60s, manual login may be needed
goto end
:napcat_ok
echo [1/2] NapCat ready
echo [2/2] Starting bridge...
start "LiaBridge" /min cmd /c "cd /d D:\LiaQQ && C:\Users\13040\AppData\Local\Programs\Python\Python312\python.exe lia_qq.py"
echo [OK] Lia online
:end
exit
