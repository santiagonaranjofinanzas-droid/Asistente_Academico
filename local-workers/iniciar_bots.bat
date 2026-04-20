@echo off
cd /d "%~dp0"
echo [%date% %time%] Iniciando Bots de Asistente Academico (Telegram y Notificaciones)...

:: Iniciar el Bot de Captura Rápida en segundo plano
start /B .venv\Scripts\python.exe telegram_bot.py > bot_log.txt 2>&1

:: Iniciar el Monitor de Vencimientos en segundo plano
start /B .venv\Scripts\python.exe deadline_monitor.py > monitor_log.txt 2>&1

:: Iniciar el Monitor de Correo ESPE en segundo plano
start /B .venv\Scripts\python.exe email_checker.py > email_log.txt 2>&1

:: Iniciar el Recordatorio de Clases en segundo plano
start /B .venv\Scripts\python.exe class_reminder.py > reminder_log.txt 2>&1

echo Bots iniciados correctamente. Se están ejecutando en segundo plano.
exit
