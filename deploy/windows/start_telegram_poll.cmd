@echo off
cd /d C:\agent-cli-v4
if not exist .agent_state\logs mkdir .agent_state\logs
set PYTHONIOENCODING=utf-8
set AGENT_PYTHON=C:\Users\leoma\AppData\Local\Python\bin\python.exe
if not exist "%AGENT_PYTHON%" set AGENT_PYTHON=python
"%AGENT_PYTHON%" telegram_poll.py >> .agent_state\logs\telegram_poll.log 2>&1
