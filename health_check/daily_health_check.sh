#!/bin/bash
# Daily Health Check runner script for cron job
# Developed by Dev Team 4

# Move to workspace directory
cd /home/yuju/Dev/Pythons

# Activate virtual environment and run python health check
/home/yuju/Dev/Pythons/.venv/bin/python /home/yuju/Dev/Pythons/utils/health_check/daily_health_check.py >> /home/yuju/Dev/Pythons/utils/health_check/health_check.log 2>&1
