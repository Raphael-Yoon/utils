"""
[개발4팀 CBT 엔진] MySQL 'cbt' ➔ SQLite 백업 동기화 모듈
일일 백업 스크립트(backup_all.sh) 실행 시 MySQL의 cbt 데이터를 cbt.db(SQLite)로 스냅샷 백업합니다.
"""

import sys
import json
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = BASE_DIR.parent.parent
DEFAULT_SQLITE_PATH = BASE_DIR / "cbt.db"

if str(WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_DIR))
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from utils.cbt_engine.db import _parse_mysql_url, DATABASE_URL


def backup_cbt_to_sqlite(sqlite_path: Path = DEFAULT_SQLITE_PATH):
    import pymysql
    import pymysql.cursors

    config = _parse_mysql_url(DATABASE_URL)
    db_name = config["database"]

    try:
        mysql_conn = pymysql.connect(
            **config,
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=5,
        )
    except Exception as e:
        print(f"⚠️ [CBT Backup] MySQL 연결 불가 ({e}), 백업 스킵.")
        return

    sqlite_conn = sqlite3.connect(sqlite_path)
    s_cur = sqlite_conn.cursor()

    try:
        # 1. exam_results 백업
        s_cur.execute(
            """
            CREATE TABLE IF NOT EXISTS exam_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT DEFAULT '응시자',
                exam_id TEXT,
                exam_title TEXT,
                total_score REAL,
                max_score REAL,
                is_pass INTEGER,
                fail_reason TEXT,
                time_taken_seconds INTEGER,
                subject_scores_json TEXT,
                user_answers_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        with mysql_conn.cursor() as m_cur:
            m_cur.execute("SELECT * FROM exam_results ORDER BY id ASC")
            m_results = m_cur.fetchall()

        s_cur.execute("DELETE FROM exam_results")
        for r in m_results:
            subj = r.get("subject_scores_json") or "[]"
            if not isinstance(subj, str):
                subj = json.dumps(subj, ensure_ascii=False)
            ans = r.get("user_answers_json") or "{}"
            if not isinstance(ans, str):
                ans = json.dumps(ans, ensure_ascii=False)

            s_cur.execute(
                """
                INSERT INTO exam_results (
                    id, user_name, exam_id, exam_title, total_score, max_score, is_pass, fail_reason, time_taken_seconds, subject_scores_json, user_answers_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    r["id"],
                    r.get("user_name", "응시자"),
                    r.get("exam_id", ""),
                    r.get("exam_title", ""),
                    float(r.get("total_score") or 0.0),
                    float(r.get("max_score") or 100.0),
                    int(r.get("is_pass") or 0),
                    r.get("fail_reason", ""),
                    int(r.get("time_taken_seconds") or 0),
                    subj,
                    ans,
                    str(r.get("created_at") or ""),
                ),
            )

        # 2. exam_drafts 백업
        s_cur.execute(
            """
            CREATE TABLE IF NOT EXISTS exam_drafts (
                user_name TEXT PRIMARY KEY,
                exam_path TEXT,
                exam_title TEXT,
                user_answers_json TEXT,
                remaining_seconds INTEGER,
                current_question_idx INTEGER,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        with mysql_conn.cursor() as m_cur:
            m_cur.execute("SELECT * FROM exam_drafts")
            m_drafts = m_cur.fetchall()

        s_cur.execute("DELETE FROM exam_drafts")
        for d in m_drafts:
            ans = d.get("user_answers_json") or "{}"
            if not isinstance(ans, str):
                ans = json.dumps(ans, ensure_ascii=False)

            s_cur.execute(
                """
                INSERT INTO exam_drafts (
                    user_name, exam_path, exam_title, user_answers_json, remaining_seconds, current_question_idx, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    d["user_name"],
                    d.get("exam_path", ""),
                    d.get("exam_title", ""),
                    ans,
                    int(d.get("remaining_seconds") or 0),
                    int(d.get("current_question_idx") or 0),
                    str(d.get("updated_at") or ""),
                ),
            )

        sqlite_conn.commit()
        print(f"✅ [CBT Backup] MySQL '{db_name}' ➔ SQLite 동기화 완료: exam_results {len(m_results)}건, exam_drafts {len(m_drafts)}건")
    finally:
        sqlite_conn.close()
        mysql_conn.close()


if __name__ == "__main__":
    backup_cbt_to_sqlite()
