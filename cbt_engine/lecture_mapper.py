# -*- coding: utf-8 -*-
"""
[개발4팀 CBT 엔진] 감리사 기출문제-정규강의(244강) 자동 매핑 및 추천 유틸리티
"""
import sys
import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LECTURES_FILE = BASE_DIR / "auditor_lectures.json"


class AuditorLectureMapper:
    def __init__(self, json_path: Path = LECTURES_FILE):
        if not json_path.exists():
            raise FileNotFoundError(f"강의 데이터베이스를 찾을 수 없습니다: {json_path}")
        with open(json_path, "r", encoding="utf-8") as f:
            self.lectures = json.load(f)
            
        # Subject alias map
        self.subject_aliases = {
            "1": "제1과목", "1과목": "제1과목", "감리": "제1과목", "사업관리": "제1과목",
            "2": "제2과목", "2과목": "제2과목", "소공": "제2과목", "소프트웨어공학": "제2과목",
            "3": "제3과목", "3과목": "제3과목", "db": "제3과목", "데이터베이스": "제3과목",
            "4": "제4과목", "4과목": "제4과목", "시스템구조": "제4과목", "구조": "제4과목", "네트워크": "제4과목",
            "5": "제5과목", "5과목": "제5과목", "보안": "제5과목", "시스템보안": "제5과목"
        }

    def get_by_round(self, round_no: int):
        for lec in self.lectures:
            if lec["round"] == round_no:
                return lec
        return None

    def search(self, query: str, subject: str = None, top_k: int = 3):
        """
        주어진 쿼리(키워드 또는 문제 본문)를 바탕으로 가장 연관성이 높은 강의를 순위별로 반환
        """
        if not query or not query.strip():
            return []

        # Parse query keywords
        raw_words = re.findall(r'[a-zA-Z0-9가-힣]+', query.lower())
        stopwords = {
            "다음", "설명", "대한", "것은", "가장", "옳은", "틀린", "모두", "고른",
            "어떤", "위한", "대해", "경우", "해당하는", "아닌", "따른", "기준",
            "문제", "보기", "정답", "해설", "1번", "2번", "3번", "4번", "ㄱ", "ㄴ", "ㄷ", "ㄹ"
        }
        query_words = [w for w in raw_words if len(w) >= 2 and w not in stopwords]

        target_subject = None
        if subject:
            subj_clean = str(subject).strip().lower()
            target_subject = self.subject_aliases.get(subj_clean, subj_clean)

        results = []
        for lec in self.lectures:
            # Filter by subject if specified
            if target_subject and lec["official_subject_code"] != target_subject:
                continue

            score = 0.0
            lec_text = (lec["full_title"] + " " + " ".join(lec["keywords"])).lower()

            # Exact query in lecture title
            clean_query = query.strip().lower()
            if len(clean_query) >= 2 and clean_query in lec_text:
                score += 15.0

            # Match words
            for qw in query_words:
                if qw in lec_text:
                    # Higher weight if word is in title vs keywords
                    if qw in lec["lecture_title"].lower():
                        score += 5.0
                    else:
                        score += 2.0

            if score > 0:
                results.append((score, lec))

        results.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in results[:top_k]]

    def format_badge(self, round_no: int) -> str:
        """차시 번호로 단일 뱃지 텍스트 반환"""
        lec = self.get_by_round(round_no)
        if not lec:
            return f"🎬 [연계 추천 강의] {round_no}차시"
        return f"🎬 [연계 추천 강의] {lec['display_badge']}"

    def recommend(self, query: str, subject: str = None, top_k: int = 1) -> str:
        """질의어에 대한 뱃지 마크다운 반환"""
        matches = self.search(query, subject=subject, top_k=top_k)
        if not matches:
            return ""
        badges = [f"🎬 **[연계 추천 강의]** {m['display_badge']}" for m in matches]
        return "\n".join(badges)


def main():
    if len(sys.argv) < 2:
        print("사용법:")
        print("  python3 lecture_mapper.py <검색어>")
        print("  python3 lecture_mapper.py --round <차시번호>")
        print("  python3 lecture_mapper.py --subject <과목> <검색어>")
        return

    mapper = AuditorLectureMapper()

    if sys.argv[1] == "--round" and len(sys.argv) >= 3:
        round_no = int(sys.argv[2])
        lec = mapper.get_by_round(round_no)
        if lec:
            print(f"[{lec['official_subject_code']} - {lec['sub_area']}] {lec['display_badge']}")
            print(f"핵심 키워드: {', '.join(lec['keywords'])}")
        else:
            print(f"{round_no}차시 강의를 찾을 수 없습니다.")
        return

    subject = None
    query_args = sys.argv[1:]
    if sys.argv[1] == "--subject" and len(sys.argv) >= 4:
        subject = sys.argv[2]
        query_args = sys.argv[3:]

    query = " ".join(query_args)
    matches = mapper.search(query, subject=subject, top_k=3)
    if not matches:
        print(f"'{query}'에 대한 추천 강의를 찾지 못했습니다.")
    else:
        print(f"🔍 '{query}' 추천 강의 검색 결과:")
        for idx, m in enumerate(matches, 1):
            print(f"  {idx}. [{m['official_subject_code']}] {m['display_badge']}")


if __name__ == "__main__":
    main()
