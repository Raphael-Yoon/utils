#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 1. 기존에 돌고 있는 CBT Engine 프로세스 종료 (PID 파일 활용)
PID_FILE="$SCRIPT_DIR/cbt.pid"
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
export PYTHONIOENCODING=utf-8
PID=$("$WORKSPACE_DIR/.venv/bin/python" -c "import subprocess, sys; p = subprocess.Popen(['$WORKSPACE_DIR/.venv/bin/python', '-u', '$SCRIPT_DIR/run_cbt_server.py', '5004'], stdout=open('$SCRIPT_DIR/cbt_server.log', 'a'), stderr=open('$SCRIPT_DIR/cbt_server.log', 'a'), start_new_session=True); print(p.pid)")
echo $PID > "$PID_FILE"
sleep 1

# 4. 결과 출력 (프로세스 생존 여부까지 확인 후 성공/실패를 명확히 알림)
if ps -p $PID > /dev/null 2>&1; then
    echo "🚀 CBT Engine 서버가 정상적으로 기동되었습니다 (PID: $PID, 포트: 5004)"
else
    echo "❌ CBT Engine 서버 기동 실패. cbt_server.log를 확인하세요."
    exit 1
fi
