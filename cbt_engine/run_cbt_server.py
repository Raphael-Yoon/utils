"""
[개발4팀 전사 공통 모듈] CBT 모의고사 전용 HTTP 서버 및 러너 (Run CBT Server)
기능: utils/cbt_engine/exams/ 폴더의 모든 시험 데이터를 자동 탐색하여 제공합니다. (한글 URL 인코딩 완벽 지원)
"""

import sys
import json
import urllib.parse
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

BASE_DIR = Path(__file__).parent
EXAMS_DIR = BASE_DIR / "exams"

class CBTRequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        # /api/exams 요청 시 exams/ 폴더 내 전체 시험 파일 목록 반환
        if self.path == '/api/exams':
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
                            "path": f"/exams/{json_file.name}"
                        })
                    except Exception:
                        pass
            
            self.wfile.write(json.dumps(exam_list, ensure_ascii=False).encode('utf-8'))
            return

        super().do_GET()

    def translate_path(self, path):
        # URL 디코딩 처리 (한글 파일명 %EB%B9%85... 인코딩 해제)
        decoded_path = urllib.parse.unquote(path)
        rel_path = decoded_path.lstrip('/')
        if not rel_path:
            rel_path = 'index.html'
        
        target = BASE_DIR / rel_path
        return str(target)

def run(port=8080):
    server_address = ('', port)
    httpd = HTTPServer(server_address, CBTRequestHandler)
    url = f"http://localhost:{port}"
    print(f"==================================================")
    print(f"🚀 [개발4팀 CBT Engine Server] 구동 성공! (한글 지원)")
    print(f"📁 시험 데이터 폴더: {EXAMS_DIR}")
    print(f"🌐 접속 주소: {url}")
    print(f"==================================================")
    
    try:
        webbrowser.open(url)
    except Exception:
        pass

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nCBT 서버를 종료합니다.")

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run(port)
