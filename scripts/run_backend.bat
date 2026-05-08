@echo off
cd /d C:\Users\leobl\OneDrive\Documents\EtoroDemo
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 > logs\backend_stdout.log 2> logs\backend_stderr.log
