@echo off
cd /d "%~dp0"
echo [%date% %time%] Iniciando Bots de Asistente Academico (Telegram y Notificaciones)...

:: Iniciar el Bot de Captura Rápida en segundo plano
start /B ..\.venv\Scripts\python.exe telegram_bot.py > bot_log.txt 2>&1

:: Iniciar el Monitor de Vencimientos en segundo plano
start /B ..\.venv\Scripts\python.exe deadline_monitor.py > monitor_log.txt 2>&1

:: Iniciar el Puente de Ollama Automatizado
start /B ..\.venv\Scripts\python.exe ollama_bridge.py > bridge_log.txt 2>&1

echo Bots iniciados correctamente. Se están ejecutando en segundo plano.
exit
