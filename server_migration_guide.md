# 전사 서비스 서버 이전 및 자동 환경 구성 가이드 (AI-Ready Runbook)

본 문서는 현재 PC에서 구동 중인 전사 웹 서비스 및 유틸리티 시스템을 신규 PC(서버)로 안전하게 이전하기 위한 인프라 구축 및 실행 가이드라인입니다. 
신규 PC의 **Gemini AI 어시스턴트**가 이 문서를 컨텍스트로 읽고, 환경 구축부터 통합 서비스 실행까지 **자동으로 설정을 구성하고 검증**할 수 있도록 표준 명령과 구성을 제공합니다.

---

## 1. 시스템 개요 및 타깃 아키텍처

신규 PC에 구축해야 할 최종 구성 요소와 서비스 포트 매핑 정보입니다.

### 1.1 서비스 포트 및 터널 매핑
| 서비스명 | 대상 디렉토리 | 구동 방식 | 내부 포트 | 외부 연결 (Cloudflare Tunnel ID) |
| :--- | :--- | :--- | :--- | :--- |
| **trade** (트레이딩) | `~/Dev/pythons/trade` | Gunicorn (daemon) | `5000` | `10d06dea-316c-452d-97a0-6d89a1adb223` |
| **snowball** (IT 감사) | `~/Dev/pythons/snowball` | Gunicorn (daemon) | `5001` | `84e81d82-14e0-4c05-b317-6caa923e0bd4` |
| **infosd** (정보보호공시) | `~/Dev/pythons/infosd` | Gunicorn (daemon) | `5003` | `89a30767-5899-4985-9723-59b7a9eebea2` |
| **casino** (카지노 게임) | `~/Dev/pythons/casino` | 정적 리소스 호스팅 | N/A | N/A (필요 시 정적 웹서버 연동) |
| **telegram_bridge** | `~/Dev/pythons/utils/telegram_bridge` | Python daemon | N/A | Telegram Bot API 연동 |

### 1.2 인프라 및 DB 구성
*   **Docker Container**: `snowball-mysql` (IT 감사 및 공통 DB용 MySQL 컨테이너)
*   **Python 가상환경**: `~/Dev/pythons/.venv` (모든 서비스 공통 가상환경 활용)
*   **터널 서비스**: `cloudflared` (Systemd --user 유닛 연동 기동)

---

## 2. Gemini AI용 단계별 자동 구축 명령어 (AI Runbook)

신규 PC의 Gemini 어시스턴트는 아래 가이드에 따라 시스템 환경을 차례대로 셋업해야 합니다.

### 단계 1: 프로젝트 디렉토리 준비 및 코드 동기화
신규 PC의 `/home/raphael/Dev/pythons/` 경로 아래에 기존 리포지토리들이 모두 복사/클론되어 있는지 확인합니다.
```bash
# 디렉토리 구조 검증
ls -la /home/raphael/Dev/pythons/
```

### 단계 2: Python 공통 가상환경 구축 및 의존성 설치
모든 파이썬 기반 서비스는 동일한 가상환경(`~/Dev/pythons/.venv`)을 공유합니다.
```bash
cd /home/raphael/Dev/pythons
python3 -m venv .venv
source .venv/bin/activate

# 각 프로젝트 내 requirements.txt 의존성 일괄 설치
for dir in snowball trade infosd utils/telegram_bridge; do
    if [ -f "$dir/requirements.txt" ]; then
        echo "Installing requirements for $dir..."
        .venv/bin/pip install -r "$dir/requirements.txt"
    fi
done
```

### 단계 3: Docker 엔진 설치 및 MySQL 컨테이너 구성

신규 PC에 Docker가 설치되어 있지 않은 경우, 아래 명령어를 실행하여 Docker 엔진을 설치하고 데몬을 구동합니다.

```bash
# 1. Docker 설치 (Ubuntu 기준)
sudo apt-get update
sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io

# 2. Docker Compose 플러그인 설치
sudo apt-get install -y docker-compose-plugin

# 3. 현재 사용자를 docker 그룹에 추가하여 sudo 없이 실행할 수 있도록 설정
sudo usermod -aG docker $USER
# (주의: 그룹 권한을 적용하려면 터미널 세션을 재시작하거나 'newgrp docker' 명령을 실행해야 합니다)
newgrp docker
```

이후, 아래 단계에 따라 데이터베이스를 세팅합니다.

*   **기존 PC 백업 (이전 대상 컴퓨터)**:
    이전하기 직전, MySQL 운영 데이터를 로컬 `snowball.db`로 역동기화하여 단일 SQLite 백업 파일로 만듭니다.
    ```bash
    # 1. MySQL 최신 데이터를 snowball.db로 백업 실행
    /home/raphael/Dev/pythons/.venv/bin/python -c "import sys; sys.path.insert(0, '/home/raphael/Dev/pythons/snowball'); from migrations.backup_mysql_to_sqlite import backup_mysql_to_sqlite; backup_mysql_to_sqlite('/home/raphael/Dev/pythons/snowball/snowball.db')"

    # 2. 형상관리에 포함되지 않는 주요 보안 및 실데이터 파일을 단일 압축파일(migration_secrets.tar.gz)로 압축
    # (실행 대상: /home/raphael/Dev/pythons 디렉토리)
    tar -czvf utils/migration_secrets.tar.gz \
      snowball/.env snowball/credentials.json snowball/token.pickle snowball/snowball.db \
      trade/.env trade/trade.db trade/credentials.json trade/token.pickle \
      infosd/.env infosd/infosd.db infosd/credentials.json infosd/token.pickle
    ```

    *※ 위 압축 파일(`utils/migration_secrets.tar.gz`)은 API Key 및 패스워드를 담고 있어 Git 저장소 추적에서 자동 제외(.gitignore)되어 있으므로, 신규 PC로 수동 이동(scp, USB 등) 시 이 압축 파일 하나만 넘기면 편리합니다.*

