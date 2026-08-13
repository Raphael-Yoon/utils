#!/bin/bash
# -----------------------------------------------------------------------------
# 전사 서비스 일괄 백업 스크립트 (All-in-One Full Backup Script)
# 개발4팀 (PM: 손현호 차장)
# -----------------------------------------------------------------------------

set -e

WORKSPACE_DIR="/home/raphael/Dev/pythons"
BACKUP_DIR="$WORKSPACE_DIR/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/server_backup_${TIMESTAMP}.tar.gz"

echo "==========================================="
echo "📦 전사 서버 시스템 풀 백업 시작: $TIMESTAMP"
echo "==========================================="

mkdir -p "$BACKUP_DIR"

echo "=== [1/3] MySQL 최신 데이터 SQLite 동기화 백업 ==="
if [ -f "$WORKSPACE_DIR/.venv/bin/python" ]; then
    MYSQL_HOST="${MYSQL_HOST:-100.103.64.85}" MYSQL_USER="${MYSQL_USER:-root}" MYSQL_PASSWORD="${MYSQL_PASSWORD:-150606}" MYSQL_PORT="${MYSQL_PORT:-3306}" \
    "$WORKSPACE_DIR/.venv/bin/python" -c "import sys; sys.path.insert(0, '$WORKSPACE_DIR/snowball'); from migrations.backup_mysql_to_sqlite import backup_mysql_to_sqlite; backup_mysql_to_sqlite('$WORKSPACE_DIR/snowball/snowball.db')" || echo "⚠️ MySQL 백업 경고 (SQLite 동기화 스킵)"
else
    echo "⚠️ Python 가상환경을 찾을 수 없어 DB 역동기화를 스킵합니다."
fi

echo "=== [2/3] DB, Cloudflared 설정 및 주요 자격증명 파일 압축 백업 ==="
cd "$WORKSPACE_DIR"
tar -czvf "$BACKUP_FILE" \
    snowball/.env snowball/credentials.json snowball/token.pickle snowball/snowball.db \
    trade/.env trade/trade.db trade/credentials.json trade/token.pickle \
    infosd/.env infosd/infosd.db infosd/credentials.json infosd/token.pickle \
    utils/cbt_engine/cbt_engine.db \
    -C "$HOME" .cloudflared 2>/dev/null || true

echo "=== [3/4] 오래된 백업 보관 주기 정리 (7일 초과 및 최근 7개 초과 삭제) ==="
cd "$BACKUP_DIR"
find . -maxdepth 1 -name "server_backup_*.tar.gz" -mtime +7 -delete 2>/dev/null || true
ls -t server_backup_*.tar.gz 2>/dev/null | tail -n +8 | xargs -r rm -f || true

echo "=== [4/4] Google Cloud 원격 소산 전송 및 Telegram 알림 ==="
if [ -f "$WORKSPACE_DIR/.venv/bin/python" ]; then
    "$WORKSPACE_DIR/.venv/bin/python" "$WORKSPACE_DIR/utils/send_backup_offsite.py"
fi

echo "==========================================="
echo "✅ 풀 백업 및 원격 소산 완료!"
echo "📍 백업 파일 위치: $BACKUP_FILE"
echo "📊 백업 파일 용량: $(du -sh "$BACKUP_FILE" | cut -f1)"
echo "==========================================="
