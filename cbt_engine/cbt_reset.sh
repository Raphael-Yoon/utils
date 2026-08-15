#!/bin/bash

# 1. utils 프로젝트 폴더 위치로 이동 (.git 저장소 위치)
cd /home/raphael/Dev/pythons/utils

# 2. 깃허브 최신 코드 강제 동기화 (원격에서 삭제된 파일도 함께 정리되도록 reset --hard 사용)
echo "Overriding local files with latest origin/master from GitHub..."
git fetch origin
if ! git reset --hard origin/master; then
    echo "ERROR: git reset failed (network or git error). CBT server will not be restarted." >&2
    exit 1
fi

# 3. 최신 코드 반영 후 서버 재시작
cd /home/raphael/Dev/pythons/utils/cbt_engine
./cbt_start.sh
