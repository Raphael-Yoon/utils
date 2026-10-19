"""
[개발4팀 전사 공통 모듈] 2019년 제20회 정보시스템감리사 CBT 기출문제 변환 및 등록기
PDF 2단 칼럼 레이아웃의 인위적 줄바꿈(엔터) 제거 및 단락·코드·리스트 정규화,
다이어그램/표 고해상도 이미지 크롭 추출, 복수 정답(Q66 [2, 4]) 완벽 지원 및 1~5과목 분할 생성
"""
import json
import re
from pathlib import Path
import pymupdf

BASE_DIR = Path(__file__).resolve().parent
PDF_PATH = BASE_DIR / "Adds" / "2019년(제20회)정보시스템 감리사 필기시험 문제 및 답안.pdf"
EXAMS_DIR = BASE_DIR / "exams"
IMAGES_DIR = EXAMS_DIR / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

SUBJECT_NAMES = {
    1: "1과목 : 감리 및 사업관리",
    2: "2과목 : 소프트웨어공학",
    3: "3과목 : 데이터베이스",
    4: "4과목 : 시스템구조",
    5: "5과목 : 보안",
}

# PDF 칼럼 줄바꿈으로 인해 쪼개진 한글 단어 보정 맵
SPLIT_WORDS = [
    ('프로', '젝트', '프로젝트'),
    ('프로', '젝트(PROJECT)', '프로젝트(PROJECT)'),
    ('방', '법', '방법'),
    ('동기', '부여', '동기부여'),
    ('설명으', '로', '설명으로'),
    ('설', '명으로', '설명으로'),
    ('설명', '으로', '설명으로'),
    ('것', '은?', '것은?'),
    ('상', '당한', '상당한'),
    ('계', '약', '계약'),
    ('경', '우', '경우'),
    ('소', '프트웨어', '소프트웨어'),
    ('소프트', '웨어', '소프트웨어'),
    ('다이어', '그램', '다이어그램'),
    ('다이어그', '램에', '다이어그램에'),
    ('바람', '직한', '바람직한'),
    ('카디널', '리티', '카디널리티'),
    ('네트', '워크', '네트워크'),
    ('과', '정을', '과정을'),
    ('이', '해하여', '이해하여'),
    ('하', '고', '하고'),
    ('들', '어갈', '들어갈'),
    ('적', '용할', '적용할'),
    ('속', '성명', '속성명'),
    ('거부', '될', '거부될'),
    ('구', '문을', '구문을'),
    ('소', '요되는', '소요되는'),
    ('사용', '하는', '사용하는'),
    ('사용', '하며,', '사용하며,'),
    ('사', '용하며,', '사용하며,'),
    ('학', '과', '학과'),
    ('검색하', '라', '검색하라'),
    ('작', '성할', '작성할'),
    ('표', '시한다', '표시한다'),
    ('사', '용하여', '사용하여'),
    ('실행', '결과', '실행결과'),
    ('동', '시에', '동시에'),
    ('소속부', '서', '소속부서'),
    ('나', '타내고', '나타내고'),
    ('일관', '성을', '일관성을'),
    ('일관', '성(consistency)을', '일관성(consistency)을'),
    ('옳', '지', '옳지'),
    ('검사시', '점', '검사시점'),
    ('공', '통', '공통'),
    ('사용', '하여', '사용하여'),
    ('사', '실로부터', '사실로부터'),
    ('통', '합한', '통합한'),
    ('머신', '의', '머신의'),
    ('사용', '되는', '사용되는'),
    ('서비', '스', '서비스'),
    ('머', '신러닝', '머신러닝'),
    ('포함', '된', '포함된'),
    ('금액', '을', '금액을'),
    ('끝', '수를', '끝수를'),
    ('트랜', '잭션', '트랜잭션'),
    ('아키', '텍처', '아키텍처'),
    ('릴레', '이션', '릴레이션'),
    ('데이터', '베이스', '데이터베이스'),
    ('데이터베이', '스', '데이터베이스'),
    ('정규', '화', '정규화'),
    ('가상', '화', '가상화'),
    ('스토', '리지', '스토리지'),
    ('인터', '페이스', '인터페이스'),
    ('시스', '템을', '시스템을'),
    ('시', '스템을', '시스템을'),
    ('테', '이블의', '테이블의'),
    ('외', '래키', '외래키'),
    ('충', '돌을', '충돌을'),
    ('해', '결', '해결'),
    ('바', '르게', '바르게'),
    ('다', '음과', '다음과'),
    ('논', '문제목(title)과', '논문제목(title)과'),
    ('서', '버', '서버'),
    ('라', '운드', '라운드'),
    ('지', '났을', '지났을'),
    ('프로', '그램에서', '프로그램에서'),
    ('평균', '적으로', '평균적으로'),
    ('식별', '자', '식별자'),
    ('않', '고', '않고'),
    ('데', '이터', '데이터'),
    ('온', '톨로지', '온톨로지'),
    ('가', '장', '가장'),
    ('수', '준의', '수준의'),
    ('서', '명의', '서명의'),
    ('기', '업이나', '기업이나'),
    ('프로토', '콜을', '프로토콜을'),
    ('방', '지에', '방지에'),
    ('예방하', '기', '예방하기'),
    ('기', '법에', '기법에'),
    ('기', '법', '기법'),
    ('공', '격대상의', '공격대상의'),
    ('위', '조된', '위조된'),
    ('성공', '을', '성공을'),
    ('변', '경이', '변경이'),
    ('모', '드는', '모드는'),
    ('있', '는', '있는'),
    ('있', '다.', '있다.'),
    ('효율', '성', '효율성'),
    ('위', '탁한', '위탁한'),
    ('사', '항에', '사항에'),
    ('개', '발한다고', '개발한다고'),
    ('속성과', '의', '속성과의'),
    ('클래스', '에', '클래스에'),
    ('표', '준,', '표준,'),
    ('메소', '드', '메소드'),
    ('프', '로토콜이', '프로토콜이'),
    ('참', '조하는', '참조하는')
]

