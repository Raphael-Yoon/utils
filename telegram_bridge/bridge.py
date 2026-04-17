import asyncio
import json
import os
import time
import subprocess
from pathlib import Path
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# 설정 파일 및 경로
BRIDGE_DIR = Path(__file__).parent
INBOX_FILE = BRIDGE_DIR / "inbox.json"
OUTBOX_FILE = BRIDGE_DIR / "outbox.json"
ENV_FILE = BRIDGE_DIR / ".env"

load_dotenv(ENV_FILE)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# 데이터 초기화
if not INBOX_FILE.exists():
    INBOX_FILE.write_text(json.dumps([], indent=4))
if not OUTBOX_FILE.exists():
    OUTBOX_FILE.write_text(json.dumps([], indent=4))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """텔레그램 수신 메시지를 리눅스 쉘 명령어로 즉시 실행 (전원 켜진 PC 원격 제어용)"""
    if not update.message or not update.message.text:
        return

    user = update.effective_user
    chat_id = update.effective_chat.id
    command = update.message.text

    print(f"[📡 원격 명령] {user.first_name}: {command}")

    # 1. 큐에 기록 (히스토리용)
    try:
        data = json.loads(INBOX_FILE.read_text())
    except:
        data = []
    data.append({"command": command, "timestamp": time.time(), "user": user.first_name})
    INBOX_FILE.write_text(json.dumps(data[-20:], indent=4, ensure_ascii=False))

    # 2. 명령어 실행 및 결과 캡처
    await update.message.reply_text(f"⚡️ `{command}` 실행 중...", parse_mode='Markdown')
    
    try:
        # 서브프로세스로 쉘 명령어 실행
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=60, # 1분 타임아웃
            cwd=str(Path.home()) # 홈 디렉토리 기준 실행
        )
        
        output = result.stdout.strip()
        error = result.stderr.strip()
        
        response = ""
        if output:
            response += f"📋 **결과:**\n```\n{output}\n```"
        if error:
            response += f"\n❌ **에러:**\n```\n{error}\n```"
        if not output and not error:
            response = "✅ 작업이 완료되었습니다 (출력 없음)."
            
    except subprocess.TimeoutExpired:
        response = "⏳ **타임아웃**: 명령 실행 시간이 60초를 초과했습니다."
    except Exception as e:
        response = f"🚫 **실행 실패**: {str(e)}"

    # 3. 텔레그램으로 즉시 결과 보고 (4000자 초과 시 절삭)
    if len(response) > 4000:
        response = response[:3900] + "\n...(이하 생략)"

    await update.message.reply_text(response, parse_mode='Markdown')

def main():
    if not TOKEN:
        print("에러: .env 파일에 TELEGRAM_BOT_TOKEN이 없습니다.")
        return

    application = ApplicationBuilder().token(TOKEN).build()
    
    # 텔레그램의 모든 메시지를 쉘 명령어로 처리
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("--- 📡 Antigravity Remote Shell 가동 시작 ---")
    print(f"이 PC는 이제 텔레그램으로 원격 제어됩니다 (24시간 상시 대기 모드).")
    
    application.run_polling()

if __name__ == "__main__":
    main()
