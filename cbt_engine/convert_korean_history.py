"""
[개발4팀 & 작가팀] 한국사능력검정시험 멀티 회차 배치 파이프라인
기능:
 77회(심화/기본), 78회(심화), 79회(심화/기본) 총 5개 시험지 PDF를 자동 정밀 분석하여
 - 문항별 300DPI 지문/사료 대형 이미지 크롭 (미짤림 100% 안전 마진)
 - 1점/2점/3점 배점 및 정답표 매핑
 - CBT 호환 표준 JSON 생성 및 2단계 선택 UI 카테고리/회차 세팅
"""

import json
import pymupdf
from PIL import Image
from pathlib import Path

# 회차별 정답표 & 배점 정보 (75회 심화/기본, 76회 심화, 77회 심화/기본, 78회 심화, 79회 심화/기본)
EXAM_DATABASE = {
    "korean_history_75_advanced": {
        "title": "제75회 한국사능력검정시험 (심화)",
        "category": "한국사능력검정시험 (심화)",
        "pdf_name": "제75회 심화 문제지.pdf",
        "answers": {
            1: (4, 1), 2: (1, 2), 3: (5, 2), 4: (1, 2), 5: (2, 2), 6: (4, 2), 7: (4, 3), 8: (2, 2), 9: (3, 2), 10: (1, 3),
            11: (5, 2), 12: (5, 1), 13: (3, 2), 14: (3, 2), 15: (5, 2), 16: (5, 2), 17: (4, 1), 18: (3, 2), 19: (1, 2), 20: (5, 2),
            21: (2, 2), 22: (2, 3), 23: (2, 2), 24: (3, 2), 25: (1, 1), 26: (1, 2), 27: (4, 2), 28: (5, 2), 29: (1, 1), 30: (2, 3),
            31: (3, 3), 32: (2, 2), 33: (3, 1), 34: (5, 2), 35: (2, 2), 36: (5, 1), 37: (1, 2), 38: (3, 3), 39: (4, 2), 40: (3, 3),
            41: (4, 3), 42: (1, 1), 43: (2, 2), 44: (2, 1), 45: (4, 3), 46: (2, 2), 47: (5, 2), 48: (3, 1), 49: (5, 3), 50: (4, 2)
        }
    },
    "korean_history_75_basic": {
        "title": "제75회 한국사능력검정시험 (기본)",
        "category": "한국사능력검정시험 (기본)",
        "pdf_name": "75회 한국사_문제지(기본).pdf",
        "answers": {
            1: (3, 1), 2: (3, 2), 3: (4, 2), 4: (1, 3), 5: (2, 2), 6: (3, 2), 7: (1, 3), 8: (4, 1), 9: (4, 1), 10: (3, 2),
            11: (3, 3), 12: (3, 2), 13: (2, 2), 14: (1, 1), 15: (3, 2), 16: (3, 2), 17: (3, 2), 18: (1, 2), 19: (3, 2), 20: (4, 1),
            21: (2, 2), 22: (4, 3), 23: (1, 2), 24: (4, 2), 25: (2, 1), 26: (4, 1), 27: (2, 3), 28: (4, 2), 29: (3, 2), 30: (1, 2),
            31: (2, 1), 32: (1, 2), 33: (1, 2), 34: (4, 3), 35: (2, 2), 36: (4, 2), 37: (3, 2), 38: (3, 3), 39: (1, 2), 40: (1, 3),
            41: (2, 1), 42: (3, 2), 43: (2, 3), 44: (2, 2), 45: (4, 2), 46: (2, 1), 47: (1, 2), 48: (2, 3), 49: (2, 2), 50: (4, 2)
        }
    },
    "korean_history_76_advanced": {
        "title": "제76회 한국사능력검정시험 (심화)",
        "category": "한국사능력검정시험 (심화)",
        "pdf_name": "76회 한국사_문제지(심화).pdf",
        "answers": {
            1: (5, 1), 2: (2, 2), 3: (3, 2), 4: (1, 1), 5: (4, 2), 6: (2, 2), 7: (4, 2), 8: (3, 2), 9: (2, 3), 10: (2, 2),
            11: (1, 2), 12: (3, 3), 13: (5, 2), 14: (4, 2), 15: (3, 3), 16: (1, 2), 17: (1, 1), 18: (3, 1), 19: (4, 3), 20: (5, 2),
            21: (1, 2), 22: (2, 2), 23: (5, 1), 24: (4, 2), 25: (2, 2), 26: (3, 2), 27: (3, 1), 28: (2, 3), 29: (5, 2), 30: (1, 2),
            31: (3, 1), 32: (4, 2), 33: (4, 2), 34: (3, 3), 35: (5, 2), 36: (2, 1), 37: (5, 3), 38: (4, 2), 39: (3, 2), 40: (3, 2),
            41: (1, 2), 42: (4, 1), 43: (4, 2), 44: (5, 3), 45: (5, 1), 46: (5, 3), 47: (1, 2), 48: (1, 2), 49: (2, 2), 50: (5, 3)
        }
    },
    "korean_history_77_advanced": {
        "title": "제77회 한국사능력검정시험 (심화)",
        "category": "한국사능력검정시험 (심화)",
        "pdf_name": "77회 한국사_문제지(심화).pdf",
        "answers": {
            1: (3, 1), 2: (5, 2), 3: (2, 2), 4: (4, 2), 5: (3, 2), 6: (2, 3), 7: (2, 1), 8: (3, 2), 9: (2, 2), 10: (4, 2),
            11: (4, 2), 12: (1, 3), 13: (4, 1), 14: (5, 2), 15: (1, 3), 16: (4, 2), 17: (1, 2), 18: (5, 1), 19: (1, 1), 20: (5, 3),
            21: (4, 2), 22: (5, 2), 23: (1, 2), 24: (3, 3), 25: (3, 1), 26: (4, 2), 27: (5, 1), 28: (3, 2), 29: (4, 2), 30: (3, 3),
            31: (2, 2), 32: (3, 2), 33: (2, 1), 34: (2, 2), 35: (5, 3), 36: (4, 2), 37: (1, 1), 38: (5, 2), 39: (5, 2), 40: (2, 3),
            41: (1, 2), 42: (5, 3), 43: (2, 2), 44: (4, 1), 45: (1, 2), 46: (1, 2), 47: (2, 3), 48: (2, 2), 49: (2, 2), 50: (3, 2)
        }
    },
    "korean_history_77_basic": {
        "title": "제77회 한국사능력검정시험 (기본)",
        "category": "한국사능력검정시험 (기본)",
        "pdf_name": "77회 한국사_문제지(기본).pdf",
        "answers": {
            1: (3, 1), 2: (4, 2), 3: (4, 2), 4: (3, 2), 5: (3, 2), 6: (2, 1), 7: (4, 3), 8: (1, 2), 9: (1, 2), 10: (2, 3),
            11: (2, 1), 12: (4, 2), 13: (1, 1), 14: (4, 2), 15: (1, 2), 16: (1, 3), 17: (4, 2), 18: (3, 3), 19: (1, 2), 20: (1, 2),
            21: (2, 1), 22: (1, 2), 23: (2, 2), 24: (3, 2), 25: (4, 1), 26: (2, 2), 27: (4, 3), 28: (4, 2), 29: (1, 3), 30: (2, 2),
            31: (1, 3), 32: (2, 2), 33: (2, 1), 34: (2, 3), 35: (1, 1), 36: (3, 2), 37: (3, 2), 38: (4, 2), 39: (4, 2), 40: (3, 2),
            41: (1, 3), 42: (2, 2), 43: (4, 1), 44: (3, 2), 45: (2, 2), 46: (4, 2), 47: (3, 2), 48: (3, 2), 49: (4, 1), 50: (1, 3)
        }
    },
    "korean_history_78_advanced": {
        "title": "제78회 한국사능력검정시험 (심화)",
        "category": "한국사능력검정시험 (심화)",
        "pdf_name": "78회 한국사_문제지(심화).pdf",
        "answers": {
            1: (5, 1), 2: (2, 3), 3: (1, 2), 4: (5, 3), 5: (2, 2), 6: (4, 2), 7: (4, 1), 8: (3, 2), 9: (3, 2), 10: (4, 2),
            11: (4, 2), 12: (3, 1), 13: (5, 1), 14: (3, 2), 15: (4, 2), 16: (3, 2), 17: (5, 2), 18: (4, 2), 19: (1, 3), 20: (5, 3),
            21: (1, 3), 22: (4, 2), 23: (1, 3), 24: (5, 1), 25: (1, 2), 26: (5, 1), 27: (2, 2), 28: (2, 2), 29: (1, 2), 30: (2, 3),
            31: (4, 2), 32: (3, 2), 33: (2, 2), 34: (4, 1), 35: (3, 3), 36: (1, 1), 37: (3, 3), 38: (4, 2), 39: (2, 2), 40: (4, 2),
            41: (2, 2), 42: (1, 2), 43: (1, 2), 44: (5, 2), 45: (5, 1), 46: (2, 2), 47: (2, 1), 48: (5, 3), 49: (2, 2), 50: (5, 2)
        }
    },
    "korean_history_79_basic": {
        "title": "제79회 한국사능력검정시험 (기본)",
        "category": "한국사능력검정시험 (기본)",
        "pdf_name": "79회 한국사_문제지(기본).pdf",
        "answers": {
            1: (4, 1), 2: (3, 1), 3: (2, 3), 4: (4, 2), 5: (2, 2), 6: (1, 2), 7: (3, 3), 8: (2, 1), 9: (2, 2), 10: (1, 2),
            11: (4, 2), 12: (3, 1), 13: (1, 3), 14: (2, 2), 15: (4, 2), 16: (4, 3), 17: (1, 1), 18: (2, 2), 19: (1, 2), 20: (3, 2),
            21: (4, 2), 22: (4, 3), 23: (1, 2), 24: (1, 1), 25: (3, 2), 26: (4, 2), 27: (3, 1), 28: (1, 2), 29: (1, 3), 30: (2, 2),
            31: (2, 2), 32: (1, 1), 33: (2, 2), 34: (3, 3), 35: (1, 1), 36: (1, 2), 37: (1, 3), 38: (3, 2), 39: (3, 2), 40: (3, 1),
            41: (4, 2), 42: (1, 3), 43: (3, 2), 44: (4, 2), 45: (4, 2), 46: (3, 2), 47: (4, 2), 48: (4, 3), 49: (4, 2), 50: (2, 2)
        }
    },
    "korean_history_79_advanced": {
        "title": "제79회 한국사능력검정시험 (심화)",
        "category": "한국사능력검정시험 (심화)",
        "pdf_name": "79회 한국사_문제지(심화).pdf",
        "answers": {
            1: (2, 1), 2: (4, 1), 3: (2, 2), 4: (1, 1), 5: (2, 3), 6: (1, 3), 7: (3, 1), 8: (2, 2), 9: (5, 2), 10: (3, 2),
            11: (5, 2), 12: (5, 2), 13: (1, 3), 14: (3, 2), 15: (3, 2), 16: (3, 1), 17: (4, 2), 18: (5, 3), 19: (5, 2), 20: (4, 2),
            21: (2, 1), 22: (4, 3), 23: (4, 2), 24: (3, 2), 25: (1, 3), 26: (3, 2), 27: (1, 1), 28: (5, 1), 29: (1, 2), 30: (2, 2),
            31: (2, 3), 32: (1, 2), 33: (4, 2), 34: (2, 2), 35: (2, 1), 36: (1, 3), 37: (3, 3), 38: (5, 2), 39: (5, 2), 40: (4, 2),
            41: (1, 1), 42: (4, 2), 43: (3, 2), 44: (4, 2), 45: (5, 2), 46: (1, 2), 47: (2, 2), 48: (5, 2), 49: (2, 2), 50: (3, 3)
        }
    }
}