def clean_question_body(raw_text):
    lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
    if not lines:
        return ''
        
    header_lines = []
    block_lines = []
    in_block = False
    
    for i, line in enumerate(lines):
        is_block_start = (
            any(line.startswith(m) for m in [
                '가.', '나.', '다.', '라.', '마.', '바.', '사.',
                'ㄱ.', 'ㄴ.', 'ㄷ.', 'ㄹ.', 'ㅁ.',
                '1)', '2)', '3)', '4)',
                'Ÿ', '-', '•', '※', '[', '<',
                'void ', 'int ', 'char ', 'public ', 'class ', 'interface ', '#if', 'SELECT ', 'TID ', 'DocID ', 'R(', 'S('
            ])
            or (in_block)
            or (i > 0 and header_lines and header_lines[-1].endswith(('?', ':', '것은?')))
        )
        if is_block_start:
            in_block = True
            block_lines.append(line)
        else:
            header_lines.append(line)
            
    header_text = ' '.join(header_lines)
    for p1, p2, target in SPLIT_WORDS:
        header_text = header_text.replace(f'{p1} {p2}', target)
        
    if not block_lines:
        return header_text
        
    formatted_block = []
    curr_item = []
    
    for line in block_lines:
        is_new_item = any(line.startswith(m) for m in [
            '가.', '나.', '다.', '라.', '마.', '바.', '사.',
            'ㄱ.', 'ㄴ.', 'ㄷ.', 'ㄹ.', 'ㅁ.',
            '1)', '2)', '3)', '4)',
            'Ÿ', '-', '•', '※', '[', '<'
        ])
        is_code = any(line.startswith(m) for m in [
            'void ', 'int ', 'char ', 'public ', 'class ', 'interface ', '#if', '#else', '#endif',
            'printf', 'scanf', 'SELECT ', 'FROM ', 'WHERE ', 'CREATE ', 'TID ', 'DocID ', '{', '}', '...', '//'
        ])
        
        if is_code:
            if curr_item:
                formatted_block.append(' '.join(curr_item))
                curr_item = []
            formatted_block.append(line)
        elif is_new_item:
            if curr_item:
                formatted_block.append(' '.join(curr_item))
                curr_item = []
            curr_item.append(line)
        else:
            if curr_item:
                curr_item.append(line)
            else:
                curr_item.append(line)
                
    if curr_item:
        formatted_block.append(' '.join(curr_item))
        
    cleaned_blocks = []
    for blk in formatted_block:
        b_clean = blk
        for p1, p2, target in SPLIT_WORDS:
            b_clean = b_clean.replace(f'{p1} {p2}', target)
        cleaned_blocks.append(b_clean)
        
    return header_text + '\n\n' + '\n'.join(cleaned_blocks)

