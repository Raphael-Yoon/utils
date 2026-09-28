#!/bin/bash
# -----------------------------------------------------------------------------
# Antigravity 종료 스크립트
# 개발4팀 (손현호 PM, 박새찬 Automation, 김주성 Platform)
# -----------------------------------------------------------------------------

# 1. 실행 중인 Antigravity 프로세스 확인
PIDS=$(pgrep -f "^/snap/antigravity/.*/opt/antigravity/antigravity")

if [ -z "$PIDS" ]; then
    echo "ℹ️ 실행 중인 Antigravity 프로세스가 없습니다."
    exit 0
fi

# 2. 부드러운 종료(SIGTERM) 시도
pkill -TERM -f "^/snap/antigravity/.*/opt/antigravity/antigravity" 2>/dev/null
sleep 2

# 3. 잔여 프로세스 강제 종료(SIGKILL) 확인
REMAINING=$(pgrep -f "^/snap/antigravity/.*/opt/antigravity/antigravity")
if [ -n "$REMAINING" ]; then
    pkill -9 -f "^/snap/antigravity/.*/opt/antigravity/antigravity" 2>/dev/null
    sleep 1
fi

# 4. 최종 확인
FINAL_CHECK=$(pgrep -f "^/snap/antigravity/.*/opt/antigravity/antigravity")
if [ -z "$FINAL_CHECK" ]; then
    echo "🛑 Antigravity가 안전하게 종료되었습니다."
    exit 0
else
    echo "⚠️ 일부 프로세스 정리에 실패했습니다. (남은 PID: $FINAL_CHECK)"
    exit 1
fi
