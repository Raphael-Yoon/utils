"""
[개발4팀 전사 공통 모듈] 풀어봄 (Pool-eobom) CBT 모의고사 전용 HTTP 서버 및 러너 (Run CBT Server)
기능: utils/cbt_engine/exams/ 폴더의 모든 시험 데이터를 자동 탐색하여 제공합니다. (한글 URL 인코딩 완벽 지원)
데이터베이스: MySQL 전용 DB 스페이스('cbt') 및 SQLite 듀얼 모드 지원
"""

import sys
import os
import json
import re
import urllib.parse
from datetime import datetime, date
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
CRAM_SHEETS_DIR = BASE_DIR / "reviews" / "cram_sheets"


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
            user_name = query.get('user_name', ['user'])[0]
            row = DB.get_draft(user_name)
            if not row and user_name == 'user':
                row = DB.get_draft('응시자')

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

        # /api/category-locks - 자격시험 종목 잠금 목록 반환
        if path_only == '/api/category-locks':
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            locked = DB.get_locked_categories()
            self.wfile.write(json.dumps({"locked_categories": locked}, ensure_ascii=False).encode('utf-8'))
            return

        # /api/cram-sheets - 시험 직전 핵심 요약본(파이널 치트시트) 목록 및 내용 조회
        if path_only == '/api/cram-sheets':
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()

            requested_file = query.get('file', [None])[0] or query.get('id', [None])[0]
            if requested_file:
                if not requested_file.endswith('.md'):
                    requested_file = f"{requested_file}_직전요약본.md"
                target_path = CRAM_SHEETS_DIR / requested_file
                if target_path.exists():
                    try:
                        content = target_path.read_text(encoding='utf-8')
                        self.wfile.write(json.dumps({
                            "success": True,
                            "filename": target_path.name,
                            "content": content
                        }, ensure_ascii=False).encode('utf-8'))
                    except Exception as e:
                        self.wfile.write(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False).encode('utf-8'))
                else:
                    self.wfile.write(json.dumps({"success": False, "error": "요약본 파일을 찾을 수 없습니다."}, ensure_ascii=False).encode('utf-8'))
                return

            sheets = []
            CATEGORY_MAP = {
                "bigdata": "빅데이터분석기사",
                "auditor": "정보시스템감리사",
                "sqld": "SQL 개발자",
                "digital_forensic": "디지털포렌식전문가",
            }
            if CRAM_SHEETS_DIR.exists():
                for md_file in sorted(CRAM_SHEETS_DIR.glob('*_직전요약본.md')):
                    try:
                        first_line = ""
                        with open(md_file, 'r', encoding='utf-8') as f:
                            for line in f:
                                line = line.strip()
                                if line.startswith('#'):
                                    first_line = line.lstrip('#').strip()
                                    break
                        key = md_file.stem.replace('_직전요약본', '')
                        cat = CATEGORY_MAP.get(key, key)
                        sheets.append({
                            "id": key,
                            "filename": md_file.name,
                            "title": first_line or md_file.stem,
                            "category": cat,
                        })
                    except Exception as e:
                        print(f"요약본 파일 읽기 오류 ({md_file.name}): {e}")

            self.wfile.write(json.dumps({"sheets": sheets}, ensure_ascii=False).encode('utf-8'))
            return

        # /api/exams 요청 시 exams/ 폴더 내 전체 시험 파일 목록 반환
        if path_only == '/api/exams':
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            
            locked_cats = set(DB.get_locked_categories())
            exam_list = []
            if EXAMS_DIR.exists():
                for json_file in EXAMS_DIR.glob('*.json'):
                    try:
                        data = json.loads(json_file.read_text(encoding='utf-8'))
                        info = data.get('exam_info', {})
                        cat = info.get('category', '자격증')
                        exam_list.append({
                            "filename": json_file.name,
                            "title": info.get('title', json_file.stem),
                            "category": cat,
                            "is_category_locked": cat in locked_cats,
                            "time_limit_minutes": info.get('time_limit_minutes', 120),
                            "passing_rules": info.get('passing_rules', {}),
                            "subjects": data.get('subjects', []),
                            "questions_count": len(data.get('questions', [])),
                            "path": f"/exams/{json_file.name}",
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

        # /api/schedules - 시험 일정 목록 조회 (D-Day 및 접수 상태 포함)
        if path_only == '/api/schedules':
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()

            schedules = DB.get_schedules()
            today = datetime.now().date()
            for s in schedules:
                # D-Day 계산
                try:
                    exam_dt = datetime.strptime(s.get('exam_date', ''), '%Y-%m-%d').date()
                    s['d_day'] = (exam_dt - today).days
                except Exception:
                    s['d_day'] = None

                # 접수 상태 계산
                try:
                    start_str = s.get('apply_start_date', '')
                    end_str = s.get('apply_end_date', '')
                    if start_str and end_str:
                        st_dt = datetime.strptime(start_str, '%Y-%m-%d').date()
                        ed_dt = datetime.strptime(end_str, '%Y-%m-%d').date()
                        if today < st_dt:
                            s['apply_status'] = 'upcoming'
                            s['apply_days_left'] = (st_dt - today).days
                        elif st_dt <= today <= ed_dt:
                            s['apply_status'] = 'ongoing'
                            s['apply_days_left'] = (ed_dt - today).days
                        else:
                            s['apply_status'] = 'ended'
                            s['apply_days_left'] = 0
                    else:
                        s['apply_status'] = 'none'
                        s['apply_days_left'] = 0
                except Exception:
                    s['apply_status'] = 'none'
                    s['apply_days_left'] = 0

            self.wfile.write(json.dumps(schedules, ensure_ascii=False).encode('utf-8'))
            return

        super().do_GET()

    def do_POST(self):
        # /api/draft - 시험 진행 상태 서버 임시저장
        if self.path == '/api/draft':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            payload = json.loads(body.decode('utf-8'))

            user_name = payload.get('user_name', 'user')
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
                user_name=payload.get('user_name', 'user'),
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

        # /api/category-locks - 자격시험 종목 잠금/해제 설정
        if self.path == '/api/category-locks':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            payload = json.loads(body.decode('utf-8'))

            category = payload.get('category', '').strip()
            is_locked = bool(payload.get('is_locked', True))
            if category:
                DB.set_category_lock(category, is_locked)

            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "ok",
                "category": category,
                "is_locked": is_locked,
                "locked_categories": DB.get_locked_categories()
            }, ensure_ascii=False).encode('utf-8'))
            return

        # /api/schedules - 신규 시험 일정 등록
        if self.path == '/api/schedules':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            payload = json.loads(body.decode('utf-8'))

            new_id = DB.save_schedule(payload)
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "id": new_id}, ensure_ascii=False).encode('utf-8'))
            return

        # /api/schedules/update - 시험 일정 수정
        if self.path == '/api/schedules/update':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            payload = json.loads(body.decode('utf-8'))

            schedule_id = int(payload.get('id', 0))
            success = DB.update_schedule(schedule_id, payload)
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "success": success}, ensure_ascii=False).encode('utf-8'))
            return

        # /api/schedules/target - 대표 목표 시험 설정/토글
        if self.path == '/api/schedules/target':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            payload = json.loads(body.decode('utf-8'))

            schedule_id = int(payload.get('id', 0))
            success = DB.set_target_schedule(schedule_id)
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "success": success}, ensure_ascii=False).encode('utf-8'))
            return

        self.send_error(404, "Not Found")

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path_only = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # /api/draft - 임시저장 삭제
        if path_only == '/api/draft':
            user_name = query.get('user_name', ['user'])[0]
            deleted_cnt = DB.delete_draft(user_name)
            if user_name == 'user':
                DB.delete_draft('응시자')

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

        # /api/schedules - 시험 일정 삭제 (?id=X)
        if path_only == '/api/schedules':
            if 'id' in query:
                schedule_id = int(query['id'][0])
                deleted_cnt = DB.delete_schedule(schedule_id)
                self.send_response(200)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "deleted_count": deleted_cnt}, ensure_ascii=False).encode('utf-8'))
                return
            else:
                self.send_error(400, "Bad Request: Missing 'id' parameter")
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
    print(f"🚀 [개발4팀 풀어봄 (Pool-eobom) CBT Server] 구동 성공! (DB 연동 완료)")
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
