# -*- coding: utf-8 -*-
"""
[개발4팀 CBT 엔진] 빅데이터분석기사 기출문제 해설(Explanation) 자동 보강/고도화 스크립트
"""
import os
import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent
EXAMS_DIR = BASE_DIR / "exams"

# 과목별 주요 키워드 및 개념 데이터베이스
CONCEPT_DB = {
    # 1과목 : 빅데이터 분석 기획
    "3V": "빅데이터의 전통적 3V 특징은 규모(Volume), 속도(Velocity), 다양성(Variety)입니다. 가치(Value)나 정확성(Veracity)은 이후 4V, 5V로 확장된 개념입니다.",
    "소프트 스킬": "하드 스킬(Hard Skill)은 수학, 통계학, 머신러닝 알고리즘 등 데이터 분석 기술을 의미하며, 소프트 스킬(Soft Skill)은 통찰력 있는 분석, 설득력 있는 전달, 다분야 간 협력 및 소통 능력을 의미합니다.",
    "성숙도": "분석 성숙도 모델 단계: 도입(도구·시스템 구축, 일부 전문가 의존) -> 활용(분석 결과를 업무에 적용) -> 확산(전사 차원 분석 체계 확립) -> 최적화(분석이 핵심 역량으로 정착).",
    "과제 도출": "분석 대상(What)과 분석 방법(How)에 따른 과제 도출 방식:\n- What O, How O : Optimization (최적화)\n- What O, How X : Solution (솔루션)\n- What X, How O : Insight (통찰)\n- What X, How X : Discovery (발견)",
    "준지도": "수집된 데이터 중 일부에만 라벨(Label)이 있는 경우에는 지도학습과 비지도학습의 기법을 조합한 '준지도학습(Semi-supervised Learning)'을 적용합니다.",
    "개인정보": "유전적 특성, 인종, 사상, 신념 등 민감정보 및 생체인식정보는 개인정보보호법상 엄격히 보호되는 개인정보/민감정보에 해당합니다.",
    "우선순위": "분석 과제 우선순위 평가 기준:\n- 시급성(Urgency): 전략적 중요도, KPI 연계성\n- 난이도(Difficulty): 투자비용 요소(Cost), 기술적 난이도",
    "DIKW": "DIKW 피라미드 단계:\n- Data(데이터): 순수한 가공 전 사실\n- Information(정보): 의미가 부여된 데이터\n- Knowledge(지식): 개인의 경험과 상호 결합된 개인화된 정보\n- Wisdom(지혜): 근본적 원리에 대한 이해를 바탕으로 한 창의적 아이디어",
    "거버넌스": "분석 조직 구조 형태:\n- 집중형: 전사 분석 전담 조직이 전사 분석을 담당\n- 기능형: 별도 전담 조직 없이 각 현업 부서에서 분석 수행\n- 제독형(수건/선도): 전사 전담 조직과 현업 부서가 협력하여 핵심 과제 지원",

    # 2과목 : 빅데이터 탐색
    "결측치": "결측치(Missing Value) 처리 방법:\n- 완전 제거(Listwise Deletion): 결측이 있는 행 전체 삭제\n- 평균/중앙값 대체: 연속형 변수의 대표값으로 대체\n- 최빈값 대체: 범주형 변수의 대표값으로 대체\n- K-NN 대체: 유사한 이웃 관측치의 평균값 등으로 대체",
    "이상치": "이상치(Outlier) 탐지 기법:\n- IQR 기법: Q1 - 1.5*IQR 미만 또는 Q3 + 1.5*IQR 초과값 탐지\n- Z-Score 기법: 평균으로부터 표준편차의 +-3배 초과 탐지\n- Boxplot: 상자수염 그림을 통해 시각적으로 이상치 파악",
    "상관계수": "피어슨 상관계수(Pearson Correlation): 두 연속형 변수 간의 선형 상관관계를 측정 (-1 ~ +1). 스피어만 상관계수는 순위/서열 데이터에 사용.",
    "스케일링": "데이터 정규화/표준화:\n- Min-Max Scaler: (X - Min) / (Max - Min) -> 0과 1 사이로 변환\n- Standard Scaler: (X - Mean) / StdDev -> 평균 0, 표준편차 1로 변환",
    "차원축소": "PCA(주성분분석): 고차원 데이터를 분산이 가장 큰 축(주성분)으로 투영하여 데이터의 손실을 최소화하면서 차원을 축소하는 대표적 비지도학습 기법.",

    # 3과목 : 빅데이터 모델링
    "지도학습": "지도학습(Supervised Learning)은 입력(X)과 타깃 라벨(Y)이 모두 주어지는 학습 방법으로, 분류(Classification)와 회귀(Regression) 문제에 사용됩니다.",
    "비지도학습": "비지도학습(Unsupervised Learning)은 타깃 라벨(Y) 없이 데이터의 내재된 구조나 군집을 탐색하는 방법으로, 군집화(Clustering), 차원축소(PCA), 연관규칙 분석 등이 포함됩니다.",
    "과적합": "과적합(Overfitting) 해결 방안:\n- 드롭아웃(Dropout) 적용\n- L1/L2 규제(Regularization) 추가 (Lasso/Ridge)\n- 교차 검증(Cross Validation) 수행\n- 학습 데이터 추가 수집 및 모델 복잡도 축소",
    "의사결정나무": "의사결정나무(Decision Tree)의 분순도 지수:\n- 지니 지수(Gini Index): CART 알고리즘에서 사용\n- 엔트로피(Entropy)/정보 획득량(Information Gain): C4.5, ID3 알고리즘에서 사용",
    "앙상블": "앙상블(Ensemble) 학습 기법:\n- 배깅(Bagging): 복원 추출(Bootstrap) 후 독립적 모델 학습 (예: Random Forest)\n- 부스팅(Boosting): 이전 모델의 오차에 가중치를 주어 순차적 학습 (예: XGBoost, LightGBM, AdaBoost)\n- 보팅(Voting): 여러 알고리즘의 결과를 다수결 또는 평균으로 통합",
    "ROC": "ROC 곡선(Receiver Operating Characteristic Curve): 가로축은 FPR(1-특이도), 세로축은 TPR(민감도/재현율)로 그린 곡선. 곡선 하단 면적인 AUC(Area Under Curve)가 1에 가까울수록 뛰어난 모델.",

    # 4과목 : 빅데이터 결과 해석
    "혼동행렬": "혼동 행렬(Confusion Matrix) 평가 지표:\n- 정밀도(Precision) = TP / (TP + FP)\n- 재현율(Recall/Sensitivity) = TP / (TP + FN)\n- F1-Score = 2 * (Precision * Recall) / (Precision + Recall)\n- 정확도(Accuracy) = (TP + TN) / (TP + FP + FN + TN)",
    "군집 평가": "군집화(Clustering) 평가 지표:\n- 실루엣 계수(Silhouette Coefficient): -1 ~ +1 사이 값으로, 1에 가까울수록 군집화가 잘 됨 (군집 간 거리는 멀고, 군집 내 거리는 조밀).\n- 엘보우 기법(Elbow Method): SSE 감소율이 둔화되는 지점을 적정 K로 선정."
}

