#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Google Drive Offsite Backup & Telegram Alert Script
- Developed by Dev Team 4 (PM: 손현호 차장)
- Uploads latest server backup archive to Google Drive ("Server_Backups" folder)
- Automatically purges Google Drive backups older than 7 days (or keeping max 7 backups)
- Sends status notification via Telegram
"""

import os
import sys
import glob
import requests
from datetime import datetime

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

sys.path.insert(0, os.path.join(PROJECT_ROOT, "trade"))
from drive_sync import get_drive_service
from googleapiclient.http import MediaFileUpload

TELEGRAM_BOT_TOKEN = "8439778551:AAHMXpbmR1_JgxKDFGjNIUzH6YOSnXrJF5A"
DEFAULT_CHAT_ID = "8587089093"


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
        return resp.status_code == 200
    except Exception as e:
        print(f"❌ Telegram 전송 실패: {e}")
        return False


def get_or_create_drive_folder(service, folder_name="Server_Backups"):
    q = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    res = service.files().list(q=q, spaces='drive').execute()
    folders = res.get('files', [])

    if folders:
        return folders[0]['id']
    else:
        meta = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
        f = service.files().create(body=meta, fields='id').execute()
        return f['id']


def upload_and_clean_gdrive(file_path):
    token_file = os.path.join(PROJECT_ROOT, 'trade', 'token.pickle')
    service = get_drive_service(token_file)

    folder_id = get_or_create_drive_folder(service, "Server_Backups")
    fname = os.path.basename(file_path)

    # 1. Upload to Google Drive Server_Backups folder
    media = MediaFileUpload(file_path, mimetype='application/gzip')
    meta = {'name': fname, 'parents': [folder_id]}
    uploaded = service.files().create(body=meta, media_body=media, fields='id, name').execute()

    # 2. Clean Google Drive backups (keep max 7 recent files)
    res = service.files().list(
        q=f"'{folder_id}' in parents and trashed = false",
        orderBy='createdTime desc',
        fields='files(id, name, createdTime)'
    ).execute()
    drive_files = res.get('files', [])

    deleted_count = 0
    if len(drive_files) > 7:
        for old_file in drive_files[7:]:
            try:
                service.files().delete(fileId=old_file['id']).execute()
                print(f"🗑️ Google Drive 오래된 백업 삭제: {old_file['name']}")
                deleted_count += 1
            except Exception as de:
                print(f"⚠️ Drive 삭제 실패 ({old_file['name']}): {de}")

    return uploaded['id'], len(drive_files) - deleted_count, deleted_count


def main():
    backup_dir = os.path.join(PROJECT_ROOT, "backups")
    backup_files = sorted(glob.glob(os.path.join(backup_dir, "server_backup_*.tar.gz")), key=os.path.getmtime, reverse=True)

    if not backup_files:
        msg = "❌ 백업 파일 생성 실패: 소산 전송할 백업 아카이브를 찾을 수 없습니다."
        print(msg)
        send_telegram(f"<b>[⚠️ 서버 백업 경고]</b>\n{msg}")
        sys.exit(1)

    latest_file = backup_files[0]
    file_basename = os.path.basename(latest_file)
    file_size_kb = os.path.getsize(latest_file) / 1024.0
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"📦 최신 백업 파일 발견: {file_basename} ({file_size_kb:.1f} KB)")

    # Google Drive 업로드 및 7일 보관 주기 정리
    try:
        print("☁️ Google Drive 원격 소산 업로드 중...")
        file_id, total_retained, deleted_count = upload_and_clean_gdrive(latest_file)
        drive_status = f"✅ 성공 (보관: {total_retained}개, 정리: {deleted_count}개)"
        print(f"✅ Google Drive 소산 업로드 완료! File ID: {file_id}")
    except Exception as e:
        drive_status = f"❌ 실패 ({e})"
        print(f"❌ Google Drive 소산 업로드 실패: {e}")

    # Telegram 상태 보고 발송
    telegram_text = f"""<b>[📦 서버 풀 백업 & Google Drive 원격 소산 보고]</b>
일시: {now_str}
백업 파일: <code>{file_basename}</code>
파일 용량: {file_size_kb:.1f} KB
Google Drive 상태: {drive_status}

<i>*로컬 및 Google Drive(Server_Backups 폴더) 7일 보관 주기가 자동으로 적용되었습니다.</i>"""

    send_telegram(telegram_text)
    print("✅ Telegram 통지 완료.")


if __name__ == "__main__":
    main()
