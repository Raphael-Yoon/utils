#!/bin/bash
# -----------------------------------------------------------------------------
# 전사 서비스 일괄 재시작 스크립트 (All-in-One Restart Script)
# 개발4팀 (PM: 손현호 차장)
# -----------------------------------------------------------------------------

WORKSPACE_DIR="/home/raphael/Dev/pythons"

echo "=== [1/6] Docker Databases 기동 ==="
docker start snowball-mysql

echo "=== [2/6] AP Gunicorn & Python 서버 재기동 ==="
# 각 서비스 디렉토리로 이동하여 start 스크립트 실행
cd "$WORKSPACE_DIR/snowball" && ./snowball_start.sh
cd "$WORKSPACE_DIR/trade" && ./coffee_house_start.sh
cd "$WORKSPACE_DIR/infosd" && ./infosd_start.sh
cd "$WORKSPACE_DIR/utils/cbt_engine" && ./cbt_start.sh

echo "=== [3/6] Cloudflared 터널 프로세스 재기동 ==="
systemctl --user stop cloudflared-ksox cloudflared-trade cloudflared-infosd cloudflared-cbt 2>/dev/null || true
pkill -f "cloudflared tunnel run"
sleep 1
systemd-run --user --unit=cloudflared-ksox bash -c "exec cloudflared tunnel run --url http://127.0.0.1:5001 84e81d82-14e0-4c05-b317-6caa923e0bd4 > '$WORKSPACE_DIR/snowball/cloudflared_ksox.log' 2>&1"
systemd-run --user --unit=cloudflared-trade bash -c "exec cloudflared tunnel run --url http://127.0.0.1:5000 10d06dea-316c-452d-97a0-6d89a1adb223 > '$WORKSPACE_DIR/trade/cloudflared_trade.log' 2>&1"
systemd-run --user --unit=cloudflared-infosd bash -c "exec cloudflared tunnel run --url http://127.0.0.1:5003 89a30767-5899-4985-9723-59b7a9eebea2 > '$WORKSPACE_DIR/infosd/cloudflared_infosd.log' 2>&1"
systemd-run --user --unit=cloudflared-cbt bash -c "exec cloudflared tunnel run --url http://127.0.0.1:5004 f8af40cf-0088-45f0-82bc-3befe3bb6dbd > '$WORKSPACE_DIR/utils/cbt_engine/cloudflared_cbt.log' 2>&1"

echo "=== [4/6] Telegram Remote Bridge 재기동 ==="
systemctl --user stop telegram-bridge 2>/dev/null || true
pkill -f "telegram_bridge/bridge.py" 2>/dev/null || true
sleep 1
systemd-run --user --unit=telegram-bridge bash -c "exec '$WORKSPACE_DIR/.venv/bin/python' -u '$WORKSPACE_DIR/utils/telegram_bridge/bridge.py' > '$WORKSPACE_DIR/utils/telegram_bridge/bridge.log' 2>&1"

echo "=== [5/6] 헬스체크 수행 및 알림 발송 ==="
sleep 3
"$WORKSPACE_DIR/.venv/bin/python" "$WORKSPACE_DIR/utils/health_check/daily_health_check.py"

echo "==========================================="
echo "모든 전사 시스템 서비스 재구동 완료!"
echo "==========================================="

