import asyncio
import json
import os
import time
import subprocess
import html
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
RAW_COMMANDS = [
    # 1. Snowball (IT 감사)
    {
        "system": "1. Snowball (IT 감사)",
        "num": "1-1",
        "alias": "sb-start",
        "cmd": "./snowball_start.sh",
        "cwd": "/home/raphael/Dev/pythons/snowball",
        "desc": "Snowball AP 서버 시작"
    },
    {
        "system": "1. Snowball (IT 감사)",
        "num": "1-2",
        "alias": "sb-reset",
        "cmd": "./snowball_reset.sh",
        "cwd": "/home/raphael/Dev/pythons/snowball",
        "desc": "Snowball AP 서버 재설정 및 재기동"
    },
    {
        "system": "1. Snowball (IT 감사)",
        "num": "1-3",
        "alias": "sb-stop",
        "cmd": "./snowball_stop.sh",
        "cwd": "/home/raphael/Dev/pythons/snowball",
        "desc": "Snowball AP 서버 종료"
    },
    # 2. Trading (Jonathan's Coffee House)
    {
        "system": "2. Trading (Jonathan's Coffee House)",
        "num": "2-1",
        "alias": "tr-start",
        "cmd": "./coffee_house_start.sh",
        "cwd": "/home/raphael/Dev/pythons/trade",
        "desc": "Jonathan's Coffee House AP 서버 시작"
    },
    {
        "system": "2. Trading (Jonathan's Coffee House)",
        "num": "2-2",
        "alias": "tr-reset",
        "cmd": "./coffee_house_reset.sh",
        "cwd": "/home/raphael/Dev/pythons/trade",
        "desc": "Jonathan's Coffee House AP 서버 재설정 및 재기동"
    },
    {
        "system": "2. Trading (Jonathan's Coffee House)",
        "num": "2-3",
        "alias": "tr-stop",
        "cmd": "./coffee_house_stop.sh",
        "cwd": "/home/raphael/Dev/pythons/trade",
        "desc": "Jonathan's Coffee House AP 서버 종료"
    },
    # 3. Infosd (정보보호공시)
    {
        "system": "3. Infosd (정보보호공시)",
        "num": "3-1",
        "alias": "is-start",
        "cmd": "./infosd_start.sh",
        "cwd": "/home/raphael/Dev/pythons/infosd",
        "desc": "정보보호공시 AP 서버 시작"
    },
    {
        "system": "3. Infosd (정보보호공시)",
        "num": "3-2",
        "alias": "is-reset",
        "cmd": "./infosd_reset.sh",
        "cwd": "/home/raphael/Dev/pythons/infosd",
        "desc": "정보보호공시 AP 서버 재설정 및 재기동"
    },
    {
        "system": "3. Infosd (정보보호공시)",
        "num": "3-3",
        "alias": "is-stop",
        "cmd": "./infosd_stop.sh",
        "cwd": "/home/raphael/Dev/pythons/infosd",
        "desc": "정보보호공시 AP 서버 종료"
    },
    # 4. CBT Engine (모의고사)
    {
        "system": "4. CBT Engine (모의고사)",
        "num": "4-1",
        "alias": "cbt-start",
        "cmd": "./cbt_start.sh",
        "cwd": "/home/raphael/Dev/pythons/utils/cbt_engine",
        "desc": "CBT Engine AP 서버 시작"
    },
    {
        "system": "4. CBT Engine (모의고사)",
        "num": "4-2",
        "alias": "cbt-reset",
        "cmd": "./cbt_reset.sh",
        "cwd": "/home/raphael/Dev/pythons/utils/cbt_engine",
        "desc": "CBT Engine AP 서버 재설정 및 재기동"
    },
    {
        "system": "4. CBT Engine (모의고사)",
        "num": "4-3",
        "alias": "cbt-stop",
        "cmd": "./cbt_stop.sh",
        "cwd": "/home/raphael/Dev/pythons/utils/cbt_engine",
        "desc": "CBT Engine AP 서버 종료"
    }
]

COMMAND_MAPPING = {}
for cmd_info in RAW_COMMANDS:
    COMMAND_MAPPING[cmd_info["num"]] = cmd_info
    COMMAND_MAPPING[cmd_info["alias"]] = cmd_info

