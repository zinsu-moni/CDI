@echo off
echo Starting FastAPI server...
cd %~dp0
python -m uvicorn fast_api:app --reload
pause
