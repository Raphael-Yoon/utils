#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/cbt.pid"
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        echo "Stopping CBT Engine process (PID: $PID)..."
        kill -9 $PID
    fi
    rm "$PID_FILE"
fi

# 혹시 모를 잔여 프로세스 정리 (패턴 매칭)
pkill -f "run_cbt_server.py"

echo "CBT Engine server stopped successfully."