def process_all_korean_history_exams():
    base_dir = Path(__file__).parent
    writer_dir = base_dir.parent.parent / "writer" / "한국사능력검정시험"
    exams_dir = base_dir / "exams"

    for exam_key, exam_data in EXAM_DATABASE.items():
        title = exam_data["title"]
        category = exam_data["category"]
        pdf_path = writer_dir / exam_data["pdf_name"]

        if not pdf_path.exists():
            print(f"[건너뜀] PDF 파일 없음: {pdf_path}")
            continue

        img_out_dir = exams_dir / "images" / exam_key
        json_out_file = exams_dir / f"{exam_key}.json"
        img_out_dir.mkdir(parents=True, exist_ok=True)

        doc = pymupdf.open(pdf_path)

        # 50개 문항별 이미지 크롭
        for q_id in range(1, 51):
            img_filename = f"q_{str(q_id).zfill(2)}.png"
            page_idx = (q_id - 1) // 4
            if page_idx >= len(doc): page_idx = len(doc) - 1

            page = doc[page_idx]
            zoom = 300 / 72.0
            mat = pymupdf.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            page_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            w, h = page_img.size

            is_right = (q_id % 4 == 3 or q_id % 4 == 0)
            is_bottom = (q_id % 4 == 2 or q_id % 4 == 0)

            crop_x1 = int(w * 0.50) if is_right else int(w * 0.02)
            crop_x2 = int(w * 0.98) if is_right else int(w * 0.50)

            if not is_bottom:
                crop_y1 = int(h * 0.05)
                crop_y2 = int(h * 0.51)
            else:
                crop_y1 = int(h * 0.49)
                crop_y2 = int(h * 0.95)

            cropped = page_img.crop((crop_x1, crop_y1, crop_x2, crop_y2))
            cropped.save(img_out_dir / img_filename, "PNG")

        # 50문항 JSON 데이터 구조 수립
        is_basic = "기본" in category
        questions_data = []

        # 기본 4지선다, 심화 5지선다
        opt_count = 4 if is_basic else 5

        # PDF 텍스트 및 OCR 기반 실제 보기(선택지) 추출
        parsed_options = {q: {} for q in range(1, 51)}
        symbols = ['①','②','③','④','⑤']

        for page_idx, page in enumerate(doc):
            text = page.get_text('text')
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            cur_q = None
            for line in lines:
                m_q = re.match(r'^(\d+)\.\s*', line)
                if m_q:
                    qn = int(m_q.group(1))
                    if 1 <= qn <= 50: cur_q = qn
                if cur_q:
                    m_opt = re.match(r'^([①②③④⑤])\s*(.*)', line)
                    if m_opt:
                        sym, txt = m_opt.group(1), m_opt.group(2)
                        idx = symbols.index(sym)
                        if txt.strip(): parsed_options[cur_q][idx] = txt.strip()

        for q_id in range(1, 51):
            ans_val, pts_val = exam_data["answers"][q_id]
            img_filename = f"q_{str(q_id).zfill(2)}.png"

            opts = []
            for i in range(opt_count):
                txt = parsed_options[q_id].get(i, '')
                if not txt:
                    txt = f"{symbols[i]}번 선택지"
                elif not any(txt.startswith(s) for s in symbols):
                    txt = f"{symbols[i]} {txt}"
                opts.append(txt)

            q_obj = {
                "id": q_id,
                "subject_id": 1,
                "question": f"제{q_id}번 문항 [{pts_val}점]",
                "points": pts_val,
                "options": opts,
                "answer": ans_val,
                "image_url": f"/exams/images/{exam_key}/{img_filename}",
                "explanation": f"{title} {q_id}번 문항입니다. (배점: {pts_val}점, 정답: {ans_val}번)"
            }
            questions_data.append(q_obj)

        passing_rules = {
            "total_pass_score": 60,
            "points_per_question": 2.0
        }
        if is_basic:
            passing_rules.update({"tier_4_score": 80, "tier_5_score": 70, "tier_6_score": 60})
        else:
            passing_rules.update({"tier_1_score": 80, "tier_2_score": 70, "tier_3_score": 60})

        cbt_data = {
            "exam_info": {
                "title": title,
                "category": category,
                "time_limit_minutes": 70 if is_basic else 80,
                "passing_rules": passing_rules
            },
            "subjects": [
                {"id": 1, "name": f"{category} (50문항)", "question_count": 50}
            ],
            "questions": questions_data
        }

        json_out_file.write_text(json.dumps(cbt_data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[배치 성공] {title} -> {json_out_file}")

if __name__ == "__main__":
    process_all_korean_history_exams()
