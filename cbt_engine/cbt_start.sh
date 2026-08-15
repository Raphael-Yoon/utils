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

# 2. 깃허브 원격 최신 파일 동기화
# 주의: "git checkout origin/master -- cbt_engine/" 방식은 원격에서 삭제된 파일을
# 로컬에 그대로 남겨두는 문제가 있어(예: 파일명 변경 시 구 파일 잔존), reset --hard로 대체함.
# -q(quiet) 옵션으로 git의 원문 로그("HEAD is now at ..." 등)는 숨기고, 아래의 친절한 한 줄 메시지만 남긴다.
cd /home/raphael/Dev/pythons/utils
if ! git fetch -q origin || ! git reset -q --hard origin/master; then
    echo "❌ 코드 동기화 실패 (네트워크 또는 git 오류). 서버를 재기동하지 않습니다."
    exit 1
fi
COMMIT_MSG=$(git log -1 --format='%h %s')
echo "✅ 최신 코드 반영 완료: $COMMIT_MSG"
cd /home/raphael/Dev/pythons/utils/cbt_engine

# 3. 포트가 풀리도록 대기
sleep 1

# 3. 127.0.0.1:5004번 포트로 백그라운드 구동 (PID 파일 지정)
export PYTHONIOENCODING=utf-8
PID=$(/home/raphael/Dev/pythons/.venv/bin/python -c "import subprocess, sys; p = subprocess.Popen(['/home/raphael/Dev/pythons/.venv/bin/python', '-u', '/home/raphael/Dev/pythons/utils/cbt_engine/run_cbt_server.py', '5004'], stdout=open('/home/raphael/Dev/pythons/utils/cbt_engine/cbt_server.log', 'a'), stderr=open('/home/raphael/Dev/pythons/utils/cbt_engine/cbt_server.log', 'a'), start_new_session=True); print(p.pid)")
echo $PID > "$PID_FILE"
sleep 1

# 4. 결과 출력 (프로세스 생존 여부까지 확인 후 성공/실패를 명확히 알림)
if ps -p $PID > /dev/null 2>&1; then
    echo "🚀 CBT Engine 서버가 정상적으로 기동되었습니다 (PID: $PID, 포트: 5004)"
else
    echo "❌ CBT Engine 서버 기동 실패. cbt_server.log를 확인하세요."
    exit 1
fi
