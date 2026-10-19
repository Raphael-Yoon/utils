"""
[개발4팀 전사 공통 모듈] 2015-2018 정보시스템감리사 CBT 기출문제 일괄 변환 및 등록기
- 4개년(2015, 2016, 2017, 2018) 총 480문항 전수 변환
- 2단 칼럼 레이아웃, 크로스 칼럼/페이지 수집 완벽 지원
- 딩뱃 원문자(➀➁➂➃) 정규화
- 다이어그램/표 고해상도(DPI 150) 자동 크롭 및 이미지 URL 연동
- 볼드 스트로크(2 Tr) 기반 정답 추출 및 복수정답/공식 확정 답안 완벽 반영
- 전체 120문항 JSON 및 1~5과목 분할 JSON 일괄 생성
"""

import json
import re
from pathlib import Path
import pymupdf

BASE_DIR = Path(__file__).resolve().parent
ADDS_DIR = BASE_DIR / "Adds"
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

# 연도별 정답 오버라이드 및 복수 정답 맵
ANSWER_OVERRIDES = {
    2015: {
        25: 4,
        85: [1, 2],       # (2개 선택)
        113: [1, 3],      # (2개 선택)
    },
    2016: {
        1: [1, 2, 3, 4],  # 전항 정답
        91: [1, 4],       # 복수 정답
    },
    2017: {
        50: 2,
        61: [3, 4],       # (2개 선택)
        100: 4,
    },
    2018: {
        4: 1,
        11: 1,
        12: 1,
        16: 4,
        117: 1,
    }
}

YEAR_CONFIGS = {
    2015: {
        "file": "2015년(제16회) 정보시스템 감리사 필기시험 문제 및 답안.pdf",
        "scale_x": 0.119914, "scale_y": 0.119912,
        "rects": [('L', pymupdf.Rect(30, 40, 364, 980)), ('R', pymupdf.Rect(364, 40, 700, 980))]
    },
    2016: {
        "file": "2016년(제17회) 정보시스템 감리사 필기시험 문제 및 답안.pdf",
        "scale_x": 0.119935, "scale_y": 0.119869,
        "rects": [('L', pymupdf.Rect(20, 30, 298, 820)), ('R', pymupdf.Rect(298, 30, 580, 820))]
    },
    2017: {
        "file": "2017년(제18회) 정보시스템 감리사 필기시험 문제 및 답안.pdf",
        "scale_x": 0.119935, "scale_y": 0.119869,
        "rects": [('L', pymupdf.Rect(20, 30, 298, 820)), ('R', pymupdf.Rect(298, 30, 580, 820))]
    },
    2018: {
        "file": "2018년(제19회)정보시스템 감리사 필기시험 문제 및 답안.pdf",
        "scale_x": 0.119935, "scale_y": 0.119869,
        "rects": [('L', pymupdf.Rect(20, 30, 298, 820)), ('R', pymupdf.Rect(298, 30, 580, 820))]
    }
}

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
                'void ', 'int ', 'char ', 'public ', 'class ', 'interface ', '#if', 'SELECT ', 'FROM ', 'WHERE ', 'TID ', 'DocID ', 'R(', 'S('
            ])
            or (in_block)
            or (i > 0 and header_lines and header_lines[-1].endswith(('?', ':', '것은?', '옳은가?')))
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

