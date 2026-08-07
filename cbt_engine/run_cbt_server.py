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
    conn.commit()
    conn.close()

class CBTRequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path_only = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

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
            
            # 회차 숫자를 추출하여 내림차순(10회 -> 9회 -> ... -> 3회) 정렬
            def get_round_num(item):
                m = re.search(r'(\d+)', item['filename'])
                if not m:
                    m = re.search(r'(\d+)회', item['title'])
                return int(m.group(1)) if m else 0

            exam_list.sort(key=get_round_num, reverse=True)

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
            conn.commit()
            conn.close()

            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "id": new_id}, ensure_ascii=False).encode('utf-8'))
            return

        self.send_error(404, "Not Found")

    def do_DELETE(self):
        # /api/results - 응시 이력 삭제 (단건 삭제: ?id=X, 전체 삭제: ?all=true)
        parsed = urllib.parse.urlparse(self.path)
        path_only = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

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