def clean_option_text(text):
    t = text.strip()
    for p1, p2, target in SPLIT_WORDS:
        t = t.replace(f'{p1} {p2}', target)
    return t

def get_subject_id(q_id):
    if q_id <= 25: return 1
    elif q_id <= 50: return 2
    elif q_id <= 75: return 3
    elif q_id <= 100: return 4
    else: return 5

def convert():
    doc = pymupdf.open(PDF_PATH)
    
    columns = []
    for pno in range(1, len(doc)):
        page = doc[pno]
        stream = b''.join([doc.xref_stream(x) for x in page.get_contents()]).decode('latin1', errors='ignore')
        matches = re.findall(r'2\s+Tr.*?([\d\.]+)\s+([\d\.]+)\s+Tm', stream, re.DOTALL)
        bold_pts = [(float(m[0]) * 0.119935, float(m[1]) * 0.119869) for m in matches]

        # 2019년 페이지 폭은 595.0pt (A4 규격) -> 분할 기준 x=298
        for side, clip in [('L', pymupdf.Rect(20, 30, 298, 820)), ('R', pymupdf.Rect(298, 30, 580, 820))]:
            words = page.get_text('words', clip=clip)
            words_sorted = sorted(words, key=lambda w: (round(w[1]/6)*6, w[0]))
            lines = []
            curr_y = None
            curr_line = []
            curr_line_words = []
            for w in words_sorted:
                y_group = round(w[1]/6)*6
                if curr_y is None or abs(y_group - curr_y) > 3:
                    if curr_line: lines.append((curr_y, ' '.join(curr_line), curr_line_words))
                    curr_line = [w[4]]
                    curr_line_words = [w]
                    curr_y = y_group
                else:
                    curr_line.append(w[4])
                    curr_line_words.append(w)
            if curr_line: lines.append((curr_y, ' '.join(curr_line), curr_line_words))
            columns.append((pno+1, side, clip, lines, bold_pts, page))

    headers = []
    expected_q = 1
    for col_idx, (pno, side, clip, lines, bold_pts, page) in enumerate(columns):
        for l_idx, (y, l_text, l_words) in enumerate(lines):
            m = re.match(r'^(\d{1,3})\.(?!\d)', l_text)
            if m and int(m.group(1)) == expected_q:
                headers.append((expected_q, col_idx, l_idx, y))
                expected_q += 1

    # 다이어그램 및 표 이미지 크롭 정의 (2019년 문항별 고해상도)
    CROP_BOXES = {
        29: (355.0, 125.0, 500.0, 400.0),    # 클래스 다이어그램
        30: (310.0, 540.0, 545.0, 745.0),    # 유스케이스 다이어그램
        31: (45.0, 170.0, 290.0, 715.0),     # 상태전이 테스트 다이어그램
        39: (305.0, 375.0, 560.0, 530.0),    # 외부 품질 속성 다이어그램
        40: (305.0, 655.0, 550.0, 745.0),    # 개발 팀 속도 표
        42: (50.0, 435.0, 295.0, 600.0),     # 책임연쇄 다이어그램
        44: (335.0, 550.0, 550.0, 705.0),    # 인터페이스 다이어그램 (가)~(라)
        61: (135.0, 170.0, 215.0, 255.0),    # 수퍼타입/서브타입 다이어그램
        63: (50.0, 675.0, 290.0, 735.0),     # ER 다이어그램 (직원-프로젝트)
        72: (305.0, 465.0, 550.0, 575.0),    # B-트리 다이어그램
        73: (65.0, 125.0, 280.0, 335.0),     # 시퀀스 데이터베이스 표
    }

    for q_num, bbox in CROP_BOXES.items():
        h = [h for h in headers if h[0] == q_num][0]
        col_idx = h[1]
        page = columns[col_idx][5]
        u = pymupdf.Rect(*bbox)
        pix = page.get_pixmap(clip=u, dpi=150)
        img_file = IMAGES_DIR / f"auditor_2019_q{q_num}.png"
        pix.save(img_file)

    parsed_questions = []
    for i, (q, col_idx, l_idx, y) in enumerate(headers):
        pno, side, clip, lines, bold_pts, page = columns[col_idx]
        end_l_idx = headers[i+1][2] if (i < len(headers)-1 and headers[i+1][1] == col_idx) else len(lines)
        q_lines = lines[l_idx:end_l_idx]
        
        first_opt_idx = [idx for idx, (ly, lt, lw) in enumerate(q_lines) if '①' in lt][0]
        q_text_lines = [lt for ly, lt, lw in q_lines[:first_opt_idx]]
        q_text_lines[0] = re.sub(r'^\d{1,3}\.\s*', '', q_text_lines[0])
        raw_q_body = '\n'.join(q_text_lines).strip()
        
        cleaned_body = clean_question_body(raw_q_body)
        
        opt_words = [w for ly, lt, lw in q_lines[first_opt_idx:] for w in lw]
        syms = ['①', '②', '③', '④']
        sym_positions = {}
        for widx, w in enumerate(opt_words):
            for s in syms:
                if w[4].startswith(s) and s not in sym_positions:
                    sym_positions[s] = (widx, w)
                    
        sorted_syms = sorted(sym_positions.keys(), key=lambda s: sym_positions[s][0])
        options_text = []
        sym_scores = {'①': 0, '②': 0, '③': 0, '④': 0}
        
        for s_idx, s in enumerate(sorted_syms):
            start_widx, sw = sym_positions[s]
            if s_idx < len(sorted_syms) - 1:
                next_s = sorted_syms[s_idx + 1]
                next_sw = sym_positions[next_s][1]
                end_widx = sym_positions[next_s][0]
                same_line = abs(next_sw[1] - sw[1]) < 8
                if same_line:
                    bx0 = sw[0] - 1
                    bx1 = next_sw[0] - 1
                    by0 = sw[1] - 3
                    by1 = sw[3] + 4
                else:
                    bx0 = clip.x0
                    bx1 = clip.x1
                    by0 = sw[1] - 3
                    by1 = next_sw[1] - 1
            else:
                next_sw = None
                end_widx = len(opt_words)
                bx0 = sw[0] - 1
                bx1 = clip.x1
                by0 = sw[1] - 3
                by1 = opt_words[-1][3] + 4
                
            words_in_opt = opt_words[start_widx:end_widx]
            text_in_opt = ' '.join(w[4] for w in words_in_opt)
            if not text_in_opt.startswith(s):
                text_in_opt = f"{s} {text_in_opt}"
            options_text.append(clean_option_text(text_in_opt))
            
            for bp in bold_pts:
                if by0 <= bp[1] <= by1 and bx0 <= bp[0] <= bx1:
                    sym_scores[s] += 1
                    
        # Q66 복수 정답 처리 (문제 지문: '외래키 역할을 수행하는 속성으로 옳은 것을 모두 고르시오. (2개 선택)' -> ② C, ④ E)
        if q == 66:
            ans_val = [2, 4]
            explanation = "정답: ②, ④ (복수 정답)\n\n[출처]\n2019년 제20회 정보시스템감리사 필기시험\n\n[기본 해설]\n문제 조건(2개 선택)에 따라 BCNF 분해 시 외래키 역할을 수행하는 속성은 ②번(C)과 ④번(E)입니다."
        else:
            best_sym = max(sym_scores.keys(), key=lambda s: sym_scores[s])
            ans_val = {'①': 1, '②': 2, '③': 3, '④': 4}[best_sym]
            circle_symbols = {1: '①', 2: '②', 3: '③', 4: '④'}
            explanation = f"정답: {circle_symbols[ans_val]}\n\n[출처]\n2019년 제20회 정보시스템감리사 필기시험\n\n[기본 해설]\n정답은 {circle_symbols[ans_val]}번입니다."
            
        subj_id = get_subject_id(q)
        
        image_url = None
        if q in CROP_BOXES:
            image_url = f"/exams/images/auditor_2019_q{q}.png"
            
        q_obj = {
            "id": q,
            "subject_id": subj_id,
            "question": cleaned_body,
            "options": options_text,
            "answer": ans_val,
            "explanation": explanation
        }
        if image_url:
            q_obj["image_url"] = image_url
            q_obj["image"] = image_url
            
        parsed_questions.append(q_obj)

    # Full 120 questions
    full_data = {
        "exam_info": {
            "id": "auditor_2019",
            "title": "2019년 정보시스템감리사 기출문제",
            "category": "정보시스템감리사",
            "year": 2019,
            "time_limit_minutes": 120,
            "passing_rules": {
                "total_pass_score": 80,
                "subject_cutoff_score": 40,
                "points_per_question": 4.0
            }
        },
        "subjects": [
            {"id": 1, "name": "1과목 : 감리 및 사업관리", "start_q": 1, "end_q": 25, "weight_per_q": 4.0, "question_count": 25},
            {"id": 2, "name": "2과목 : 소프트웨어공학", "start_q": 26, "end_q": 50, "weight_per_q": 4.0, "question_count": 25},
            {"id": 3, "name": "3과목 : 데이터베이스", "start_q": 51, "end_q": 75, "weight_per_q": 4.0, "question_count": 25},
            {"id": 4, "name": "4과목 : 시스템구조", "start_q": 76, "end_q": 100, "weight_per_q": 4.0, "question_count": 25},
            {"id": 5, "name": "5과목 : 보안", "start_q": 101, "end_q": 120, "weight_per_q": 4.0, "question_count": 20}
        ],
        "questions": parsed_questions
    }
    
    full_path = EXAMS_DIR / "auditor_2019.json"
    full_path.write_text(json.dumps(full_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[성공] {full_path.name} 저장 완료 (120문항)")

    # 5 subject files
    for s_id in range(1, 6):
        subj_name = SUBJECT_NAMES[s_id]
        subj_qs = [q for q in parsed_questions if q["subject_id"] == s_id]
        cnt = len(subj_qs)
        
        subj_qs_formatted = []
        for idx, q_item in enumerate(subj_qs, start=1):
            item_copy = dict(q_item)
            item_copy["id"] = idx
            item_copy["subject_id"] = 1
            item_copy["subject"] = subj_name.split(" : ")[1]
            item_copy["origin_year"] = 2019
            item_copy["origin_id"] = q_item["id"]
            subj_qs_formatted.append(item_copy)
            
        subj_data = {
            "exam_info": {
                "id": f"auditor_2019_sub{s_id}",
                "title": f"[2019년] {s_id}과목 : {subj_name.split(' : ')[1]} ({cnt}문항)",
                "category": "정보시스템감리사",
                "year": 2019,
                "time_limit_minutes": cnt,
                "passing_rules": {
                    "total_questions": cnt,
                    "cutline_score": 60.0,
                    "fail_score_per_subject": 40.0,
                    "points_per_question": 4.0
                }
            },
            "subjects": [
                {
                    "id": 1,
                    "name": f"2019년 {s_id}과목 : {subj_name.split(' : ')[1]} ({cnt}문항)",
                    "start_q": 1,
                    "end_q": cnt,
                    "question_count": cnt,
                    "weight_per_q": 4.0
                }
            ],
            "questions": subj_qs_formatted
        }
        
        subj_file = EXAMS_DIR / f"auditor_2019_subject{s_id}.json"
        subj_file.write_text(json.dumps(subj_data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[성공] {subj_file.name} 저장 완료 ({cnt}문항)")

if __name__ == "__main__":
    convert()
