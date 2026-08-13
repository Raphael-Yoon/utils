"""
[개발4팀 전사 공통 모듈] CBT 모의고사 전용 HTTP 서버 및 러너 (Run CBT Server)
기능: utils/cbt_engine/exams/ 폴더의 모든 시험 데이터를 자동 탐색하여 제공합니다. (한글 URL 인코딩 완벽 지원)
"""

import sys
import json
import re
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

import sqlite3

BASE_DIR = Path(__file__).parent
EXAMS_DIR = BASE_DIR / "exams"
DB_PATH = BASE_DIR / "cbt_results.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
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
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exam_drafts (
            user_name TEXT PRIMARY KEY,
            exam_path TEXT,
            exam_title TEXT,
            user_answers_json TEXT,
            remaining_seconds INTEGER,
            current_question_idx INTEGER,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

class CBTRequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path_only = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # /api/draft - 서버 임시저장 조회
        if path_only == '/api/draft':
            user_name = query.get('user_name', ['응시자'])[0]
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM exam_drafts WHERE user_name = ?', (user_name,))
            row = cursor.fetchone()
            conn.close()

            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            if row:
                draft_data = {
                    "user_name": row["user_name"],
                    "examPath": row["exam_path"],
                    "examTitle": row["exam_title"],
                    "userAnswers": json.loads(row["user_answers_json"] or '{}'),
                    "remainingSeconds": row["remaining_seconds"],
                    "currentQuestionIdx": row["current_question_idx"],
                    "updatedAt": row["updated_at"]
                }
                self.wfile.write(json.dumps(draft_data, ensure_ascii=False).encode('utf-8'))
            else:
                self.wfile.write(json.dumps(None, ensure_ascii=False).encode('utf-8'))
            return

        # /api/exams 요청 시 exams/ 폴더 내 전체 시험 파일 목록 반환
        if path_only == '/api/exams':
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            
            exam_list = []
            if EXAMS_DIR.exists():
                for json_file in EXAMS_DIR.glob('*.json'):
                    try:
                        data = json.loads(json_file.read_text(encoding='utf-8'))
                        info = data.get('exam_info', {})
                        exam_list.append({
                            "filename": json_file.name,
                            "title": info.get('title', json_file.stem),
                            "category": info.get('category', '자격증'),
                            "time_limit_minutes": info.get('time_limit_minutes', 120),
                            "passing_rules": info.get('passing_rules', {}),
                            "subjects": data.get('subjects', []),
                            "questions_count": len(data.get('questions', [])),
                            "path": f"/exams/{json_file.name}"
                        })
                    except Exception:
                        pass
            
            # 시험 목록 정렬 (카테고리 가나다순, 회차 번호 오름차순: 제1회->제2회... / 77회->78회->79회)
            def get_sort_key(item):
                title = item.get('title', '')
                filename = item.get('filename', '')
                m_round = re.search(r'제\s*(\d+)\s*회', title) or re.search(r'(\d+)\s*회', title)
                if m_round:
                    num = int(m_round.group(1))
                else:
                    m_file = re.search(r'(\d+)', filename)
                    if m_file:
                        num = int(m_file.group(1))
                    else:
                        matches = re.findall(r'\d+', title)
                        num = int(matches[-1]) if matches else 0
                return (item.get('category', ''), num)

            exam_list.sort(key=get_sort_key)

            self.wfile.write(json.dumps(exam_list, ensure_ascii=False).encode('utf-8'))
            return

        # /api/results - 응시 이력 목록 조회
        if path_only == '/api/results':
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if 'id' in query:
                result_id = query['id'][0]
                cursor.execute('SELECT * FROM exam_results WHERE id = ?', (result_id,))
                row = cursor.fetchone()
                res_data = dict(row) if row else None
            else:
                cursor.execute('''
                    SELECT id, user_name, exam_id, exam_title, total_score, max_score, is_pass, fail_reason, time_taken_seconds, created_at 
                    FROM exam_results ORDER BY id DESC LIMIT 50
                ''')
                res_data = [dict(r) for r in cursor.fetchall()]

            conn.close()
            self.wfile.write(json.dumps(res_data, ensure_ascii=False).encode('utf-8'))
            return

        super().do_GET()

    def do_POST(self):
        # /api/draft - 시험 진행 상태 서버 임시저장
        if self.path == '/api/draft':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            payload = json.loads(body.decode('utf-8'))

            user_name = payload.get('user_name', '응시자')
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
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
            ''', (
                user_name,
                payload.get('examPath', ''),
                payload.get('examTitle', ''),
                json.dumps(payload.get('userAnswers', {}), ensure_ascii=False),
                payload.get('remainingSeconds', 0),
                payload.get('currentQuestionIdx', 0)
            ))
            conn.commit()
            conn.close()

            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}, ensure_ascii=False).encode('utf-8'))
            return

        # /api/results - 시험 채점 결과 저장
        if self.path == '/api/results':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            payload = json.loads(body.decode('utf-8'))

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO exam_results (
                    user_name, exam_id, exam_title, total_score, max_score, is_pass, fail_reason, time_taken_seconds, subject_scores_json, user_answers_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                payload.get('user_name', '응시자'),
                payload.get('exam_id', ''),
                payload.get('exam_title', ''),
                payload.get('total_score', 0.0),
                payload.get('max_score', 100.0),
                1 if payload.get('is_pass') else 0,
                payload.get('fail_reason', ''),
                payload.get('time_taken_seconds', 0),
                json.dumps(payload.get('subject_scores', []), ensure_ascii=False),
                json.dumps(payload.get('user_answers', {}), ensure_ascii=False)
            ))
            new_id = cursor.lastrowid

            # 제출 완료 시 해당 유저의 draft 삭제
            cursor.execute('DELETE FROM exam_drafts WHERE user_name = ?', (payload.get('user_name', '응시자'),))
            conn.commit()
            conn.close()

            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "id": new_id}, ensure_ascii=False).encode('utf-8'))
            return

        self.send_error(404, "Not Found")

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path_only = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # /api/draft - 임시저장 삭제
        if path_only == '/api/draft':
            user_name = query.get('user_name', ['응시자'])[0]
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM exam_drafts WHERE user_name = ?', (user_name,))
            deleted_cnt = cursor.rowcount
            conn.commit()
            conn.close()

            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "deleted_count": deleted_cnt}, ensure_ascii=False).encode('utf-8'))
            return

        # /api/results - 응시 이력 삭제 (단건 삭제: ?id=X, 전체 삭제: ?all=true)
        if path_only == '/api/results':
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            if 'id' in query:
                result_id = query['id'][0]
                cursor.execute('DELETE FROM exam_results WHERE id = ?', (result_id,))
                deleted_cnt = cursor.rowcount
            elif query.get('all', [''])[0] == 'true':
                cursor.execute('DELETE FROM exam_results')
                deleted_cnt = cursor.rowcount
            else:
                conn.close()
                self.send_error(400, "Bad Request: Missing 'id' or 'all=true' parameter")
                return

            conn.commit()
            conn.close()

            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "deleted_count": deleted_cnt}, ensure_ascii=False).encode('utf-8'))
            return

        self.send_error(404, "Not Found")

    def translate_path(self, path):
        # URL 디코딩 처리 (한글 파일명 %EB%B9%85... 인코딩 해제)
        decoded_path = urllib.parse.unquote(path)
        rel_path = decoded_path.lstrip('/')
        if not rel_path:
            rel_path = 'index.html'
        
        target = BASE_DIR / rel_path
        return str(target)

def run(port=8080):
    init_db()
    server_address = ('', port)
    httpd = HTTPServer(server_address, CBTRequestHandler)
    url = f"http://localhost:{port}"
    print(f"==================================================")
    print(f"🚀 [개발4팀 CBT Engine Server] 구동 성공! (DB 연동 완료)")
    print(f"📁 시험 데이터 폴더: {EXAMS_DIR}")
    print(f"🗄️ 성적 DB 파일: {DB_PATH}")
    print(f"🌐 접속 주소: {url}")
    print(f"==================================================")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nCBT 서버를 종료합니다.")

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run(port)
