"""
[개발4팀 전사 공통 모듈] CBT 파서 및 변환기 (CBT Converter)
기능: Markdown 형태의 기출문제 및 정답표 문서를 읽어 utils/cbt_engine/exams/ 하위에 표준 JSON 생성.
"""

import sys
import json
import re
from pathlib import Path

class CBTConverter:
    def __init__(self, exam_title="필기 기출문제", category="자격증", time_limit=120, subjects=None, passing_rules=None):
        self.exam_title = exam_title
        self.category = category
        self.time_limit = time_limit
        self.subjects = subjects or [
            { "id": 1, "name": "1과목 : 빅데이터 분석 기획", "question_count": 20 },
            { "id": 2, "name": "2과목 : 빅데이터 탐색", "question_count": 20 },
            { "id": 3, "name": "3과목 : 빅데이터 모델링", "question_count": 20 },
            { "id": 4, "name": "4과목 : 빅데이터 결과 해석", "question_count": 20 }
        ]
        self.passing_rules = passing_rules or {
            "total_pass_score": 60,
            "subject_cutoff_score": 10,
            "points_per_question": 1.25
        }

    def convert(self, md_path: Path, answer_path: Path, output_json_path: Path):
        md_path = Path(md_path)
        answer_path = Path(answer_path)
        output_json_path = Path(output_json_path)

        answers = {}
        if answer_path.exists():
            ans_content = answer_path.read_text(encoding="utf-8")
            matches = re.findall(r'\*\*\s*(\d+)\s*\*\*\s*\|\s*([①②③④1234])', ans_content)
            symbol_map = {'①': 1, '②': 2, '③': 3, '④': 4, '1': 1, '2': 2, '3': 3, '4': 4}
            for q_num, ans in matches:
                answers[int(q_num)] = symbol_map.get(ans.strip(), 1)

        md_content = md_path.read_text(encoding="utf-8")
        questions = []
        
        q_blocks = re.split(r'\n(?=###\s*\d+\.)', md_content)
        for block in q_blocks:
            m = re.search(r'###\s*(\d+)\.\s*(.*?)(?=\n\s*[-*]?\s*[①②③④]|\Z)', block, re.DOTALL)
            if not m:
                continue

            q_id = int(m.group(1))

            # 문항 번호 기준 과목 ID 할당 (1-20: 1과목, 21-40: 2과목, 41-60: 3과목, 61-80: 4과목)
            if q_id <= 20:
                current_subject_id = 1
            elif q_id <= 40:
                current_subject_id = 2
            elif q_id <= 60:
                current_subject_id = 3
            else:
                current_subject_id = 4

            q_text = m.group(2).strip()

            opt_text = block[m.end():]
            options = [re.sub(r'^\s*[-*]\s*', '', opt.strip()) for opt in re.findall(r'[-*]?\s*[①②③④]\s*.*', opt_text)]

            clean_options = []
            for opt in options:
                for item in re.split(r'(?=[①②③④])', opt):
                    if item.strip():
                        clean_options.append(re.sub(r'^\s*[-*]\s*', '', item.strip()))
            
            if len(clean_options) > 4:
                clean_options = clean_options[:4]

            img_m = re.search(r'!\[.*?\]\((.*?)\)', block)
            image_url = img_m.group(1) if img_m else None

            q_obj = {
                "id": q_id,
                "subject_id": current_subject_id,
                "question": q_text,
                "options": clean_options,
                "answer": answers.get(q_id, 1),
                "explanation": f"{self.exam_title} {q_id}번 문항입니다."
            }
            if image_url:
                q_obj["image_url"] = image_url

            questions.append(q_obj)

        cbt_data = {
            "exam_info": {
                "title": self.exam_title,
                "category": self.category,
                "time_limit_minutes": self.time_limit,
                "passing_rules": self.passing_rules
            },
            "subjects": self.subjects,
            "questions": questions
        }

        output_json_path.parent.mkdir(parents=True, exist_ok=True)
        output_json_path.write_text(json.dumps(cbt_data, ensure_ascii=False, indent=2), encoding="utf-8")
        return len(questions)

if __name__ == "__main__":
    base_src = Path(__file__).resolve().parent.parent.parent / "writer" / "빅데이터분석기사"
    target_dir = Path(__file__).resolve().parent / "exams"
    
    rounds = [sys.argv[1]] if len(sys.argv) > 1 else [str(r) for r in range(3, 11)]
    
    for round_num in rounds:
        converter = CBTConverter(f"빅데이터분석기사 제{round_num}회 필기 기출문제", "빅데이터분석기사")
        target_file = target_dir / f"bigdata_{round_num.zfill(2)}.json"
        
        md_file = base_src / f"{round_num}회_기출문제.md"
        ans_file = base_src / f"{round_num}회_정답표.md"
        
        if md_file.exists():
            cnt = converter.convert(md_file, ans_file, target_file)
            print(f"[cbt_converter] 제{round_num}회 {cnt}문항 변환 완료 -> {target_file}")
        else:
            print(f"[cbt_converter] 경고: {md_file} 파일이 존재하지 않습니다.")
