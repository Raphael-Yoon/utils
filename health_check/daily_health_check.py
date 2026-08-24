#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Daily Morning Health Check & Reporting Script
- Developed by Dev Team 4 (PM: 손현호)
- Checks health of 3 AP servers (local port and external domain)
- Checks health of 3 DB servers (SQLite, MySQL, Neon PostgreSQL)
- Sends detailed HTML report via Gmail API (utilizing snowball credentials)
- Sends summary alert via Telegram API
"""

import os
import sys
import time
import socket
import sqlite3
import requests
import base64
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from googleapiclient.discovery import build

# Add parent path to import snowball_mail
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from snowball.snowball_mail import get_gmail_credentials
except ImportError:
    get_gmail_credentials = None

# Telegram settings
TELEGRAM_BOT_TOKEN = "8439778551:AAHMXpbmR1_JgxKDFGjNIUzH6YOSnXrJF5A"
DEFAULT_CHAT_ID = "8587089093"  # Raphael's chat_id

import subprocess

# Target AP Servers configuration
AP_TARGETS = [
    {
        "name": "snowball (K-Sox)",
        "local_url": "http://127.0.0.1:5001",
        "external_url": "https://ksox.snowball.pe.kr",
        "start_script": os.path.join(PROJECT_ROOT, "snowball", "snowball_start.sh"),
        "working_dir": os.path.join(PROJECT_ROOT, "snowball"),
        "tunnel_unit": "cloudflared-ksox",
        "tunnel_cmd": f"cloudflared tunnel run --url http://127.0.0.1:5001 84e81d82-14e0-4c05-b317-6caa923e0bd4 > '{os.path.join(PROJECT_ROOT, 'snowball', 'cloudflared_ksox.log')}' 2>&1"
    },
    {
        "name": "Jonathan's Coffee House (트레이딩 시스템)",
        "local_url": "http://127.0.0.1:5000",
        "external_url": "https://trade.snowball.pe.kr",
        "start_script": os.path.join(PROJECT_ROOT, "trade", "coffee_house_start.sh"),
        "working_dir": os.path.join(PROJECT_ROOT, "trade"),
        "tunnel_unit": "cloudflared-trade",
        "tunnel_cmd": f"cloudflared tunnel run --url http://127.0.0.1:5000 10d06dea-316c-452d-97a0-6d89a1adb223 > '{os.path.join(PROJECT_ROOT, 'trade', 'cloudflared_trade.log')}' 2>&1"
    },
    {
        "name": "infosd (정보보호공시)",
        "local_url": "http://127.0.0.1:5003",
        "external_url": "https://infosd.snowball.pe.kr",
        "start_script": os.path.join(PROJECT_ROOT, "infosd", "infosd_start.sh"),
        "working_dir": os.path.join(PROJECT_ROOT, "infosd"),
        "tunnel_unit": "cloudflared-infosd",
        "tunnel_cmd": f"cloudflared tunnel run --url http://127.0.0.1:5003 89a30767-5899-4985-9723-59b7a9eebea2 > '{os.path.join(PROJECT_ROOT, 'infosd', 'cloudflared_infosd.log')}' 2>&1"
    },
    {
        "name": "CBT Engine (모의고사 시스템)",
        "local_url": "http://127.0.0.1:5004",
        "external_url": "https://cbt.snowball.pe.kr",
        "start_script": os.path.join(PROJECT_ROOT, "utils", "cbt_engine", "cbt_start.sh"),
        "working_dir": os.path.join(PROJECT_ROOT, "utils", "cbt_engine"),
        "tunnel_unit": "cloudflared-cbt",
        "tunnel_cmd": f"cloudflared tunnel run --url http://127.0.0.1:5004 f8af40cf-0088-45f0-82bc-3befe3bb6dbd > '{os.path.join(PROJECT_ROOT, 'utils', 'cbt_engine', 'cloudflared_cbt.log')}' 2>&1"
    }
]

# MySQL Database Server Configuration (Common Database Infrastructure)
mysql_host = "127.0.0.1"
mysql_port = 3306
mysql_user = "root"
mysql_password = os.getenv("MYSQL_PASSWORD", "150606")

# Target Database Infrastructure configuration
DB_TARGETS = [
    {
        "name": "MySQL Database Server (Port 3306)",
        "type": "mysql",
        "host": mysql_host,
        "port": mysql_port,
        "user": mysql_user,
        "password": mysql_password,
        "docker_container": "snowball-mysql"
    }
]


def check_ap(ap):
    results = {}
    
    # 1. Local URL Check
    try:
        t0 = time.time()
        resp = requests.get(ap["local_url"], timeout=5, allow_redirects=True)
        t1 = time.time()
        is_ok = 200 <= resp.status_code < 400
        results["local"] = {
            "status": "UP" if is_ok else "DOWN",
            "code": resp.status_code,
            "time_ms": int((t1 - t0) * 1000),
            "error": None if is_ok else f"HTTP {resp.status_code}"
        }
    except Exception as e:
        results["local"] = {
            "status": "DOWN",
            "code": "N/A",
            "time_ms": 0,
            "error": str(e)
        }

    # 2. External URL Check
    try:
        t0 = time.time()
        resp = requests.get(ap["external_url"], timeout=5, allow_redirects=True)
        t1 = time.time()
        is_ok = 200 <= resp.status_code < 400
        results["external"] = {
            "status": "UP" if is_ok else "DOWN",
            "code": resp.status_code,
            "time_ms": int((t1 - t0) * 1000),
            "error": None if is_ok else f"HTTP {resp.status_code}"
        }
    except Exception as e:
        results["external"] = {
            "status": "DOWN",
            "code": "N/A",
            "time_ms": 0,
            "error": str(e)
        }

    return results



def check_db(db):
    t0 = time.time()
    if db["type"] == "sqlite":
        try:
            if not os.path.exists(db["path"]):
                raise FileNotFoundError(f"Database file not found: {db['path']}")
            conn = sqlite3.connect(db["path"])
            conn.execute("SELECT 1")
            conn.close()
            return {"status": "UP", "time_ms": int((time.time() - t0) * 1000), "error": None}
        except Exception as e:
            return {"status": "DOWN", "time_ms": 0, "error": str(e)}
            
    elif db["type"] == "mysql":
        import pymysql
        hosts_to_try = [db["host"]]
        for fallback in ["100.103.64.85", "127.0.0.1", "localhost"]:
            if fallback not in hosts_to_try:
                hosts_to_try.append(fallback)

        last_error = None
        for h in hosts_to_try:
            try:
                conn = pymysql.connect(
                    host=h,
                    port=db["port"],
                    user=db["user"],
                    password=db["password"],
                    database=db.get("database"),
                    connect_timeout=5
                )
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                conn.close()
                return {"status": "UP", "time_ms": int((time.time() - t0) * 1000), "error": None}
            except Exception as e:
                last_error = e

        return {"status": "DOWN", "time_ms": 0, "error": str(last_error)}

    elif db["type"] == "postgres":
        try:
            import psycopg2
            conn = psycopg2.connect(db["url"], connect_timeout=5)
            conn.close()
            return {"status": "UP", "time_ms": int((time.time() - t0) * 1000), "error": None}
        except Exception as e:
            return {"status": "DOWN", "time_ms": 0, "error": str(e)}

    return {"status": "UNKNOWN", "time_ms": 0, "error": "Unsupported database type"}


def heal_ap(ap, local_down, external_down):
    healed = False
    details = []

    if local_down and ap.get("start_script"):
        try:
            print(f"🔄 [Auto-Healing] {ap['name']} 로컬 프로세스 재기동 시도중...")
            subprocess.run(["bash", ap["start_script"]], cwd=ap["working_dir"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            details.append("로컬 프로세스 재기동 완료")
            healed = True
        except Exception as e:
            details.append(f"로컬 재기동 실패: {e}")

    if external_down and ap.get("tunnel_unit"):
        try:
            print(f"🔄 [Auto-Healing] {ap['name']} Cloudflare 터널 재기동 시도중...")
            subprocess.run(f"systemctl --user stop {ap['tunnel_unit']} 2>/dev/null || true", shell=True)
            cmd = f"systemd-run --user --unit={ap['tunnel_unit']} bash -c \"exec {ap['tunnel_cmd']}\""
            subprocess.run(cmd, shell=True, check=True)
            details.append("Cloudflare 터널 재기동 완료")
            healed = True
        except Exception as e:
            details.append(f"터널 재기동 실패: {e}")

    return healed, ", ".join(details)


def heal_db(db):
    if db.get("docker_container"):
        try:
            print(f"🔄 [Auto-Healing] {db['name']} Docker 컨테이너 재기동 시도중...")
            subprocess.run(["docker", "restart", db["docker_container"]], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True, f"Docker {db['docker_container']} 재기동 완료"
        except Exception as e:
            return False, f"Docker 재기동 실패: {e}"
    return False, "자동 조치 스크립트 없음"


def build_html_report(ap_results, db_results, healing_history=None):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    healing_section = ""
    if healing_history:
        healing_rows = ""
        for item in healing_history:
            healing_rows += f"""
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">{item['target']}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{item['action']}</td>
                <td style="padding: 8px; border: 1px solid #ddd; text-align: center; color: {'#28a745' if item['result'] == 'SUCCESS' else '#dc3545'}; font-weight: bold;">{item['result']}</td>
            </tr>
            """
        healing_section = f"""
        <h3>⚡ 자동 복구 (Auto-healing) 조치 내역</h3>
        <table>
            <thead>
                <tr>
                    <th>대상</th>
                    <th>조치 내용</th>
                    <th>복구 결과</th>
                </tr>
            </thead>
            <tbody>
                {healing_rows}
            </tbody>
        </table>
        """

    # Generate AP table rows
    ap_rows = ""
    for ap, res in zip(AP_TARGETS, ap_results):
        local_status_color = "#28a745" if res["local"]["status"] == "UP" else "#dc3545"
        external_status_color = "#28a745" if res["external"]["status"] == "UP" else "#dc3545"
        
        ap_rows += f"""
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">{ap['name']}</td>
            <td style="padding: 10px; border: 1px solid #ddd; text-align: center; color: {local_status_color}; font-weight: bold;">{res['local']['status']}</td>
            <td style="padding: 10px; border: 1px solid #ddd; text-align: center;">{res['local']['code']} ({res['local']['time_ms']}ms)</td>
            <td style="padding: 10px; border: 1px solid #ddd; text-align: center; color: {external_status_color}; font-weight: bold;">{res['external']['status']}</td>
            <td style="padding: 10px; border: 1px solid #ddd; text-align: center;">{res['external']['code']} ({res['external']['time_ms']}ms)</td>
            <td style="padding: 10px; border: 1px solid #ddd; font-size: 12px; color: #666;">{res['external']['error'] or '정상'}</td>
        </tr>
        """
        
    # Generate DB table rows
    db_rows = ""
    for db, res in zip(DB_TARGETS, db_results):
        status_color = "#28a745" if res["status"] == "UP" else "#dc3545"
        db_rows += f"""
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">{db['name']}</td>
            <td style="padding: 10px; border: 1px solid #ddd; text-align: center; color: {status_color}; font-weight: bold;">{res['status']}</td>
            <td style="padding: 10px; border: 1px solid #ddd; text-align: center;">{res['time_ms']}ms</td>
            <td style="padding: 10px; border: 1px solid #ddd; font-size: 12px; color: #666;">{res['error'] or '정상'}</td>
        </tr>
        """

    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Malgun Gothic', Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ width: 100%; max-width: 800px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #343a40; color: #fff; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
            .content {{ padding: 20px; border: 1px solid #ddd; border-top: none; border-radius: 0 0 5px 5px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 15px; margin-bottom: 25px; }}
            th {{ background-color: #f8f9fa; padding: 10px; text-align: left; border: 1px solid #ddd; font-weight: bold; }}
            .footer {{ font-size: 12px; color: #777; text-align: center; margin-top: 30px; border-top: 1px solid #ddd; padding-top: 15px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>🛠️ 통합 시스템 모니터링 데일리 리포트</h2>
                <p>점검 일시: {now_str}</p>
            </div>
            <div class="content">
                {healing_section}

                <h3>1. Application Server (AP) 접속 상태</h3>
                <table>
                    <thead>
                        <tr>
                            <th>시스템명</th>
                            <th>로컬 상태</th>
                            <th>로컬 응답</th>
                            <th>외부(터널) 상태</th>
                            <th>외부 응답</th>
                            <th>상세 에러</th>
                        </tr>
                    </thead>
                    <tbody>
                        {ap_rows}
                    </tbody>
                </table>

                <h3>2. Database Server (DB) 연결 상태</h3>
                <table>
                    <thead>
                        <tr>
                            <th>데이터베이스</th>
                            <th>연결 상태</th>
                            <th>응답 속도</th>
                            <th>상세 에러</th>
                        </tr>
                    </thead>
                    <tbody>
                        {db_rows}
                    </tbody>
                </table>
            </div>
            <div class="footer">
                <p>본 메일은 전사 공통 유틸리티 팀(개발4팀) 모니터링 데몬에 의해 자동 발송되었습니다.</p>
                <p>수신인 변경 및 문의: 손현호 차장 (PM)</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html


def build_telegram_message(ap_results, db_results, healing_history=None):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # AP status summary
    ap_summaries = []
    for ap, res in zip(AP_TARGETS, ap_results):
        icon = "✅" if (res["local"]["status"] == "UP" and res["external"]["status"] == "UP") else "⚠️"
        ap_summaries.append(f"{icon} {ap['name']} (로컬:{res['local']['status']}/외부:{res['external']['status']})")
        
    # DB status summary
    db_summaries = []
    for db, res in zip(DB_TARGETS, db_results):
        icon = "✅" if res["status"] == "UP" else "❌"
        db_summaries.append(f"{icon} {db['name']}: {res['status']}")

    healing_text = ""
    if healing_history:
        h_lines = []
        for h in healing_history:
            h_icon = "🔄✅" if h["result"] == "SUCCESS" else "🔄❌"
            h_lines.append(f"{h_icon} <b>{h['target']}</b>: {h['action']} ({h['result']})")
        healing_text = f"\n<b>■ ⚡ 자동 복구(Auto-Healing) 결과</b>\n" + "\n".join(h_lines) + "\n"

    message = f"""<b>[📡 시스템 헬스체크 보고]</b>
