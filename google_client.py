# -*- coding: utf-8 -*-
"""
[개발4팀 공통 유틸리티] 전사 통합 Google API 멀티 계정 클라이언트 (Google Client)
- 업무계정(Work): snowball1566@gmail.com
- 개인계정(Personal): newsist27@gmail.com
- 지원 서비스: Google Drive, Sheets, Docs, Gmail
"""

import os
import sys
import pickle
import base64
import argparse
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# Windows 콘솔 인코딩 대응
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# 표준 계정 정의
ACCOUNT_WORK = "snowball1566@gmail.com"
ACCOUNT_PERSONAL = "newsist27@gmail.com"

# 기본 경로 설정
UTILS_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = UTILS_DIR.parent
TOKENS_DIR = UTILS_DIR / "google_tokens"
TOKENS_DIR.mkdir(parents=True, exist_ok=True)

CREDENTIALS_PATHS = [
    UTILS_DIR / "credentials.json",
    PROJECT_ROOT / "credentials.json",
    PROJECT_ROOT / "trade" / "credentials.json",
    PROJECT_ROOT / "snowball" / "credentials.json",
]

# 통합 SCOPES (Drive, Sheets, Docs, Gmail)
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly'
]

def resolve_account_key(account: str = "work") -> tuple[str, str]:
    """
    계정 식별자를 표준화하여 (account_key, account_email) 튜플 반환
    """
    if not account:
        return "work", ACCOUNT_WORK

    norm = str(account).strip().lower()
    if norm in ["work", "snowball", "snowball1566", "snowball1566@gmail.com", "업무", "업무계정", "공용"]:
        return "work", ACCOUNT_WORK
    elif norm in ["personal", "newsist", "newsist27", "newsist27@gmail.com", "개인", "개인계정"]:
        return "personal", ACCOUNT_PERSONAL
    else:
        # 이메일 주소 직접 전달 시
        if "newsist27" in norm:
            return "personal", ACCOUNT_PERSONAL
        return "work", ACCOUNT_WORK

def get_credentials_path() -> Path:
    """유효한 credentials.json 경로 탐색"""
    for p in CREDENTIALS_PATHS:
        if p.exists():
            return p
    raise FileNotFoundError(f"credentials.json을 찾을 수 없습니다. 경로: {CREDENTIALS_PATHS[0]}")

def get_credentials(account: str = "work"):
    """
    지정된 계정(업무/개인)의 OAuth2 인증 객체 획득 및 자동 갱신
    """
    account_key, account_email = resolve_account_key(account)
    token_path = TOKENS_DIR / f"token_{account_key}.pickle"
    creds = None

    if token_path.exists():
        with open(token_path, "rb") as token:
            try:
                creds = pickle.load(token)
            except Exception:
                creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"[{account_email}] 토큰 갱신 실패, 재인증 필요: {e}")
                creds = None

        if not creds:
            import webbrowser
            cred_file = get_credentials_path()
            flow = InstalledAppFlow.from_client_secrets_file(str(cred_file), SCOPES)
            print(f"\n[AUTH] [{account_email} ({'개인계정' if account_key == 'personal' else '업무계정'})] 인증 서버를 시작합니다...")
            # run_local_server 구동
            creds = flow.run_local_server(port=0, prompt='consent')

        with open(token_path, "wb") as token:
            pickle.dump(creds, token)
            print(f"[OK] [{account_email}] 인증 토큰 저장 완료: {token_path.name}")

    return creds

def get_drive_service(account: str = "work"):
    """Google Drive v3 서비스 객체 반환"""
    creds = get_credentials(account)
    return build("drive", "v3", credentials=creds)

def get_sheets_service(account: str = "work"):
    """Google Sheets v4 서비스 객체 반환"""
    creds = get_credentials(account)
    return build("sheets", "v4", credentials=creds)

def get_docs_service(account: str = "work"):
    """Google Docs v1 서비스 객체 반환"""
    creds = get_credentials(account)
    return build("docs", "v1", credentials=creds)

def get_gmail_service(account: str = "work"):
    """Gmail v1 서비스 객체 반환"""
    creds = get_credentials(account)
    return build("gmail", "v1", credentials=creds)

def send_gmail(to: str, subject: str, body: str, html: bool = False, account: str = "work", bcc: str = None, attachments: list = None):
    """
    지정된 계정(업무계정/개인계정)으로 이메일 발송
    """
    account_key, account_email = resolve_account_key(account)

    if os.getenv("MOCK_MAIL") == "True":
        print(f"\n=== [MOCK GMAIL REPORT ({account_key.upper()}: {account_email})] ===")
        print(f"To: {to} | Bcc: {bcc}")
        print(f"Subject: {subject}")
        print("Body Preview:", body[:100] + "..." if len(body) > 100 else body)
        return {"id": "mock_id"}

    service = get_gmail_service(account)
    message = MIMEMultipart()
    message['to'] = to
    message['from'] = account_email
    message['subject'] = subject
    if bcc:
        message['bcc'] = bcc

    msg_type = 'html' if html else 'plain'
    message.attach(MIMEText(body, msg_type, 'utf-8'))

    if attachments:
        for file_path in attachments:
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f'attachment; filename="{os.path.basename(file_path)}"')
                    message.attach(part)

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    res = service.users().messages().send(userId='me', body={'raw': raw_message}).execute()
    print(f"[MAIL] [{account_email}] 이메일 발송 성공 (Message ID: {res.get('id')})")
    return res

def upload_to_drive(local_file_path: str, folder_id: str = None, folder_name: str = None, account: str = "work") -> dict:
    """
    지정된 계정의 Google Drive에 파일 업로드
    """
    service = get_drive_service(account)
    file_name = os.path.basename(local_file_path)

    # 폴더명 지정 시 폴더 검색 또는 생성
    target_folder_id = folder_id
    if not target_folder_id and folder_name:
        query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        files = results.get('files', [])
        if files:
            target_folder_id = files[0]['id']
        else:
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = service.files().create(body=folder_metadata, fields='id').execute()
            target_folder_id = folder.get('id')

    file_metadata = {'name': file_name}
    if target_folder_id:
        file_metadata['parents'] = [target_folder_id]

    media = MediaFileUpload(local_file_path, resumable=True)
    uploaded = service.files().create(body=file_metadata, media_body=media, fields='id, name, webViewLink').execute()
    print(f"[DRIVE] [{resolve_account_key(account)[1]}] Drive 업로드 완료: {uploaded.get('name')} (ID: {uploaded.get('id')})")
    return uploaded

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Google 멀티 계정 인증 및 관리 CLI")
    parser.add_argument("--auth", choices=["work", "personal", "all"], help="지정된 계정의 OAuth2 토큰 생성/갱신")
    args = parser.parse_args()

    if args.auth == "work":
        get_credentials("work")
    elif args.auth == "personal":
        get_credentials("personal")
    elif args.auth == "all":
        get_credentials("work")
        get_credentials("personal")
    else:
        print("명령어 예시:")
        print("  python google_client.py --auth work      # 업무계정(snowball1566@gmail.com) 인증")
        print("  python google_client.py --auth personal  # 개인계정(newsist27@gmail.com) 인증")
