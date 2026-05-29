@echo off
echo Stopping old Streamlit on port 8501...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8501.*LISTENING" 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
)
timeout /t 1 >nul

echo Starting dashboard...
cd /d D:\BotsAPIv2
start /B python -m streamlit run dashboard/app.py --server.headless true --browser.gatherUsageStats false

timeout /t 4 >nul
start http://localhost:8501
echo Done. Dashboard running at http://localhost:8501
