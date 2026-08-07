#!/bin/bash

# 1. 기존에 돌고 있는 CBT Engine 프로세스 종료 (PID 파일 활용)
PID_FILE="/home/raphael/Dev/pythons/utils/cbt_engine/cbt.pid"
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        echo "Stopping existing CBT Engine process (PID: $PID)..."
        kill -9 $PID
    fi
    rm "$PID_FILE"
fi

# 혹시 모를 잔여 프로세스 정리 (패턴 매칭)
pkill -f "run_cbt_server.py"

# 2. 포트가 풀리도록 대기
sleep 1

# 3. 127.0.0.1:5004번 포트로 백그라운드 구동 (PID 파일 지정)
echo "Starting CBT Engine server on port 5004..."
export PYTHONIOENCODING=utf-8
PID=$(/home/raphael/Dev/pythons/.venv/bin/python -c "import subprocess, sys; p = subprocess.Popen(['/home/raphael/Dev/pythons/.venv/bin/python', '-u', '/home/raphael/Dev/pythons/utils/cbt_engine/run_cbt_server.py', '5004'], stdout=open('/home/raphael/Dev/pythons/utils/cbt_engine/cbt_server.log', 'a'), stderr=open('/home/raphael/Dev/pythons/utils/cbt_engine/cbt_server.log', 'a'), start_new_session=True); print(p.pid)")
echo $PID > "$PID_FILE"

# 4. 결과 출력
echo "------------------------------------------------"
echo "CBT Engine server started successfully on port 5004 (PID: $PID)!"
echo "Logs are being written to cbt_server.log"
echo "------------------------------------------------"
