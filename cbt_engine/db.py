"""
[개발4팀 CBT 엔진] 데이터베이스 연결 및 관리 모듈
- 운영서버 (IS_PROD=true): MySQL 전용 DB 스페이스('cbt') 사용 (실제 시험 풀이 및 성적 단일 관리)
- 개발환경 (IS_PROD=false): SQLite ('cbt.db') 사용 (코드 개발 및 로컬 테스트 전용)
"""

import os
import json
import sqlite3
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = BASE_DIR.parent.parent
DEFAULT_SQLITE_PATH = BASE_DIR / "cbt.db"

# .env 파일 자동 탐색 및 로드
try:
    from dotenv import load_dotenv
    for env_candidate in [BASE_DIR / ".env", WORKSPACE_DIR / ".env", WORKSPACE_DIR / "snowball" / ".env"]:
        if env_candidate.exists():
            load_dotenv(env_candidate, override=False)
except Exception:
    pass

# 환경 판별: IS_PROD 환경변수 기준 (snowball/trade 표준)
# IS_PROD=true  -> 운영서버 (MySQL 'cbt' DB 전용)
# IS_PROD=false -> 개발환경 (SQLite 전용)
_is_prod_env = os.getenv("IS_PROD", "").strip().lower()
_db_type_env = os.getenv("CBT_DB_TYPE") or os.getenv("DB_TYPE", "")

if _db_type_env.lower() in ("mysql", "sqlite"):
    DB_TYPE = _db_type_env.lower()
elif _is_prod_env in ("true", "1", "yes"):
    DB_TYPE = "mysql"
elif _is_prod_env in ("false", "0", "no"):
    DB_TYPE = "sqlite"
else:
    # .env 파일이 없는 기본 개발 환경에서는 자동으로 SQLite 사용 (Zero-Config)
    DB_TYPE = "sqlite"

# MySQL 기본 접속 정보 (운영서버 전용 DB: cbt)
DEFAULT_MYSQL_URL = "mysql://root:150606@127.0.0.1:3306/cbt"
DATABASE_URL = os.getenv("CBT_DATABASE_URL") or os.getenv("DATABASE_URL") or DEFAULT_MYSQL_URL


def _parse_mysql_url(url_str: str) -> Dict[str, Any]:
    parsed = urllib.parse.urlparse(url_str)
    
    # DB 스페이스 격리: CBT_DATABASE -> CBT_DATABASE_URL의 db명 -> 'cbt' 기본값
    # (snowball/trade의 DATABASE_URL을 로드하더라도 호스트/계정 정보만 공유하고 DB는 'cbt'로 엄격히 분리)
    cbt_db_name = os.getenv("CBT_DATABASE")
    if not cbt_db_name:
        if os.getenv("CBT_DATABASE_URL"):
            cbt_db_name = urllib.parse.urlparse(os.getenv("CBT_DATABASE_URL")).path.lstrip("/")
        else:
            cbt_db_name = "cbt"

    return {
        "host": parsed.hostname or "127.0.0.1",
        "port": parsed.port or 3306,
        "user": parsed.username or "root",
        "password": parsed.password or "150606",
        "database": cbt_db_name,
        "charset": "utf8mb4",
    }


