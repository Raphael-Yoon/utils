# Antigravity-Telegram Bridge

이 유틸리티는 모바일 텔레그램과 Antigravity IDE 에이전트 간의 실시간 브리지를 제공합니다.

## 🚀 시작하기

1. **봇 토큰 설정**:
   - `utils/telegram_bridge/.env` 파일을 생성하고 아래 내용을 입력합니다.
   ```env
   TELEGRAM_BOT_TOKEN=여기에_토큰_입력
   ```

2. **브리지 서버 실행**:
   - IDE 터미널에서 아래 명령을 실행하여 백그라운드 서버를 가동합니다.
   ```bash
   python utils/telegram_bridge/bridge.py
   ```
   - 이제 텔레그램 봇으로 메시지를 보내면 `inbox.json`에 쌓이게 됩니다.

3. **에이전트와 연동**:
   - 이 채팅창에서 에이전트에게 "텔레그램 메시지 확인해줘"라고 요청하세요.
   - 에이전트는 `inbox.json`을 읽고 답변을 작성한 뒤 `outbox.json`에 저장합니다.
   - 실행 중인 `bridge.py`가 이를 감지하여 텔레그램으로 답변을 보냅니다.

## 📂 파일 구조
- `bridge.py`: 텔레그램 봇 API와 통격하는 코어 엔진.
- `inbox.json`: 수신된 메시지 저장소.
- `outbox.json`: 전송 대기 중인 답변 저장소.
- `.env`: 봇 토큰 보안 설정.

## 👨‍💻 담당자
- **서주아 샘** (Automation Developer): 봇 로직 및 API 연동
- **정기민 샘** (Platform Engineer): 데이터 안정성 및 큐 관리
