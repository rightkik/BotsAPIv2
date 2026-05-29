@echo off
cd /d %~dp0
python -m streamlit run dashboard\app.py --browser.gatherUsageStats false
pause
