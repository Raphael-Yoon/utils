"""
[개발4팀 전사 공통 모듈] CBT 모의고사 전용 HTTP 서버 및 러너 (Run CBT Server)
기능: utils/cbt_engine/exams/ 폴더의 모든 시험 데이터를 자동 탐색하여 제공합니다. (한글 URL 인코딩 완벽 지원)
데이터베이스: MySQL 전용 DB 스페이스('cbt') 및 SQLite 듀얼 모드 지원
"""

import sys
import os
import json
import re
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = BASE_DIR.parent.parent
if str(WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_DIR))
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# CBT DB 어댑터 모듈 임포트
try:
    from utils.cbt_engine.db import DB, init_db, DB_TYPE, DATABASE_URL
except ImportError:
    from db import DB, init_db, DB_TYPE, DATABASE_URL
EXAMS_DIR = BASE_DIR / "exams"


class CBTRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path_only = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # /api/draft - 서버 임시저장 조회
        if path_only == '/api/draft':
            user_name = query.get('user_name', ['응시자'])[0]
            row = DB.get_draft(user_name)

            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()

            user_answers = row.get("user_answers_json", {}) if row else {}
            if row and user_answers:
                draft_data = {
                    "user_name": row["user_name"],
                    "examPath": row["exam_path"],
                    "examTitle": row["exam_title"],
                    "userAnswers": user_answers,
                    "remainingSeconds": row["remaining_seconds"],
                    "currentQuestionIdx": row["current_question_idx"],
                    "updatedAt": str(row["updated_at"])
                }
                self.wfile.write(json.dumps(draft_data, ensure_ascii=False).encode('utf-8'))
            else:
                # 응답한 문항이 하나도 없는 임시저장(진행률 0)은 이어하기 대상에서 제외
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
                        })
                    except Exception as e:
                        print(f"시험 파일 읽기 오류 ({json_file.name}): {e}")

            # 시험 목록 정렬 (카테고리 가나다순 -> 1.연도별 세트(최신순) -> 2.과목별 세트(1~5과목순) -> 3.연도/과목별 세트(과목순 -> 연도 최신순))
            def get_sort_key(item):
                cat = item.get('category', '')
                title = item.get('title', '')
                filename = item.get('filename', '')

                # 1) 과목별 집중학습(연도 통합) 세트: [5개년] 1과목 ~ 5과목
                m_5yr = re.search(r'\[5개년\]\s*(\d+)과목', title)
                if m_5yr:
                    sub_no = int(m_5yr.group(1))
                    return (cat, 2, sub_no, 0)

                # 2) 연도별/과목별 세트: [YYYY년] X과목
                m_sub = re.search(r'\[(\d{4})년\]\s*(\d+)과목', title)
                if m_sub:
                    year = int(m_sub.group(1))
                    sub_no = int(m_sub.group(2))
                    return (cat, 3, sub_no, -year)

                # 3) 연도별 전체 모의고사: [YYYY년] 정보시스템감리사
                m_year_all = re.search(r'\[(\d{4})년\]', title)
                if m_year_all and '과목' not in title:
                    year = int(m_year_all.group(1))
                    return (cat, 1, -year, 0)

                # 4) 일반 회차/연도별 시험인 경우: 최신순(내림차순) 정렬
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
                return (cat, 1, -num, 0)

            exam_list.sort(key=get_sort_key)

            self.wfile.write(json.dumps(exam_list, ensure_ascii=False).encode('utf-8'))
            return

        # /api/results - 응시 이력 목록/상세 조회
        if path_only == '/api/results':
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()

            if 'id' in query:
                result_id = int(query['id'][0])
                res_data = DB.get_result_detail(result_id)
            else:
                res_data = DB.get_results_list(limit=50)

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
            DB.save_draft(
                user_name=user_name,
                exam_path=payload.get('examPath', ''),
                exam_title=payload.get('examTitle', ''),
                user_answers=payload.get('userAnswers', {}),
                remaining_seconds=payload.get('remainingSeconds', 0),
                current_question_idx=payload.get('currentQuestionIdx', 0)
            )

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

            new_id = DB.save_result(
                user_name=payload.get('user_name', '응시자'),
                exam_id=payload.get('exam_id', ''),
                exam_title=payload.get('exam_title', ''),
                total_score=float(payload.get('total_score', 0.0)),
                max_score=float(payload.get('max_score', 100.0)),
                is_pass=bool(payload.get('is_pass')),
                fail_reason=payload.get('fail_reason', ''),
                time_taken_seconds=int(payload.get('time_taken_seconds', 0)),
                subject_scores=payload.get('subject_scores', []),
                user_answers=payload.get('user_answers', {})
            )

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
            deleted_cnt = DB.delete_draft(user_name)

            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "deleted_count": deleted_cnt}, ensure_ascii=False).encode('utf-8'))
            return

        # /api/results - 응시 이력 삭제 (단건 삭제: ?id=X, 전체 삭제: ?all=true)
        if path_only == '/api/results':
            if 'id' in query:
                result_id = int(query['id'][0])
                deleted_cnt = DB.delete_result(result_id)
            elif query.get('all', [''])[0] == 'true':
                deleted_cnt = DB.clear_all_results()
            else:
                self.send_error(400, "Bad Request: Missing 'id' or 'all=true' parameter")
                return

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
    HTTPServer.allow_reuse_address = True
    server_address = ('', port)
    httpd = HTTPServer(server_address, CBTRequestHandler)
    url = f"http://localhost:{port}"
    db_mode = "MySQL (cbt DB)" if DB.is_mysql() else "SQLite"
    print(f"==================================================")
    print(f"🚀 [개발4팀 CBT Engine Server] 구동 성공! (DB 연동 완료)")
    print(f"📁 시험 데이터 폴더: {EXAMS_DIR}")
    print(f"🗄️ 성적 DB 모드: {db_mode}")
    print(f"🌐 접속 주소: {url}")
    print(f"==================================================")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nCBT 서버를 종료합니다.")


if __name__ == '__main__':
    default_port = int(os.getenv("CBT_PORT", "8080"))
    port = int(sys.argv[1]) if len(sys.argv) > 1 else default_port
    run(port)
