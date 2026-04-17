import sqlite3
import os
from datetime import datetime

# 데이터베이스 파일 경로
DB_PATH = os.path.join(os.path.dirname(__file__), 'csr.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row # 결과를 딕셔너리처럼 접근 가능하게 함
    return conn

def init_db():
    """데이터베이스 초기화 및 테이블 생성"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS service_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sr_id TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            requester TEXT NOT NULL,
            status TEXT DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            approved_at TIMESTAMP,
            approver TEXT,
            evidence_log TEXT
        )
    ''')
    conn.commit()
    conn.close()

def generate_sr_id():
    """SRxxxxx 형식의 자동 번호 생성"""
    conn = get_db_connection()
    last_sr = conn.execute('SELECT sr_id FROM service_requests ORDER BY id DESC LIMIT 1').fetchone()
    conn.close()
    
    if not last_sr:
        return 'SR00001'
    
    try:
        last_number = int(last_sr['sr_id'][2:])
        new_number = last_number + 1
        return f'SR{new_number:05d}'
    except (ValueError, IndexError):
        return 'SR00001'
