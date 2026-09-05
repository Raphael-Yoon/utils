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
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS exam_category_locks (
                    category_name VARCHAR(100) PRIMARY KEY,
                    is_locked TINYINT(1) DEFAULT 1,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS exam_schedules (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    category_id VARCHAR(50) DEFAULT '',
                    title VARCHAR(150) NOT NULL,
                    round_name VARCHAR(100) DEFAULT '',
                    apply_start_date VARCHAR(20) DEFAULT '',
                    apply_end_date VARCHAR(20) DEFAULT '',
                    exam_date VARCHAR(20) NOT NULL,
                    result_date VARCHAR(20) DEFAULT '',
                    color_tag VARCHAR(20) DEFAULT '#3b82f6',
                    target_score INT DEFAULT 60,
                    agency_url VARCHAR(255) DEFAULT '',
                    memo TEXT,
                    is_target TINYINT(1) DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_exam_date (exam_date)
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
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS exam_category_locks (
            category_name TEXT PRIMARY KEY,
            is_locked INTEGER DEFAULT 1,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS exam_schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id TEXT DEFAULT '',
            title TEXT NOT NULL,
            round_name TEXT DEFAULT '',
            apply_start_date TEXT DEFAULT '',
            apply_end_date TEXT DEFAULT '',
            exam_date TEXT NOT NULL,
            result_date TEXT DEFAULT '',
            color_tag TEXT DEFAULT '#3b82f6',
            target_score INTEGER DEFAULT 60,
            agency_url TEXT DEFAULT '',
            memo TEXT DEFAULT '',
            is_target INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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

    @classmethod
    def get_locked_categories(cls) -> List[str]:
        """잠금 처리된 자격시험 종목(카테고리) 목록 조회"""
        if cls.is_mysql():
            conn = cls._get_mysql_conn()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT category_name FROM exam_category_locks WHERE is_locked = 1")
                    rows = cur.fetchall()
                    return [r["category_name"] for r in rows]
            finally:
                conn.close()
        else:
            conn = cls._get_sqlite_conn()
            try:
                cur = conn.cursor()
                cur.execute("SELECT category_name FROM exam_category_locks WHERE is_locked = 1")
                rows = cur.fetchall()
                return [r["category_name"] for r in rows]
            finally:
                conn.close()

    @classmethod
    def set_category_lock(cls, category_name: str, is_locked: bool) -> bool:
        """자격시험 종목 잠금 상태 설정/해제"""
        lock_val = 1 if is_locked else 0
        if cls.is_mysql():
            conn = cls._get_mysql_conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO exam_category_locks (category_name, is_locked)
                        VALUES (%s, %s)
                        ON DUPLICATE KEY UPDATE is_locked = VALUES(is_locked), updated_at = CURRENT_TIMESTAMP
                        """,
                        (category_name, lock_val),
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
                    INSERT INTO exam_category_locks (category_name, is_locked)
                    VALUES (?, ?)
                    ON CONFLICT(category_name) DO UPDATE SET is_locked = excluded.is_locked, updated_at = CURRENT_TIMESTAMP
                    """,
                    (category_name, lock_val),
                )
                conn.commit()
                return True
            finally:
                conn.close()

    @classmethod
    def get_schedules(cls) -> List[Dict[str, Any]]:
        """등록된 모든 시험 일정 목록 조회 (시험일 기준 정렬)"""
        sql = """
            SELECT id, category_id, title, round_name, apply_start_date, apply_end_date,
                   exam_date, result_date, color_tag, target_score, agency_url, memo, is_target,
                   created_at, updated_at
            FROM exam_schedules
            ORDER BY exam_date ASC, id ASC
        """
        if cls.is_mysql():
            conn = cls._get_mysql_conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(sql)
                    rows = cur.fetchall()
                    for r in rows:
                        r["is_target"] = bool(r.get("is_target", 0))
                        if "created_at" in r and r["created_at"]:
                            r["created_at"] = str(r["created_at"])
                        if "updated_at" in r and r["updated_at"]:
                            r["updated_at"] = str(r["updated_at"])
                    return rows
            finally:
                conn.close()
        else:
            conn = cls._get_sqlite_conn()
            try:
                cur = conn.cursor()
                cur.execute(sql)
                rows = cur.fetchall()
                results = []
                for r in rows:
                    item = dict(r)
                    item["is_target"] = bool(item.get("is_target", 0))
                    results.append(item)
                return results
            finally:
                conn.close()

    @classmethod
    def get_schedule(cls, schedule_id: int) -> Optional[Dict[str, Any]]:
        """시험 일정 단건 조회"""
        sql = """
            SELECT id, category_id, title, round_name, apply_start_date, apply_end_date,
                   exam_date, result_date, color_tag, target_score, agency_url, memo, is_target,
                   created_at, updated_at
            FROM exam_schedules
            WHERE id = %s
        """ if cls.is_mysql() else """
            SELECT id, category_id, title, round_name, apply_start_date, apply_end_date,
                   exam_date, result_date, color_tag, target_score, agency_url, memo, is_target,
                   created_at, updated_at
            FROM exam_schedules
            WHERE id = ?
        """
        if cls.is_mysql():
            conn = cls._get_mysql_conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(sql, (schedule_id,))
                    row = cur.fetchone()
                    if row:
                        row["is_target"] = bool(row.get("is_target", 0))
                    return row
            finally:
                conn.close()
        else:
            conn = cls._get_sqlite_conn()
            try:
                cur = conn.cursor()
                cur.execute(sql, (schedule_id,))
                row = cur.fetchone()
                if row:
                    item = dict(row)
                    item["is_target"] = bool(item.get("is_target", 0))
                    return item
                return None
            finally:
                conn.close()

    @classmethod
    def save_schedule(cls, data: Dict[str, Any]) -> int:
        """신규 시험 일정 등록"""
        title = data.get("title", "").strip()
        category_id = data.get("category_id", "").strip()
        round_name = data.get("round_name", "").strip()
        apply_start_date = data.get("apply_start_date", "").strip()
        apply_end_date = data.get("apply_end_date", "").strip()
        exam_date = data.get("exam_date", "").strip()
        result_date = data.get("result_date", "").strip()
        color_tag = data.get("color_tag", "#3b82f6").strip()
        target_score = int(data.get("target_score", 60))
        agency_url = data.get("agency_url", "").strip()
        memo = data.get("memo", "").strip()
        is_target = 1 if data.get("is_target") else 0

        # 만약 새로 등록한 일정이 target이면 기존 것들 해제
        if is_target:
            cls.clear_target_schedule()

        if cls.is_mysql():
            conn = cls._get_mysql_conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO exam_schedules (
                            category_id, title, round_name, apply_start_date, apply_end_date,
                            exam_date, result_date, color_tag, target_score, agency_url, memo, is_target
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (category_id, title, round_name, apply_start_date, apply_end_date,
                         exam_date, result_date, color_tag, target_score, agency_url, memo, is_target),
                    )
                    return cur.lastrowid
            finally:
                conn.close()
        else:
            conn = cls._get_sqlite_conn()
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO exam_schedules (
                        category_id, title, round_name, apply_start_date, apply_end_date,
                        exam_date, result_date, color_tag, target_score, agency_url, memo, is_target
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (category_id, title, round_name, apply_start_date, apply_end_date,
                     exam_date, result_date, color_tag, target_score, agency_url, memo, is_target),
                )
                new_id = cur.lastrowid
                conn.commit()
                return new_id
            finally:
                conn.close()

    @classmethod
    def update_schedule(cls, schedule_id: int, data: Dict[str, Any]) -> bool:
        """시험 일정 정보 수정"""
        title = data.get("title", "").strip()
        category_id = data.get("category_id", "").strip()
        round_name = data.get("round_name", "").strip()
        apply_start_date = data.get("apply_start_date", "").strip()
        apply_end_date = data.get("apply_end_date", "").strip()
        exam_date = data.get("exam_date", "").strip()
        result_date = data.get("result_date", "").strip()
        color_tag = data.get("color_tag", "#3b82f6").strip()
        target_score = int(data.get("target_score", 60))
        agency_url = data.get("agency_url", "").strip()
        memo = data.get("memo", "").strip()
        is_target = 1 if data.get("is_target") else 0

        if is_target:
            cls.clear_target_schedule(exclude_id=schedule_id)

        if cls.is_mysql():
            conn = cls._get_mysql_conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE exam_schedules
                        SET category_id = %s, title = %s, round_name = %s, apply_start_date = %s,
                            apply_end_date = %s, exam_date = %s, result_date = %s, color_tag = %s,
                            target_score = %s, agency_url = %s, memo = %s, is_target = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        """,
                        (category_id, title, round_name, apply_start_date, apply_end_date,
                         exam_date, result_date, color_tag, target_score, agency_url, memo, is_target, schedule_id),
                    )
                    return cur.rowcount > 0
            finally:
                conn.close()
        else:
            conn = cls._get_sqlite_conn()
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    UPDATE exam_schedules
                    SET category_id = ?, title = ?, round_name = ?, apply_start_date = ?,
                        apply_end_date = ?, exam_date = ?, result_date = ?, color_tag = ?,
                        target_score = ?, agency_url = ?, memo = ?, is_target = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (category_id, title, round_name, apply_start_date, apply_end_date,
                     exam_date, result_date, color_tag, target_score, agency_url, memo, is_target, schedule_id),
                )
                conn.commit()
                return cur.rowcount > 0
            finally:
                conn.close()

    @classmethod
    def delete_schedule(cls, schedule_id: int) -> int:
        """시험 일정 단건 삭제"""
        if cls.is_mysql():
            conn = cls._get_mysql_conn()
            try:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM exam_schedules WHERE id = %s", (schedule_id,))
                    return cur.rowcount
            finally:
                conn.close()
        else:
            conn = cls._get_sqlite_conn()
            try:
                cur = conn.cursor()
                cur.execute("DELETE FROM exam_schedules WHERE id = ?", (schedule_id,))
                cnt = cur.rowcount
                conn.commit()
                return cnt
            finally:
                conn.close()

    @classmethod
    def clear_target_schedule(cls, exclude_id: Optional[int] = None):
        """기존 목표 시험 설정 초기화"""
        if cls.is_mysql():
            conn = cls._get_mysql_conn()
            try:
                with conn.cursor() as cur:
                    if exclude_id:
                        cur.execute("UPDATE exam_schedules SET is_target = 0 WHERE id != %s", (exclude_id,))
                    else:
                        cur.execute("UPDATE exam_schedules SET is_target = 0")
            finally:
                conn.close()
        else:
            conn = cls._get_sqlite_conn()
            try:
                cur = conn.cursor()
                if exclude_id:
                    cur.execute("UPDATE exam_schedules SET is_target = 0 WHERE id != ?", (exclude_id,))
                else:
                    cur.execute("UPDATE exam_schedules SET is_target = 0")
                conn.commit()
            finally:
                conn.close()

    @classmethod
    def set_target_schedule(cls, schedule_id: int) -> bool:
        """특정 시험 일정을 대표 목표 시험으로 설정/토글"""
        current = cls.get_schedule(schedule_id)
        if not current:
            return False
        new_target = 0 if current.get("is_target") else 1
        
        cls.clear_target_schedule()
        if new_target == 1:
            if cls.is_mysql():
                conn = cls._get_mysql_conn()
                try:
                    with conn.cursor() as cur:
                        cur.execute("UPDATE exam_schedules SET is_target = 1 WHERE id = %s", (schedule_id,))
                finally:
                    conn.close()
            else:
                conn = cls._get_sqlite_conn()
                try:
                    cur = conn.cursor()
                    cur.execute("UPDATE exam_schedules SET is_target = 1 WHERE id = ?", (schedule_id,))
                    conn.commit()
                finally:
                    conn.close()
        return True

