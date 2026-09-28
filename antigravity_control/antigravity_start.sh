#!/bin/bash
# -----------------------------------------------------------------------------
# Antigravity 시작 스크립트
# 개발4팀 (손현호 PM, 박새찬 Automation, 김주성 Platform)
# -----------------------------------------------------------------------------

# 1. 이미 실행 중인지 확인
PIDS=$(pgrep -f "^/snap/antigravity/.*/opt/antigravity/antigravity")
if [ -n "$PIDS" ]; then
    MAIN_PID=$(echo "$PIDS" | head -n 1)
    echo "ℹ️ Antigravity가 이미 실행 중입니다 (PID: $MAIN_PID)."
    exit 0
fi

# 2. GUI 디스플레이 환경변수 설정
export DISPLAY="${DISPLAY:-:0}"
export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
export XDG_CURRENT_DESKTOP="${XDG_CURRENT_DESKTOP:-ubuntu:GNOME}"
export XDG_SESSION_TYPE="${XDG_SESSION_TYPE:-wayland}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=/run/user/$(id -u)/bus}"

# 3. 백그라운드 분리 실행
nohup /snap/bin/antigravity > /dev/null 2>&1 &
sleep 2

# 4. 기동 여부 검증
NEW_PIDS=$(pgrep -f "^/snap/antigravity/.*/opt/antigravity/antigravity")
if [ -n "$NEW_PIDS" ]; then
    MAIN_PID=$(echo "$NEW_PIDS" | head -n 1)
    echo "🚀 Antigravity가 성공적으로 실행되었습니다 (PID: $MAIN_PID)."
    exit 0
else
    echo "❌ Antigravity 실행 실패. 환경 및 로그를 확인해 주세요."
    exit 1
fi
