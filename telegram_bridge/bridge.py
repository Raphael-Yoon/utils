import asyncio
import json
import os
import time
import subprocess
from pathlib import Path
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
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

# 단축 명령어 매핑 설정
COMMAND_MAPPING = {
    "sb-start": {
        "cmd": "./snowball_start.sh",
        "cwd": "/home/raphael/Dev/pythons/snowball",
        "desc": "Snowball AP 서버 시작"
    },
    "sb-stop": {
        "cmd": "./snowball_stop.sh",
        "cwd": "/home/raphael/Dev/pythons/snowball",
        "desc": "Snowball AP 서버 종료"
    },
    "sb-reset": {
        "cmd": "./snowball_reset.sh",
        "cwd": "/home/raphael/Dev/pythons/snowball",
        "desc": "Snowball AP 서버 재설정 및 재기동"
    },
    "tr-start": {
        "cmd": "./coffee_house_start.sh",
        "cwd": "/home/raphael/Dev/pythons/trade",
        "desc": "Trading AP 서버 시작"
    },
    "tr-stop": {
        "cmd": "./coffee_house_stop.sh",
        "cwd": "/home/raphael/Dev/pythons/trade",
        "desc": "Trading AP 서버 종료"
    },
    "tr-reset": {
        "cmd": "./coffee_house_reset.sh",
        "cwd": "/home/raphael/Dev/pythons/trade",
        "desc": "Trading AP 서버 재설정 및 재기동"
    },
    "is-start": {
        "cmd": "./infosd_start.sh",
        "cwd": "/home/raphael/Dev/pythons/infosd",
        "desc": "정보보호공시 AP 서버 시작"
    },
    "is-stop": {
        "cmd": "./infosd_stop.sh",
        "cwd": "/home/raphael/Dev/pythons/infosd",
        "desc": "정보보호공시 AP 서버 종료"
    },
    "is-reset": {
        "cmd": "./infosd_reset.sh",
        "cwd": "/home/raphael/Dev/pythons/infosd",
        "desc": "정보보호공시 AP 서버 재설정 및 재기동"
    }
}

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """단축 명령어를 입력받아 AP 서버 제어 스크립트 실행"""
    if not update.message or not update.message.text:
        return

    user = update.effective_user
    chat_id = update.effective_chat.id
    raw_text = update.message.text.strip()
    
    # 앞의 슬래시(/) 제거 및 소문자 변환으로 유연하게 처리
    command = raw_text.lstrip("/").lower()

    print(f"[📡 원격 명령 수신] {user.first_name}: {raw_text} (매핑: {command})")

    # 1. 큐에 기록 (히스토리용)
    try:
        data = json.loads(INBOX_FILE.read_text())
    except:
        data = []
    data.append({"command": raw_text, "timestamp": time.time(), "user": user.first_name})
    INBOX_FILE.write_text(json.dumps(data[-20:], indent=4, ensure_ascii=False))

    # 2. 명령어 확인 및 처리
    if command == "help" or command == "?":
        help_text = "📋 **사용 가능한 단축 명령어 목록:**\n\n"
        for cmd, info in COMMAND_MAPPING.items():
            help_text += f"🔹 `{cmd}` : {info['desc']}\n"
        help_text += "\n* 슬래시(/) 없이 입력하셔도 작동합니다."
        await update.message.reply_text(help_text, parse_mode='Markdown')
        return

    if command not in COMMAND_MAPPING:
        err_msg = f"❌ **지원하지 않는 명령어입니다.**\n\n`help`를 입력하여 사용 가능한 단축 명령어 목록을 확인하세요."
        await update.message.reply_text(err_msg, parse_mode='Markdown')
        return

    info = COMMAND_MAPPING[command]
    await update.message.reply_text(f"⚡️ `{info['desc']}` 실행 중...", parse_mode='Markdown')
    
    try:
        # 지정된 cwd 디렉토리로 이동하여 쉘 명령어 실행
        result = subprocess.run(
            info["cmd"], 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=60, # 1분 타임아웃
            cwd=info["cwd"]
        )
        
        output = result.stdout.strip()
        error = result.stderr.strip()
        
        response = f"🎯 **{info['desc']} 결과:**\n"
        if output:
            response += f"\n📋 **출력:**\n```\n{output}\n```"
        if error:
            response += f"\n❌ **에러:**\n```\n{error}\n```"
        if not output and not error:
            response += "\n✅ 작업이 완료되었습니다 (출력 없음)."
            
    except subprocess.TimeoutExpired:
        response = f"⏳ **타임아웃**: `{info['desc']}` 실행 시간이 60초를 초과했습니다."
    except Exception as e:
        response = f"🚫 **실행 실패**: {str(e)}"

    if len(response) > 4000:
        response = response[:3900] + "\n...(이하 생략)"

    await update.message.reply_text(response, parse_mode='Markdown')

def main():
    if not TOKEN:
        print("에러: .env 파일에 TELEGRAM_BOT_TOKEN이 없습니다.")
        return

    application = ApplicationBuilder().token(TOKEN).build()
    
    # 텔레그램의 모든 텍스트 메시지를 하나의 핸들러에서 처리
    application.add_handler(MessageHandler(filters.TEXT, handle_message))
        
    print("--- 📡 Antigravity Remote Shell 가동 시작 (단축 명령어 모드) ---")
    print(f"사용 가능한 명령어: {', '.join(COMMAND_MAPPING.keys())}")
    
    application.run_polling()

if __name__ == "__main__":
    main()
