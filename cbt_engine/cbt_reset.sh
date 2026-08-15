#!/bin/bash

# "재설정"은 cbt_start.sh가 매번 수행하는 강제 동기화(git reset --hard)와 동일하므로,
# 별도로 git 동기화를 중복 수행하지 않고 시작 스크립트에 그대로 위임한다.
# (예전에는 여기서도 fetch/reset을 한 번 더 실행해 로그가 두 번 찍히는 문제가 있었음)
cd /home/raphael/Dev/pythons/utils/cbt_engine
./cbt_start.sh