*   **신규 PC 복구 및 기동 (Gemini가 실행)**:
    이관된 압축 파일을 해제하고, 각 파일들이 올바른 위치에 매핑되었는지 검증한 후 MySQL을 구성합니다.
    ```bash
    # 1. 압축 파일 해제
    cd /home/raphael/Dev/pythons
    tar -xzvf utils/migration_secrets.tar.gz
    ```

    **[압축 해제 후 파일 위치 검증 매핑]**
    압축이 해제되면 아래 목록과 같이 각 서비스 폴더에 환경 파일 및 인증 파일이 정확히 들어갔는지 확인해야 합니다.
    *   `~/Dev/pythons/snowball/.env` (IT 감사 환경 변수)
    *   `~/Dev/pythons/snowball/credentials.json` (Google API 키)
    *   `~/Dev/pythons/snowball/token.pickle` (Google API 세션 토큰)
    *   `~/Dev/pythons/snowball/snowball.db` (이관된 SQLite 데이터베이스)
    *   `~/Dev/pythons/trade/.env` (트레이딩 환경 변수)
    *   `~/Dev/pythons/trade/trade.db` (트레이딩 SQLite 데이터베이스)
    *   `~/Dev/pythons/trade/credentials.json` (Google API 키)
    *   `~/Dev/pythons/trade/token.pickle` (Google API 세션 토큰)
    *   `~/Dev/pythons/infosd/.env` (정보보호공시 환경 변수)
    *   `~/Dev/pythons/infosd/infosd.db` (정보보호공시 SQLite 데이터베이스)
    *   `~/Dev/pythons/infosd/credentials.json` (Google API 키)
    *   `~/Dev/pythons/infosd/token.pickle` (Google API 세션 토큰)

    ```bash
    # 2. MySQL 컨테이너 생성 및 실행 (볼륨 마운트로 데이터 영속성 확보)
    docker run --name snowball-mysql \
      -p 3306:3306 \
      -e MYSQL_ROOT_PASSWORD=your_password \
      -v snowball_mysql_data:/var/lib/mysql \
      -d mysql:latest

    # 컨테이너가 정상 기동될 때까지 약 10초 대기
    sleep 10

    # 신규 데이터베이스 생성 (snowball DB 생성)
    docker exec -i snowball-mysql mysql -u root -p"your_password" -e "CREATE DATABASE IF NOT EXISTS snowball CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

    # SQLite 데이터를 MySQL로 완전 마이그레이션 실행
    # (동적 테이블 생성 및 데이터 마이그레이션 원클릭 진행)
    cd /home/raphael/Dev/pythons/snowball
    /home/raphael/Dev/pythons/.venv/bin/python migrations/reset_mysql_from_sqlite.py
    ```

### 단계 4: SQLite DB 스키마 마이그레이션
Gunicorn 구동 전, 로컬 SQLite 기반 서비스들의 스키마 최신화를 진행합니다.
```bash
# trade 서비스 DB 초기화
cd /home/raphael/Dev/pythons/trade
/home/raphael/Dev/pythons/.venv/bin/python db_init.py

# snowball 서비스 DB 초기화 (필요 시)
cd /home/raphael/Dev/pythons/snowball
/home/raphael/Dev/pythons/.venv/bin/python db_init.py
```

### 단계 5: Cloudflared (터널 클라이언트) 설치 및 세션 설정
웹 브라우저를 통해 `snowball.pe.kr` 도메인과 신규 PC 포트들을 연결할 수 있도록 터널 환경을 세팅합니다.
1. `cloudflared` 바이너리가 신규 PC에 설치되어 있어야 합니다.
2. 기존 터널 자격 증명 파일(JSON)을 신규 PC의 `~/.cloudflared/` 경로로 이관하거나 신규 터널을 생성하여 매핑합니다.

---

## 3. 서비스 기동 및 통합 제어

이전 및 환경 세팅이 완료되면 `utils/restart_all.sh` 스크립트를 사용하여 일괄 실행합니다.

### 3.1 통합 기동 스크립트 실행
```bash
cd /home/raphael/Dev/pythons/utils
chmod +x restart_all.sh
./restart_all.sh
```

### 3.2 개별 서비스 기동 상태 점검 명령어
*   **Gunicorn 프로세스 상태 확인**:
    ```bash
    ps aux | grep gunicorn
    ```
*   **Cloudflared 터널 프로세스 점검**:
    ```bash
    systemctl --user status cloudflared-ksox cloudflared-trade cloudflared-infosd
    # 혹은 프로세스 수동 점검
    ps aux | grep cloudflared
    ```
*   **Telegram Bridge 로그 확인**:
    ```bash
    tail -f /home/raphael/Dev/pythons/utils/telegram_bridge/bridge.log
    ```

---

## 4. 신규 PC 어시스턴트(Gemini)에 내리는 구체적인 지시 템플릿

신규 PC에서 Gemini AI가 실행을 이어받았을 때, 사용자는 다음 프롬프트를 주입하여 자동 구성을 지시할 수 있습니다.

> **[Gemini 지시 프롬프트 예시]**
> "현재 디렉토리에 위치한 `utils/server_migration_guide.md` 문서를 완독해줘. 이 가이드에 명시된 포트 바인딩 및 서비스를 기반으로, 신규 PC에 Python 가상환경(.venv) 설정, Docker DB 컨테이너 기동, SQLite 스키마 마이그레이션, 그리고 `utils/restart_all.sh` 스크립트를 통한 통합 재기동 작업을 순차적으로 자동 실행하고 결과를 리포트해줘."