def init_db():
    """데이터베이스 및 테이블 초기화"""
    if DB_TYPE == "mysql":
        import pymysql

        config = _parse_mysql_url(DATABASE_URL)
        db_name = config["database"]

        # 1) cbt 데이터베이스 생성
        server_config = config.copy()
        server_config.pop("database", None)
        conn = pymysql.connect(**server_config, autocommit=True)
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.close()

        # 2) cbt 테이블 생성
        conn = pymysql.connect(**config, autocommit=True)
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS exam_results (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    user_name VARCHAR(100) DEFAULT 'user',
                    exam_id VARCHAR(100),
                    exam_title VARCHAR(255),
                    total_score DECIMAL(5,2),
                    max_score DECIMAL(5,2),
                    is_pass TINYINT(1) DEFAULT 0,
                    fail_reason VARCHAR(255),
                    time_taken_seconds INT DEFAULT 0,
                    subject_scores_json JSON,
                    user_answers_json JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_user_created (user_name, created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS exam_drafts (
                    user_name VARCHAR(100) PRIMARY KEY,
                    exam_path VARCHAR(255),
                    exam_title VARCHAR(255),
                    user_answers_json JSON,
                    remaining_seconds INT DEFAULT 0,
                    current_question_idx INT DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
        conn.close()
        print(f"[CBT DB] [운영서버 모드] MySQL '{db_name}' 데이터베이스 및 테이블 준비 완료.")
        return

    # 개발 모드: SQLite 초기화
    conn = sqlite3.connect(DEFAULT_SQLITE_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS exam_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT DEFAULT 'user',
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
    cursor.execute(
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
    conn.commit()
    conn.close()
    print("[CBT DB] [개발서버 모드] SQLite 테이블 준비 완료.")


class DB:
    """DB 쿼리 실행 헬퍼 (운영: MySQL cbt / 개발: SQLite)"""

    @staticmethod
    def _get_mysql_conn():
        import pymysql
        import pymysql.cursors

        config = _parse_mysql_url(DATABASE_URL)
        return pymysql.connect(
            **config,
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
            connect_timeout=5,
        )

    @staticmethod
    def _get_sqlite_conn():
        conn = sqlite3.connect(DEFAULT_SQLITE_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    @classmethod
    def is_mysql(cls) -> bool:
        return DB_TYPE == "mysql"

    @classmethod
    def get_draft(cls, user_name: str) -> Optional[Dict[str, Any]]:
        """임시저장 데이터 조회"""
        if cls.is_mysql():
            conn = cls._get_mysql_conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT user_name, exam_path, exam_title, user_answers_json, remaining_seconds, current_question_idx, updated_at "
                        "FROM exam_drafts WHERE user_name = %s",
                        (user_name,),
                    )
                    row = cur.fetchone()
                if row:
                    if isinstance(row.get("user_answers_json"), str):
                        row["user_answers_json"] = json.loads(row["user_answers_json"] or "{}")
                    if row.get("updated_at"):
                        row["updated_at"] = str(row["updated_at"])
                return row
            finally:
                conn.close()
        else:
            conn = cls._get_sqlite_conn()
            try:
                cur = conn.cursor()
                cur.execute("SELECT * FROM exam_drafts WHERE user_name = ?", (user_name,))
                row = cur.fetchone()
                if row:
                    d = dict(row)
                    d["user_answers_json"] = json.loads(d.get("user_answers_json") or "{}")
                    return d
                return None
            finally:
                conn.close()

    @classmethod
    def save_draft(
        cls,
        user_name: str,
        exam_path: str,
        exam_title: str,
        user_answers: Dict[str, Any],
        remaining_seconds: int,
        current_question_idx: int,
    ) -> bool:
        """임시저장 데이터 저장 (Upsert)"""
        user_answers_str = json.dumps(user_answers, ensure_ascii=False)

        if cls.is_mysql():
            conn = cls._get_mysql_conn()
            try:
                with conn.cursor() as cur:
                    sql = """
                        INSERT INTO exam_drafts (
                            user_name, exam_path, exam_title, user_answers_json, remaining_seconds, current_question_idx, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ON DUPLICATE KEY UPDATE
                            exam_path = VALUES(exam_path),
                            exam_title = VALUES(exam_title),
                            user_answers_json = VALUES(user_answers_json),
                            remaining_seconds = VALUES(remaining_seconds),
                            current_question_idx = VALUES(current_question_idx),
                            updated_at = CURRENT_TIMESTAMP
                    """
                    cur.execute(
                        sql,
                        (
                            user_name,
                            exam_path,
                            exam_title,
                            user_answers_str,
                            remaining_seconds,
                            current_question_idx,
                        ),
                    )
                return True
            finally:
                conn.close()
        else:
            conn = cls._get_sqlite_conn()
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO exam_drafts (
                        user_name, exam_path, exam_title, user_answers_json, remaining_seconds, current_question_idx, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(user_name) DO UPDATE SET
                        exam_path = excluded.exam_path,
                        exam_title = excluded.exam_title,
                        user_answers_json = excluded.user_answers_json,
                        remaining_seconds = excluded.remaining_seconds,
                        current_question_idx = excluded.current_question_idx,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        user_name,
                        exam_path,
                        exam_title,
                        user_answers_str,
                        remaining_seconds,
                        current_question_idx,
                    ),
                )
                conn.commit()
                return True
            finally:
                conn.close()

    @classmethod
    def delete_draft(cls, user_name: str) -> int:
        """임시저장 데이터 삭제"""
        if cls.is_mysql():
            conn = cls._get_mysql_conn()
            try:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM exam_drafts WHERE user_name = %s", (user_name,))
                    return cur.rowcount
            finally:
                conn.close()
        else:
            conn = cls._get_sqlite_conn()
            try:
                cur = conn.cursor()
                cur.execute("DELETE FROM exam_drafts WHERE user_name = ?", (user_name,))
                cnt = cur.rowcount
                conn.commit()
                return cnt
            finally:
                conn.close()

    @classmethod
    def get_results_list(cls, limit: int = 50) -> List[Dict[str, Any]]:
        """응시 결과 목록 조회"""
        if cls.is_mysql():
            conn = cls._get_mysql_conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, user_name, exam_id, exam_title, 
                               CAST(total_score AS FLOAT) AS total_score, 
                               CAST(max_score AS FLOAT) AS max_score, 
                               is_pass, fail_reason, time_taken_seconds, 
                               created_at
                        FROM exam_results 
                        ORDER BY id DESC 
                        LIMIT %s
                        """,
                        (limit,),
                    )
                    rows = cur.fetchall()
                for r in rows:
                    if r.get("created_at"):
                        r["created_at"] = str(r["created_at"])
                return rows
            finally:
                conn.close()
        else:
            conn = cls._get_sqlite_conn()
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT id, user_name, exam_id, exam_title, total_score, max_score, is_pass, fail_reason, time_taken_seconds, created_at 
                    FROM exam_results ORDER BY id DESC LIMIT ?
                    """,
                    (limit,),
                )
                return [dict(r) for r in cur.fetchall()]
            finally:
                conn.close()

    @classmethod
    def get_result_detail(cls, result_id: int) -> Optional[Dict[str, Any]]:
        """응시 결과 상세 조회"""
        if cls.is_mysql():
            conn = cls._get_mysql_conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, user_name, exam_id, exam_title, 
                               CAST(total_score AS FLOAT) AS total_score, 
                               CAST(max_score AS FLOAT) AS max_score, 
                               is_pass, fail_reason, time_taken_seconds, 
                               subject_scores_json, user_answers_json,
                               created_at
                        FROM exam_results 
                        WHERE id = %s
                        """,
                        (result_id,),
                    )
                    row = cur.fetchone()
                if row:
                    if row.get("created_at"):
                        row["created_at"] = str(row["created_at"])
                    if not isinstance(row.get("subject_scores_json"), str):
                        row["subject_scores_json"] = json.dumps(row.get("subject_scores_json") or [], ensure_ascii=False)
                    if not isinstance(row.get("user_answers_json"), str):
                        row["user_answers_json"] = json.dumps(row.get("user_answers_json") or {}, ensure_ascii=False)
                return row
            finally:
                conn.close()
        else:
            conn = cls._get_sqlite_conn()
            try:
                cur = conn.cursor()
                cur.execute("SELECT * FROM exam_results WHERE id = ?", (result_id,))
                row = cur.fetchone()
                return dict(row) if row else None
            finally:
                conn.close()

    @classmethod
    def save_result(
        cls,
        user_name: str,
        exam_id: str,
        exam_title: str,
        total_score: float,
        max_score: float,
        is_pass: bool,
        fail_reason: str,
        time_taken_seconds: int,
        subject_scores: List[Any],
        user_answers: Dict[str, Any],
    ) -> int:
        """응시 결과 저장 및 임시저장 내역 삭제"""
        subj_str = json.dumps(subject_scores, ensure_ascii=False)
        ans_str = json.dumps(user_answers, ensure_ascii=False)
        is_pass_val = 1 if is_pass else 0

        if cls.is_mysql():
            conn = cls._get_mysql_conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO exam_results (
                            user_name, exam_id, exam_title, total_score, max_score, is_pass, fail_reason, time_taken_seconds, subject_scores_json, user_answers_json
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            user_name,
                            exam_id,
                            exam_title,
                            total_score,
                            max_score,
                            is_pass_val,
                            fail_reason,
                            time_taken_seconds,
                            subj_str,
                            ans_str,
                        ),
                    )
                    new_id = cur.lastrowid
                    cur.execute("DELETE FROM exam_drafts WHERE user_name = %s", (user_name,))
                return new_id
            finally:
                conn.close()
        else:
            conn = cls._get_sqlite_conn()
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO exam_results (
                        user_name, exam_id, exam_title, total_score, max_score, is_pass, fail_reason, time_taken_seconds, subject_scores_json, user_answers_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_name,
                        exam_id,
                        exam_title,
                        total_score,
                        max_score,
                        is_pass_val,
                        fail_reason,
                        time_taken_seconds,
                        subj_str,
                        ans_str,
                    ),
                )
                new_id = cur.lastrowid
                cur.execute("DELETE FROM exam_drafts WHERE user_name = ?", (user_name,))
                conn.commit()
                return new_id
            finally:
                conn.close()

    @classmethod
    def delete_result(cls, result_id: int) -> int:
        """응시 결과 단건 삭제"""
        if cls.is_mysql():
            conn = cls._get_mysql_conn()
            try:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM exam_results WHERE id = %s", (result_id,))
                    return cur.rowcount
            finally:
                conn.close()
        else:
            conn = cls._get_sqlite_conn()
            try:
                cur = conn.cursor()
                cur.execute("DELETE FROM exam_results WHERE id = ?", (result_id,))
                cnt = cur.rowcount
                conn.commit()
                return cnt
            finally:
                conn.close()

    @classmethod
    def clear_all_results(cls) -> int:
        """전체 응시 결과 삭제"""
        if cls.is_mysql():
            conn = cls._get_mysql_conn()
            try:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM exam_results")
                    return cur.rowcount
            finally:
                conn.close()
        else:
            conn = cls._get_sqlite_conn()
            try:
                cur = conn.cursor()
                cur.execute("DELETE FROM exam_results")
                cnt = cur.rowcount
                conn.commit()
                return cnt
            finally:
                conn.close()
