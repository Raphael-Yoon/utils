"""
[개발4팀 전사 공통 모듈] 감리사 과목별 묶음 전개년(12개년, 2015-2026) 확장 조정기
기존 auditor_subject_{s}_5years.json의 2022~2026년 보강 해설을 100% 보존하면서,
2021~2015년 기출 데이터를 최신순으로 완벽 결합하여 12개년 전수 과목별 마스터 세트 구축
"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
EXAMS_DIR = BASE_DIR / "exams"

SUBJECT_NAMES = {
    1: ("감리 및 사업관리", 25),
    2: ("소프트웨어공학", 25),
    3: ("데이터베이스", 25),
    4: ("시스템구조", 25),
    5: ("보안", 20),
}

# 12개년 최신순 정렬
ALL_YEARS = list(range(2026, 2014, -1)) # 2026 down to 2015

def update_subject_bundle(sid):
    sname, q_per_year = SUBJECT_NAMES[sid]
    total_qs_target = q_per_year * len(ALL_YEARS) # 300 or 240
    bundle_file = EXAMS_DIR / f"auditor_subject_{sid}_5years.json"
    
    print(f"\n[*] {sid}과목 ({sname}) 12개년 전수 묶음 생성 시작 (목표: {total_qs_target}문항)...")
    
    # 1. 기존 5개년 파일에서 2022~2026 데이터 로드 (보강 해설 100% 보존)
    existing_qs_by_year = {}
    if bundle_file.exists():
        old_data = json.loads(bundle_file.read_text(encoding="utf-8"))
        for q in old_data.get("questions", []):
            yr = q.get("origin_year")
            if yr:
                existing_qs_by_year.setdefault(yr, []).append(q)
                
    # 2. 2026 -> 2015 역순으로 전체 연도별 문항 수집
    combined_questions = []
    subjects_meta = []
    
    curr_q_id = 1
    for idx, yr in enumerate(ALL_YEARS, start=1):
        start_q = curr_q_id
        
        # 2022~2026은 기존 5개년 보강본 우선 사용
        if yr in existing_qs_by_year and len(existing_qs_by_year[yr]) == q_per_year:
            year_qs = existing_qs_by_year[yr]
        else:
            # 연도별 단일 과목 파일에서 로드
            sub_file = EXAMS_DIR / f"auditor_{yr}_subject{sid}.json"
            if not sub_file.exists():
                raise FileNotFoundError(f"과목 파일 누락: {sub_file.name}")
            sub_data = json.loads(sub_file.read_text(encoding="utf-8"))
            year_qs = sub_data.get("questions", [])
            
        if len(year_qs) != q_per_year:
            raise ValueError(f"[{yr}년 {sid}과목] 문항수 불일치: {len(year_qs)} != {q_per_year}")
            
        for orig_idx, q in enumerate(year_qs, start=1):
            q_copy = dict(q)
            q_copy["id"] = curr_q_id
            q_copy["subject_id"] = idx
            q_copy["subject"] = sname
            q_copy["origin_year"] = yr
            if "origin_id" not in q_copy:
                q_copy["origin_id"] = orig_idx
            combined_questions.append(q_copy)
            curr_q_id += 1
            
        end_q = curr_q_id - 1
        subjects_meta.append({
            "id": idx,
            "name": f"{yr}년 기출 ({q_per_year}문항)",
            "start_q": start_q,
            "end_q": end_q,
            "question_count": q_per_year,
            "weight_per_q": 4.0 if q_per_year == 25 else 5.0
        })

    # 3. 전체 번들 데이터 구성
    bundle_data = {
        "exam_info": {
            "id": f"auditor_sub{sid}_all",
            "title": f"[12개년 전수] {sid}과목 : {sname} ({total_qs_target}문항)",
            "category": "정보시스템감리사",
            "year": 2026,
            "time_limit_minutes": total_qs_target,
            "passing_rules": {
                "total_questions": total_qs_target,
                "cutline_score": 60.0,
                "fail_score_per_subject": 40.0,
                "points_per_question": round(100.0 / total_qs_target, 2)
            }
        },
        "subjects": subjects_meta,
        "questions": combined_questions
    }

    bundle_file.write_text(json.dumps(bundle_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[성공] {bundle_file.name} 12개년 전수 ({total_qs_target}문항) 갱신 완료!")

def main():
    for sid in range(1, 6):
        update_subject_bundle(sid)
    print("\n[개발4팀] 감리사 1~5과목 전체 12개년 전수 묶음 조정 전원 완료!")

if __name__ == "__main__":
    main()
