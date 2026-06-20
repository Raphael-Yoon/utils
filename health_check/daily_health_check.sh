#!/bin/bash
# Daily Health Check runner script for cron job
# Developed by Dev Team 4

# Move to workspace directory
cd /home/raphael/Dev/pythons

# Activate virtual environment and run python health check
/home/raphael/Dev/pythons/.venv/bin/python /home/raphael/Dev/pythons/utils/health_check/daily_health_check.py >> /home/raphael/Dev/pythons/utils/health_check/health_check.log 2>&1
