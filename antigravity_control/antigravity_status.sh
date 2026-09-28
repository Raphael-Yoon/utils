#!/bin/bash
# -----------------------------------------------------------------------------
# Antigravity 상태 확인 스크립트
# 개발4팀 (손현호 PM, 박새찬 Automation, 김주성 Platform)
# -----------------------------------------------------------------------------

PIDS=$(pgrep -f "^/snap/antigravity/.*/opt/antigravity/antigravity")

if [ -n "$PIDS" ]; then
    MAIN_PID=$(echo "$PIDS" | head -n 1)
    COUNT=$(echo "$PIDS" | wc -l)
    UPTIME=$(ps -p "$MAIN_PID" -o etime= 2>/dev/null | tr -d ' ')
    echo "🟢 Antigravity 실행 중 (메인 PID: $MAIN_PID, 관련 프로세스: ${COUNT}개, 가동시간: $UPTIME)"
else
    echo "⚪️ Antigravity가 현재 실행되어 있지 않습니다 (중지 상태)."
fi
