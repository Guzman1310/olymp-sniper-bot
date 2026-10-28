@echo off
title Olymp Sniper Bot 100%% Automatico - 24/7
echo ========================================================
echo   SCANNER SNIPER REAL OLYMP TRADE (24/7 ACTIVO)
echo   Equipo: Rafael Guzman & Eduardo Rivera
echo ========================================================
cd /d "C:\Users\GTI\.gemini\antigravity\scratch\olymp_sniper_bot"

:loop
echo [%date% %time%] Iniciando Scanner Sniper...
python real_platform_reader.py
echo.
echo [!] Advertencia: Proceso finalizado o conexion interrumpida.
echo [*] Auto-reiniciando en 5 segundos de forma automatica...
timeout /t 5 >nul
goto loop