일시: {now_str}
{healing_text}
<b>■ AP 서버 상태</b>
{chr(10).join(ap_summaries)}

<b>■ DB 서버 상태</b>
{chr(10).join(db_summaries)}

<i>*상세 리포트가 등록된 메일로 발송되었습니다.</i>"""
    return message


def send_html_email(html_content, to_email="snowball1566@gmail.com", subject="[시스템 모니터링] 데일리 헬스체크 리포트"):
    if os.getenv("MOCK_MAIL") == "True" or not get_gmail_credentials:
        print("\n=== [MOCK GMAIL REPORT] ===")
        print(f"To: {to_email}")
        print(f"Subject: {subject}")
        print("Body: HTML formatted report generated successfully.")
        print("===========================\n")
        return True

    try:
        creds = get_gmail_credentials()
        service = build('gmail', 'v1', credentials=creds)

        message = MIMEMultipart()
        message['to'] = to_email
        message['subject'] = subject
        message['Bcc'] = 'snowball1566@gmail.com'
        
        # Attach HTML body
        message.attach(MIMEText(html_content, 'html', 'utf-8'))

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        service.users().messages().send(userId="me", body={'raw': raw}).execute()
        print("✅ Gmail 발송 완료!")
        return True
    except Exception as e:
        print(f"❌ Gmail 발송 실패: {e}")
        return False


def send_telegram(text_content):
    if os.getenv("MOCK_TELEGRAM") == "True":
        print("\n=== [MOCK TELEGRAM REPORT] ===")
        print(text_content)
        print("==============================\n")
        return True

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": DEFAULT_CHAT_ID,
            "text": text_content,
            "parse_mode": "HTML"
        }
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            print("✅ Telegram 알림 전송 완료!")
            return True
        else:
            print(f"❌ Telegram 전송 실패 (코드 {resp.status_code}): {resp.text}")
            return False
    except Exception as e:
        print(f"❌ Telegram 전송 실패: {e}")
        return False


def main():
    # Parse command line options
    is_test = "--test" in sys.argv
    if is_test:
        os.environ["MOCK_MAIL"] = "True"
        os.environ["MOCK_TELEGRAM"] = "True"
        print("[TEST MODE] Mocking email and telegram delivery.")

    # Check flags for selective reporting
    send_email_flag = "--email" in sys.argv
    send_telegram_flag = "--telegram" in sys.argv
    
    # If neither flag is specified, default to sending both
    if not send_email_flag and not send_telegram_flag:
        send_email_flag = True
        send_telegram_flag = True

    print("1. 1차 AP/DB 서버 점검 시작...")
    ap_results = [check_ap(ap) for ap in AP_TARGETS]
    db_results = [check_db(db) for db in DB_TARGETS]

    # Check for failures and trigger auto-healing
    healing_history = []
    need_recheck = False

    for ap, res in zip(AP_TARGETS, ap_results):
        l_down = (res["local"]["status"] != "UP")
        e_down = (res["external"]["status"] != "UP")
        if l_down or e_down:
            print(f"⚠️ {ap['name']} 장애 감지 (로컬:{res['local']['status']}, 외부:{res['external']['status']})")
            healed, action_msg = heal_ap(ap, l_down, e_down)
            if healed:
                need_recheck = True
                healing_history.append({"target": ap["name"], "action": action_msg, "result": "PENDING"})

    for db, res in zip(DB_TARGETS, db_results):
        if res["status"] != "UP":
            print(f"⚠️ {db['name']} 장애 감지 ({res['status']})")
            healed, action_msg = heal_db(db)
            if healed:
                need_recheck = True
                healing_history.append({"target": db["name"], "action": action_msg, "result": "PENDING"})

    # Re-check after healing
    if need_recheck:
        print("⏱️ 자동 조치 완료 후 3초 대기 중...")
        time.sleep(3)
        print("2. 2차 (재점검) AP/DB 서버 점검 시작...")
        ap_results = [check_ap(ap) for ap in AP_TARGETS]
        db_results = [check_db(db) for db in DB_TARGETS]

        # Update healing history results based on second check
        for h in healing_history:
            ap_match = next((res for ap, res in zip(AP_TARGETS, ap_results) if ap["name"] == h["target"]), None)
            if ap_match:
                is_recovered = (ap_match["local"]["status"] == "UP" and ap_match["external"]["status"] == "UP")
                h["result"] = "SUCCESS" if is_recovered else "FAILED"
            else:
                db_match = next((res for db, res in zip(DB_TARGETS, db_results) if db["name"] == h["target"]), None)
                if db_match:
                    h["result"] = "SUCCESS" if db_match["status"] == "UP" else "FAILED"

    print("3. 보고서 빌드 중...")
    html_report = build_html_report(ap_results, db_results, healing_history)
    telegram_msg = build_telegram_message(ap_results, db_results, healing_history)

    print("4. 리포트 전송 중...")
    if send_email_flag:
        send_html_email(html_report)
        
    if send_telegram_flag:
        has_failure = any(res["local"]["status"] != "UP" or res["external"]["status"] != "UP" for res in ap_results) or \
                      any(res["status"] != "UP" for res in db_results)
        # 데일리 리포트(--email)와 함께 가동되거나 오류가 발생하였거나 자동 복구를 시도한 경우 텔레그램 발송
        if has_failure or send_email_flag or healing_history:
            send_telegram(telegram_msg)
        else:
            print("🔊 모든 시스템 정상: 텔레그램 알림 전송을 생략합니다.")
    
    print("5. 헬스체크 및 자동 복구 프로세스 종료.")


if __name__ == "__main__":
    main()

