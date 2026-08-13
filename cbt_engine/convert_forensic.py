"""
[개발4팀 전사 공통 모듈] 디지털포렌식 모의고사 일괄 변환기 (Batch Digital Forensic Converter)
기능: writer/디지털포렌식/ 폴더 내 모든 모의고사 md 문서(1회, 2회, 3회 등)를 읽어
      utils/cbt_engine/exams/ 하위에 표준 JSON 데이터 생성.
"""

import json
import re
from pathlib import Path

def convert_all_forensic_exams():
    base_dir = Path(__file__).parent
    writer_dir = base_dir.parent.parent / "writer" / "디지털포렌식"
    out_dir = base_dir / "exams"

    if not writer_dir.exists():
        print(f"[오류] 원본 폴더를 찾을 수 없습니다: {writer_dir}")
        return

    md_files = [
        ("digital-forensic-mock-exam-100.md", "digital_forensic_mock_01.json", "디지털포렌식 전문가 2급 필기 모의고사 [제1회]"),
        ("digital-forensic-mock-exam-2nd.md", "digital_forensic_mock_02.json", "디지털포렌식 전문가 2급 필기 모의고사 [제2회]"),
        ("digital-forensic-mock-exam-3rd.md", "digital_forensic_mock_03.json", "디지털포렌식 전문가 2급 필기 모의고사 [제3회]"),
        ("digital-forensic-mock-exam-4th.md", "digital_forensic_mock_04.json", "디지털포렌식 전문가 2급 필기 모의고사 [제4회]"),
        ("digital-forensic-mock-exam-5th.md", "digital_forensic_mock_05.json", "디지털포렌식 전문가 2급 필기 모의고사 [제5회]")
    ]

    subjects = [
        {"id": 1, "name": "제1과목: 컴퓨터 구조와 디지털 저장매체", "question_count": 15},
        {"id": 2, "name": "제2과목: 파일시스템과 운영체제", "question_count": 15},
        {"id": 3, "name": "제3과목: 응용프로그램과 네트워크의 이해", "question_count": 15},
        {"id": 4, "name": "제4과목: 데이터베이스", "question_count": 15},
        {"id": 5, "name": "제5과목: 디지털포렌식 개론 (기초실무 & 법률이론)", "question_count": 40}
    ]

    passing_rules = {
        "total_pass_score": 60,
        "subject_cutoff_score": 40,
        "points_per_question": 1.0
    }

    symbol_map = {'①': 1, '②': 2, '③': 3, '④': 4}

    for src_filename, target_filename, title in md_files:
        src_path = writer_dir / src_filename
        if not src_path.exists():
            print(f"[건너뜀] 파일 없음: {src_path}")
            continue

        content = src_path.read_text(encoding="utf-8")

        # [문제 편]과 [정답 및 상세 해설 편]으로 분리되어 있는 경우
        if "## [문제 편]" in content and "## [정답 및 상세 해설 편]" in content:
            parts = content.split("## [정답 및 상세 해설 편]")
            prob_part = parts[0]
            ans_part = parts[1]

            # 정답 및 해설 사전 구축 (q_id -> {answer, explanation})
            ans_dict = {}
            ans_blocks = re.split(r'\n(?=###\s*Q\d+\.)', ans_part)
            for ablock in ans_blocks:
                am = re.search(r'###\s*Q(\d+)\.', ablock)
                if not am:
                    continue
                aq_id = int(am.group(1))
                a_match = re.search(r'\*\s*\*\*정답:\s*([①②③④1234])\*\*', ablock)
                ans_val = 1
                if a_match:
                    ans_str = a_match.group(1).strip()
                    if ans_str in symbol_map:
                        ans_val = symbol_map[ans_str]
                    elif ans_str.isdigit():
                        ans_val = int(ans_str)
                exp_match = re.search(r'\*\s*\*\*해설:\*\*\s*(.*?)(?=\n---|(?:\n###\s*Q\d+)|\Z)', ablock, re.DOTALL)
                exp_val = exp_match.group(1).strip() if exp_match else ""
                ans_dict[aq_id] = {"answer": ans_val, "explanation": exp_val}

            # 문제 추출
            q_blocks = re.split(r'\n(?=###\s*Q\d+\.)', prob_part)
            questions = []
            for block in q_blocks:
                m = re.search(r'###\s*Q(\d+)\.\s*(.*?)(?=\n\*제|\n①|\Z)', block, re.DOTALL)
                if not m:
                    continue
                q_id = int(m.group(1))
                q_text = m.group(2).strip()

                if q_id <= 15: subj_id = 1
                elif q_id <= 30: subj_id = 2
                elif q_id <= 45: subj_id = 3
                elif q_id <= 60: subj_id = 4
                else: subj_id = 5

                options = []
                for i in range(1, 5):
                    curr_sym = ['①', '②', '③', '④'][i-1]
                    m_opt = re.search(rf'{curr_sym}\s*(.*?)(?=\n[①②③④]|\n---|\n\n|\Z)', block, re.DOTALL)
                    if m_opt:
                        opt_val = m_opt.group(1).strip()
                        opt_val = re.sub(r'</?[bB]>', '', opt_val).strip()
                        options.append(opt_val)
                    else:
                        options.append("")

                ans_info = ans_dict.get(q_id, {"answer": 1, "explanation": f"{title} Q{q_id}번 해설입니다."})

                questions.append({
                    "id": q_id,
                    "subject_id": subj_id,
                    "question": q_text,
                    "options": options,
                    "answer": ans_info["answer"],
                    "explanation": ans_info["explanation"]
                })
        else:
            # 기존 통통형 포맷 (1회~3회)
            q_blocks = re.split(r'\n(?=###\s*\*\*Q\d+\.|\n\*\*Q\d+\.|\n###\s*Q\d+\.)', content)
            questions = []
            for block in q_blocks:
                m = re.search(r'(?:###\s*)?\*\*?Q(\d+)\.\s*(.*?)(?:\*\*|\n)', block, re.DOTALL)
                if not m:
                    continue

                q_id = int(m.group(1))
                q_text = m.group(2).strip().rstrip('*').strip()

                if q_id <= 15: subj_id = 1
                elif q_id <= 30: subj_id = 2
                elif q_id <= 45: subj_id = 3
                elif q_id <= 60: subj_id = 4
                else: subj_id = 5

                options = []
                for i in range(1, 5):
                    curr_sym = ['①', '②', '③', '④'][i-1]
                    next_sym_pattern = r'|'.join([r'①', r'②', r'③', r'④'][i:]) if i < 4 else r'\*'
                    m_opt = re.search(rf'{curr_sym}\s*(.*?)(?=\n\s*(?:{next_sym_pattern})|\n\s*\*|\Z)', block, re.DOTALL)
                    if m_opt:
                        opt_val = m_opt.group(1).strip()
                        opt_val = re.sub(r'</?[bB]>', '', opt_val).strip()
                        options.append(opt_val)
                    else:
                        options.append("")

                ans_m = re.search(r'\*\s*\*\*정답:\s*([①②③④1234])\*\*', block)
                answer = 1
                if ans_m:
                    ans_str = ans_m.group(1).strip()
                    if ans_str in symbol_map:
                        answer = symbol_map[ans_str]
                    elif ans_str.isdigit():
                        answer = int(ans_str)

                exp_m = re.search(r'\*\s*\*\*해설:\*\*\s*(.*?)(?=\n\n|\Z)', block, re.DOTALL)
                explanation = exp_m.group(1).strip() if exp_m else f"{title} Q{q_id}번 해설입니다."

                questions.append({
                    "id": q_id,
                    "subject_id": subj_id,
                    "question": q_text,
                    "options": options,
                    "answer": answer,
                    "explanation": explanation
                })

        cbt_data = {
            "exam_info": {
                "title": title,
                "category": "디지털포렌식 전문가 2급",
                "time_limit_minutes": 120,
                "passing_rules": passing_rules
            },
            "subjects": subjects,
            "questions": questions
        }

        out_file = out_dir / target_filename
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(json.dumps(cbt_data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[성공] {title} ({len(questions)}문항) 변환 완료 -> {out_file}")

if __name__ == "__main__":
    convert_all_forensic_exams()