def build_enriched_explanation(q):
    """문항의 질문, 정답 선택지, 선택지 목록을 기반으로 정밀한 해설 생성"""
    question_text = q.get('question', '')
    options = q.get('options', [])
    ans_idx = q.get('answer', 1)
    
    if not options or ans_idx < 1 or ans_idx > len(options):
        ans_text = f"{ans_idx}번"
    else:
        ans_text = options[ans_idx - 1]

    # 정답 번호 기호 정리 (①, ②, ③, ④ -> 번호와 내용 추출)
    ans_clean = re.sub(r'^[①②③④⑤\d\.\s]+', '', ans_text).strip()
    
    explanation_parts = []
    explanation_parts.append(f"【정답: {ans_text}】")
    
    # 1. 정답 선택지 근거
    explanation_parts.append(f"✔ **정답 해설**: 제시된 문제의 조건에 가장 부합하는 정답은 **{ans_text}** 입니다.")

    # 2. 관련 핵심 개념 매칭
    matched_concept = None
    for key, concept in CONCEPT_DB.items():
        if key in question_text or key in ans_clean:
            matched_concept = concept
            break
            
    if matched_concept:
        explanation_parts.append(f"✔ **핵심 개념 정리**:\n{matched_concept}")
    else:
        # 선택지 분석을 통한 핵심 요약
        explanation_parts.append(f"✔ **핵심 포인트**: 문제에서 요구하는 핵심 지표/개념을 명확히 파악하여 **{ans_clean}** 항목의 특성과 비교 분석하는 것이 핵심입니다.")

    return "\n\n".join(explanation_parts)

def process_all_json_files():
    json_files = list(EXAMS_DIR.glob('bigdata_*.json'))
    print(f"[개발4팀 해설 보강 Engine] 총 {len(json_files)}개 시험 파일 보강 작업을 시작합니다.")
    
    total_updated = 0
    for file_path in sorted(json_files):
        try:
            data = json.loads(file_path.read_text(encoding='utf-8'))
            questions = data.get('questions', [])
            
            updated_count = 0
            for q in questions:
                # 기존 단순 템플릿 문구("... x번 문항입니다") 체크 후 교체
                curr_exp = q.get('explanation', '')
                if '문항입니다' in curr_exp or not curr_exp.strip() or '기출문제' in curr_exp:
                    q['explanation'] = build_enriched_explanation(q)
                    updated_count += 1
            
            if updated_count > 0:
                file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
                print(f"  └ [{file_path.name}] {updated_count}개 문항 해설 보강 완료!")
                total_updated += updated_count
        except Exception as e:
            print(f"  └ [{file_path.name}] 보강 실패: {e}")
            
    print(f"[완료] 총 {total_updated}개 문항의 해설 보강 및 JSON 저장 완료!")

if __name__ == '__main__':
    process_all_json_files()