def convert_single_year(year):
    cfg = YEAR_CONFIGS[year]
    pdf_path = ADDS_DIR / cfg["file"]
    doc = pymupdf.open(pdf_path)
    print(f"\n==========================================")
    print(f"[*] {year}년 감리사 기출문제 변환 시작: {cfg['file']}")
    print(f"==========================================")
    
    # 1. 2단 칼럼 레이아웃 파싱
    columns = []
    for pno in range(1, len(doc)):
        page = doc[pno]
        stream = b''.join([doc.xref_stream(x) for x in page.get_contents()]).decode('latin1', errors='ignore')
        matches = re.findall(r'2\s+Tr.*?([\d\.]+)\s+([\d\.]+)\s+Tm', stream, re.DOTALL)
        bold_pts = [(float(m[0]) * cfg["scale_x"], float(m[1]) * cfg["scale_y"]) for m in matches]
        
        for side, clip in cfg["rects"]:
            words = page.get_text('words', clip=clip)
            # 딩뱃 원문자 정규화: ➀➁➂➃ -> ①②③④
            norm_words = []
            for w in words:
                text_clean = w[4].replace('➀', '①').replace('➁', '②').replace('➂', '③').replace('➃', '④')
                norm_words.append((w[0], w[1], w[2], w[3], text_clean, w[5], w[6], w[7]))
                
            words_sorted = sorted(norm_words, key=lambda wrd: (round(wrd[1]/6)*6, wrd[0]))
            lines = []
            curr_y = None
            curr_line = []
            curr_line_words = []
            for wrd in words_sorted:
                y_group = round(wrd[1]/6)*6
                if curr_y is None or abs(y_group - curr_y) > 3:
                    if curr_line: lines.append((curr_y, ' '.join(curr_line), curr_line_words))
                    curr_line = [wrd[4]]
                    curr_line_words = [wrd]
                    curr_y = y_group
                else:
                    curr_line.append(wrd[4])
                    curr_line_words.append(wrd)
            if curr_line: lines.append((curr_y, ' '.join(curr_line), curr_line_words))
            columns.append((pno+1, side, clip, lines, bold_pts, page))
            
    # 2. 문제 헤더 식별 (1~120)
    headers = []
    expected_q = 1
    for col_idx, (pno, side, clip, lines, bold_pts, page) in enumerate(columns):
        for l_idx, (y, l_text, l_words) in enumerate(lines):
            m = re.match(r'^(\d{1,3})\.(?!\d)', l_text)
            if m and int(m.group(1)) == expected_q:
                headers.append((expected_q, col_idx, l_idx, y))
                expected_q += 1

    if len(headers) != 120:
        raise ValueError(f"[{year}] 감리사 헤더 개수 불일치: {len(headers)}개 인식됨 (필요: 120개)")

    # 3. 이미지 자동 추출 (get_image_rects 활용)
    image_map = {}
    for i, (q, col_idx, l_idx, y) in enumerate(headers):
        curr_c = col_idx
        next_c = headers[i+1][1] if i < len(headers)-1 else len(columns)-1
        
        # 문항이 걸친 페이지 범위 확인
        pno_start = columns[curr_c][0] - 1
        pno_end = columns[next_c][0] - 1
        
        q_y_start = y
        q_y_end = headers[i+1][3] if (curr_c == next_c and i < len(headers)-1) else 9999.0
        
        for pno_i in range(pno_start, pno_end + 1):
            page_obj = doc[pno_i]
            img_list = page_obj.get_images()
            for img_info in img_list:
                xref = img_info[0]
                rects = page_obj.get_image_rects(xref)
                for r in rects:
                    # 해당 칼럼 및 문항 y영역 내에 있는지 판별
                    c_clip = columns[curr_c][2]
                    if (c_clip.x0 - 20 <= r.x0 and r.x1 <= c_clip.x1 + 30) or (pno_start != pno_end):
                        if (pno_i == pno_start and r.y0 >= q_y_start - 10) or (pno_i > pno_start):
                            if (pno_i == pno_end and r.y1 <= q_y_end + 10) or (pno_i < pno_end):
                                # 이미지 크롭 저장
                                pix = page_obj.get_pixmap(clip=r, dpi=150)
                                img_filename = f"auditor_{year}_q{q}.png"
                                img_path = IMAGES_DIR / img_filename
                                pix.save(img_path)
                                image_map[q] = f"/exams/images/{img_filename}"
                                break

    # 4. 문항 및 보기, 정답 파싱
    parsed_questions = []
    circle_symbols = {1: '①', 2: '②', 3: '③', 4: '④'}
    
    for i, (q, col_idx, l_idx, y) in enumerate(headers):
        curr_c = col_idx
        next_c = headers[i+1][1] if i < len(headers)-1 else len(columns)-1
        
        q_lines = []
        all_col_bold_pts = []
        for c in range(curr_c, next_c + 1):
            c_pno, c_side, c_clip, c_lines, c_bold, c_page = columns[c]
            start_l = l_idx if c == curr_c else 0
            end_l = headers[i+1][2] if (c == next_c and i < len(headers)-1) else len(c_lines)
            for ly, lt, lw in c_lines[start_l:end_l]:
                q_lines.append((c, c_clip, ly, lt, lw))
            all_col_bold_pts.extend([(c, bp) for bp in c_bold])
            
        first_opt_idx = [idx for idx, (c, clip, ly, lt, lw) in enumerate(q_lines) if '①' in lt][0]
        q_text_lines = [lt for c, clip, ly, lt, lw in q_lines[:first_opt_idx]]
        q_text_lines[0] = re.sub(r'^\d{1,3}\.\s*', '', q_text_lines[0])
        raw_q_body = '\n'.join(q_text_lines).strip()
        cleaned_body = clean_question_body(raw_q_body)
        
        opt_words = [(c, clip, w) for c, clip, ly, lt, lw in q_lines[first_opt_idx:] for w in lw]
        syms = ['①', '②', '③', '④']
        sym_positions = {}
        for widx, (c, clip, w) in enumerate(opt_words):
            for s in syms:
                if w[4].startswith(s) and s not in sym_positions:
                    sym_positions[s] = (widx, c, clip, w)
                    
        sorted_syms = sorted(sym_positions.keys(), key=lambda s: sym_positions[s][0])
        options_text = []
        sym_scores = {'①': 0, '②': 0, '③': 0, '④': 0}
        
        for s_idx, s in enumerate(sorted_syms):
            start_widx, sc, sclip, sw = sym_positions[s]
            if s_idx < len(sorted_syms) - 1:
                next_s = sorted_syms[s_idx + 1]
                next_widx, next_sc, next_sclip, next_sw = sym_positions[next_s]
                end_widx = next_widx
                same_line = (sc == next_sc) and (abs(next_sw[1] - sw[1]) < 8)
                if same_line:
                    bx0 = sw[0] - 1
                    bx1 = next_sw[0] - 1
                    by0 = sw[1] - 3
                    by1 = sw[3] + 4
                else:
                    bx0 = sclip.x0
                    bx1 = sclip.x1
                    by0 = sw[1] - 3
                    by1 = next_sw[1] - 1 if sc == next_sc else sclip.y1
            else:
                next_sw = None
                end_widx = len(opt_words)
                bx0 = sw[0] - 1
                bx1 = sclip.x1
                by0 = sw[1] - 3
                by1 = opt_words[-1][2][3] + 4
                
            words_in_opt = [w[2] for w in opt_words[start_widx:end_widx]]
            text_in_opt = ' '.join(w[4] for w in words_in_opt)
            if not text_in_opt.startswith(s):
                text_in_opt = f"{s} {text_in_opt}"
            options_text.append(clean_option_text(text_in_opt))
            
            for c_id, bp in all_col_bold_pts:
                if c_id == sc and (by0 <= bp[1] <= by1) and (bx0 <= bp[0] <= bx1):
                    sym_scores[s] += 1
                    
        # 정답 판별 (오버라이드 맵 우선 적용)
        if q in ANSWER_OVERRIDES.get(year, {}):
            ans_val = ANSWER_OVERRIDES[year][q]
        else:
            best_sym = max(sym_scores.keys(), key=lambda s: sym_scores[s])
            ans_val = {'①': 1, '②': 2, '③': 3, '④': 4}[best_sym]
            
        subj_id = get_subject_id(q)
        image_url = image_map.get(q)
        
        # 해설 텍스트 구성
        if isinstance(ans_val, list):
            ans_str = ', '.join(circle_symbols[x] for x in ans_val)
            explanation = f"정답: {ans_str} (복수 정답)\n\n[출처]\n{year}년 정보시스템감리사 필기시험\n\n[기본 해설]\n해당 문항의 정답은 {ans_str}입니다."
        else:
            ans_str = circle_symbols[ans_val]
            explanation = f"정답: {ans_str}\n\n[출처]\n{year}년 정보시스템감리사 필기시험\n\n[기본 해설]\n정답은 {ans_str}번입니다."
            
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

    # 5. 전체 120문항 JSON 저장
    full_data = {
        "exam_info": {
            "id": f"auditor_{year}",
            "title": f"{year}년 정보시스템감리사 기출문제",
            "category": "정보시스템감리사",
            "year": year,
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
    
    full_path = EXAMS_DIR / f"auditor_{year}.json"
    full_path.write_text(json.dumps(full_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[성공] {full_path.name} 저장 완료 (120문항)")

    # 6. 과목별 5개 분할 JSON 저장
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
            item_copy["origin_year"] = year
            item_copy["origin_id"] = q_item["id"]
            subj_qs_formatted.append(item_copy)
            
        subj_data = {
            "exam_info": {
                "id": f"auditor_{year}_sub{s_id}",
                "title": f"[{year}년] {s_id}과목 : {subj_name.split(' : ')[1]} ({cnt}문항)",
                "category": "정보시스템감리사",
                "year": year,
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
                    "name": f"{year}년 {s_id}과목 : {subj_name.split(' : ')[1]} ({cnt}문항)",
                    "start_q": 1,
                    "end_q": cnt,
                    "question_count": cnt,
                    "weight_per_q": 4.0
                }
            ],
            "questions": subj_qs_formatted
        }
        
        subj_file = EXAMS_DIR / f"auditor_{year}_subject{s_id}.json"
        subj_file.write_text(json.dumps(subj_data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[성공] {subj_file.name} 저장 완료 ({cnt}문항)")

def main():
    years = [2015, 2016, 2017, 2018]
    for y in years:
        convert_single_year(y)
    print("\n[개발4팀] 2015-2018 4개년 감리사 기출문제 일괄 변환 및 등록 전원 완료!")

if __name__ == "__main__":
    main()
