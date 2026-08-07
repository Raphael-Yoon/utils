#!/bin/bash

# 1. utils 프로젝트 폴더 위치로 이동 (.git 저장소 위치)
cd /home/raphael/Dev/pythons/utils

# 2. 깃허브 최신 코드 강제 동기화 (충돌 발생 시 CBT Engine 디렉토리 원격 파일 우선 적용)
echo "Overriding local cbt_engine files with latest origin/master from GitHub..."
git fetch origin
if ! git checkout origin/master -- cbt_engine/; then
    echo "ERROR: git checkout failed (network or git error). CBT server will not be restarted." >&2
    exit 1
fi

# 3. 최신 코드 반영 후 서버 재시작
cd /home/raphael/Dev/pythons/utils/cbt_engine
./cbt_start.sh