# 단일 숫자 명령어(1, 2, 3, 4)를 x-2 (Reset) 명령어에 추가 매핑
SINGLE_DIGIT_MAP = {"1": "1-2", "2": "2-2", "3": "3-2", "4": "4-2"}
for single, target_num in SINGLE_DIGIT_MAP.items():
    if target_num in COMMAND_MAPPING:
        COMMAND_MAPPING[single] = COMMAND_MAPPING[target_num]

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """단축 명령어를 입력받아 AP 서버 제어 스크립트 실행"""
    if not update.message or not update.message.text:
        return

    user = update.effective_user
    chat_id = update.effective_chat.id
    raw_text = update.message.text.strip()
    
    # 앞의 슬래시(/) 제거 및 소문자 변환으로 유연하게 처리
    command = raw_text.lstrip("/").lower()

    print(f"[📡 원격 명령 수신] {user.first_name}: {raw_text} (매핑: {command})", flush=True)

    # 1. 큐에 기록 (히스토리용)
    try:
        data = json.loads(INBOX_FILE.read_text())
    except:
        data = []
    data.append({"command": raw_text, "timestamp": time.time(), "user": user.first_name})
    INBOX_FILE.write_text(json.dumps(data[-20:], indent=4, ensure_ascii=False))

    # 2. 명령어 확인 및 처리
    if command in ["help", "?", "0"]:
        help_text = "📋 <b>사용 가능한 단축 명령어 목록:</b>\n\n"
        current_system = None
        for cmd_info in RAW_COMMANDS:
            if cmd_info["system"] != current_system:
                current_system = cmd_info["system"]
                help_text += f"\n🖥 <b>{current_system}</b>\n"
            extra_shortcut = f", <code>{cmd_info['num'][0]}</code>" if cmd_info['num'].endswith("-2") else ""
            help_text += f"🔹 <code>{cmd_info['num']}</code> (또는 <code>{cmd_info['alias']}</code>{extra_shortcut}) : {cmd_info['desc']}\n"
        help_text += "\n* <code>0</code>, <code>help</code>, <code>?</code> 입력 시 이 안내 메시지가 출력됩니다."
        await update.message.reply_text(help_text, parse_mode='HTML')
        return

    if command not in COMMAND_MAPPING:
        err_msg = f"❌ <b>지원하지 않는 명령어입니다.</b>\n\n<code>0</code> 또는 <code>help</code>를 입력하여 사용 가능한 단축 명령어 목록을 확인하세요."
        await update.message.reply_text(err_msg, parse_mode='HTML')
        return

    info = COMMAND_MAPPING[command]
    await update.message.reply_text(f"⚡️ <code>{info['desc']}</code> 실행 중...", parse_mode='HTML')
    
    try:
        # 지정된 cwd 디렉토리로 이동하여 쉘 명령어 비동기로 실행 (이벤트 루프 차단 방지)
        result = await asyncio.to_thread(
            subprocess.run,
            info["cmd"], 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=60, # 1분 타임아웃
            cwd=info["cwd"]
        )
        
        output = result.stdout.strip()
        error = result.stderr.strip()
        
        response = f"🎯 <b>{info['desc']} 결과:</b>\n"
        if output:
            response += f"\n📋 <b>출력:</b>\n<pre>{html.escape(output)}</pre>"
        if error:
            if result.returncode != 0:
                response += f"\n❌ <b>실행 에러 (코드 {result.returncode}):</b>\n<pre>{html.escape(error)}</pre>"
            else:
                response += f"\nℹ️ <b>추가 정보:</b>\n<pre>{html.escape(error)}</pre>"
        if not output and not error:
            response += "\n✅ 작업이 완료되었습니다 (출력 없음)."
            
    except subprocess.TimeoutExpired:
        response = f"⏳ <b>타임아웃</b>: <code>{info['desc']}</code> 실행 시간이 60초를 초과했습니다."
    except Exception as e:
        response = f"🚫 <b>실행 실패</b>: {html.escape(str(e))}"

    if len(response) > 4000:
        response = response[:3900] + "\n...(이하 생략)"

    await update.message.reply_text(response, parse_mode='HTML')

def main():
    if not TOKEN:
        print("에러: .env 파일에 TELEGRAM_BOT_TOKEN이 없습니다.", flush=True)
        return

    application = ApplicationBuilder().token(TOKEN).build()
    
    # 텔레그램의 모든 텍스트 메시지를 하나의 핸들러에서 처리
    application.add_handler(MessageHandler(filters.TEXT, handle_message))
        
    print("--- 📡 Antigravity Remote Shell 가동 시작 (단축 명령어 모드) ---", flush=True)
    print(f"사용 가능한 명령어: {', '.join(COMMAND_MAPPING.keys())}", flush=True)
    
    application.run_polling()

if __name__ == "__main__":
    main()
