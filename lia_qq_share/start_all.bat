@echo off
chcp 65001 >nul
title 莉亚 全家桶启动器
echo ========================================
echo   莉亚 QQ 一键启动 (NapCat + 桥接)
echo ========================================
netstat -ano | findstr ":3001" | findstr LISTENING >nul 2>&1
if %errorlevel%==0 (
  echo [1/2] NapCat 已在运行
) else (
  echo [1/2] 启动 NapCat（首次需扫码登录小号，之后自动登录）...
  start "NapCat" /min cmd /c "cd /d D:\Tool\AI_qq && node.exe index.js"
  timeout /t 10 /nobreak >nul
)
netstat -ano | findstr ":3001" | findstr LISTENING >nul 2>&1
if %errorlevel%==0 (
  echo [2/2] 启动莉亚桥接...
  start "LiaQQ桥接" /min cmd /c "chcp 65001 >nul & cd /d D:\LiaQQ && C:\Users\13040\AppData\Local\Programs\Python\Python312\python.exe lia_qq.py"
  echo 全部就绪！两个最小化窗口在跑。关窗口=停对应程序。
) else (
  echo [2/2] 失败：NapCat 没起来，检查 D:\Tool\AI_qq 或手动启动看报错。
)
echo.
pause
