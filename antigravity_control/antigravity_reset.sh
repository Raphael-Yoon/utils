#!/bin/bash
# -----------------------------------------------------------------------------
# Antigravity 재시작 스크립트
# 개발4팀 (손현호 PM, 박새찬 Automation, 김주성 Platform)
# -----------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🔄 [1/2] Antigravity 종료 중..."
"$SCRIPT_DIR/antigravity_stop.sh"
sleep 2

echo "🚀 [2/2] Antigravity 재기동 중..."
"$SCRIPT_DIR/antigravity_start.sh"
