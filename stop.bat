@echo off
echo Stopping Busy Agent...
taskkill /F /FI "WINDOWTITLE eq Busy Agent*" /T
if %errorlevel% neq 0 (
    echo Could not find window with title "Busy Agent". Trying to kill by process name...
    wmic process where "commandline like '%%python busy_agent.py%%'" delete
)
echo Busy Agent stopped.
pause
