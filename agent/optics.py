"""광학 실험 문서 선택과 공통 답변 지침. 측정 데이터는 생성하지 않는다."""
import re

# 문서 ID는 data/runbooks/<ID>.md와 일치해야 한다. 키워드는 학습 가중치가 아닌 규칙이다.
EXPERIMENTS = {
    "optical-equipment": ("카메라", "망원경", "현미경", "광학장비", "광학 장비", "접안렌즈", "튜브렌즈", "수광 반각", "목표 cd", "초각"),
    "measurement-and-uncertainty": ("불확도", "오차 전파", "계통오차", "우연오차", "분해능", "정밀도", "단위 오류", "측정 오차"),
    "ising-and-monte-carlo": ("ising", "이징", "아이징", "metropolis", "메트로폴리스", "몬테카를로", "monte carlo", "임계온도", "감수율", "열평형", "쿠폰 수집가"),
    "data-and-model-validation": ("데이터 누출", "데이터 분석", "이동평균", "numba", "최적화", "자기상관", "모델 검증", "과적합", "학습 데이터"),
    "electron-energy-levels": ("페르미", "fermi", "가전자대", "에너지 준위", "전자 들뜸", "전자들뜸", "정공", "도핑", "전도대"),
    "absorption-photoelectric": ("광흡수", "광전효과", "일함수", "밴드갭", "전도대", "전자 방출", "전자 들뜸", "금속 광전", "photoelectric"),
    "lithography-process": ("노광 공정", "노광공정", "패턴 만들기", "pr 도포", "positive pr", "negative pr"),
    "resolution-and-focus": ("해상도", "초점 심도", "초점심도", "개구수", "na를", "na=", "na와"),
    "pattern-quality": ("overlay", "오버레이", "패턴 품질", "cd와", "dose", "노광량"),
    "alignment-and-verification": ("교정", "검증", "정렬", "설치", "이설", "장비 이동"),
    "lithography-cd": ("euv", "duv", "노광", "레지스트", "포토레지스트", "선폭", "회로", "웨이퍼", "리소그래피"),
    "scattering-and-sky": ("산란", "하늘", "노을", "레일리", "rayleigh scattering"),
    "xrd-bragg": ("xrd", "브래그", "브레그", "결정면", "면간격", "2θ", "2세타"),
    "light-fundamentals": ("원자 크기", "전자 크기", "원자크기", "전자크기", "보어 반지름", "원자랑", "옹스트롬", "옹스트럼", "angstrom", "ångström", "å", "파장", "에너지", "광자", "진동수", "주파수", "전자기파", "가시광", "자외선", "적외선", "감마선", "x선", "빛의 종류", "빛의 특성", "빛이란", "굴절", "산란", "흡수", "결맞음", "단색", "빛의 기초", "기초 상식", "photon", "wavelength"),
    "grating-prism-spectrometer": ("회절격자", "분광", "프리즘", "스펙트럼", "spectrometer", "grating"),
    "shadow-and-diffraction": ("그림자", "회절", "슬릿", "diffraction", "이중슬릿"),
    "michelson-interferometer": ("마이켈슨", "michelson", "간섭계", "간섭무늬", "간섭 무늬"),
    "lenses-and-optical-instruments": ("거울", "렌즈", "초점", "배율", "흐릿", "lens"),
    "polarization-and-reflection": ("전반사", "임계각", "s파", "p파", "s편광", "p편광", "s·p", "s파 p파", "편광", "브루스터", "말뤼스", "반사", "polarization"),
    "speed-of-light": ("빛의 속도", "광속", "위상 지연", "시간 지연", "light speed"),
}


def select_experiments(query):
    """현재 문자열의 키워드를 문서 ID에 매핑하고 중복되는 일반 주제를 정리한다.

    Args:
        query: 사용자의 질문 문자열. 광학 경로에서는 실험 조건이 첨부될 수 있다.

    Returns:
        키워드와 일치하는 문서 ID 목록.
    """
    text = query.lower()
    # 구체적인 장비명을 일반적인 현상보다 우선한다.
    direct = []
    for key, words in EXPERIMENTS.items():
        if any(word in text for word in words):
            direct.append(key)
    if "grating-prism-spectrometer" in direct:
        direct = [k for k in direct if k != "shadow-and-diffraction"]
    if "michelson-interferometer" in direct and not any(w in text for w in ("슬릿", "회절")):
        direct = [k for k in direct if k != "shadow-and-diffraction"]
    return direct


def optical_targets(query, history=()):
    """현재 질문을 우선하고 제한된 후속 질문에만 이력을 이용해 문서를 선택한다.

    Args:
        query: 사용자의 질문 문자열. 광학 경로에서는 실험 조건이 첨부될 수 있다.
        history: 저장 순서대로 정리된 role/content 대화 메시지 목록.

    Returns:
        관련 문서 ID 목록. 광학 질문이 아니면 빈 목록.
    """
    card = short_concept_card(query)
    if card:
        return [card[0]]
    targets = select_experiments(query)
    if "optical-equipment" in targets:
        return ["optical-equipment"]
    lessons = [t for t in targets if t in {"lithography-process", "resolution-and-focus", "pattern-quality", "alignment-and-verification"}]
    if lessons:
        return lessons
    if "lithography-cd" in targets:
        return ["lithography-cd"]
    if targets:
        return targets
    # 인사/새로운 일반 질문에는 이전 광학 실험을 강제로 이어 붙이지 않는다.
    followup = re.search(r"^(?:네[.!? ]*$|아니요[.!? ]*$|그럼|그러면|이거|그거|이것|그것|방금|여전히|아직|다음|왜 이렇게|빛은|무늬만)|^(?:원리|공식|이론).*알려|^무늬가", query)
    if followup or re.search(r"\d\s*(?:nm|mm|cm|m|도|°|초|ns|개)", query):
        for msg in reversed(list(history)[-10:]):
            if msg.get("role") == "user":
                targets = select_experiments(msg.get("content", ""))
                if targets:
                    return targets
    if any(w in query for w in ("광학", "실험", "레이저")):
        return ["experiment-intake"]
    return []


def is_theory_question(query):
    """현재 질문의 설명 요청을 감지한다. 이전 대화의 의도를 강제하지 않는다."""
    return bool(re.search(r"이론|원리|개념|유도|공식|설명|배우|알려|theory|principle", query, re.I))


def answer_mode(query):
    # 자동 첨부된 실험 요약의 "원리를 설명해줘"가 사용자의 점검 의도를 덮지 않도록 한다.
    """첨부된 실험 요약과 사용자 질문을 분리해 이론 설명·점검 모드를 선택한다.

    Args:
        query: 사용자의 질문 문자열. 광학 경로에서는 실험 조건이 첨부될 수 있다.

    Returns:
        theory 또는 troubleshooting 문자열.
    """
    if query.startswith("[사용자 질문]\n"):
        query = query[len("[사용자 질문]\n"):].split("\n\n[현재 가상 실험]", 1)[0]
    # 증상이 명시된 경우만 점검한다. 짧은 사실 질문도 기본적으로 설명 요청이다.
    symptoms = re.search(
        r"안\s*보|보이지|안\s*돼|안\s*되|이상|고장|흐릿|흔들|문제|다르게|오차|"
        r"없어|없네|없어요|안 나|안나|겹쳐|다르|점검|진단|해결|작동|맞지|안 맞|잘못|두껍|두껍게|두꺼|넓어|침범", query)
    explicit_theory = re.search(r"이론|원리|개념|유도|법칙", query)
    return "theory" if explicit_theory or not symptoms else "troubleshooting"


# 생성 지침은 모델을 유도하지만 사실 검증기를 대신하지 않는다.
GROUNDING_RULES = (
    "답변은 결론을 먼저, 짧은 문단과 3~5개 핵심 항목으로 정리하라. 긴 배경 설명은 요청할 때만 추가하라. "
    "핵심 용어·결론·주의점은 **핵심 용어** 형태로 표시하라. 문장 전체를 강조하지 마라. 서식 지시어(예: 굵게, 볼드, 강조 표시)를 제목이나 본문에 출력하지 마라. 출처는 짧은 제목의 링크로 제시하라. "
    "현재 질문이 이전 대화와 다른 주제이면 현재 주제를 우선하고 이전 답변을 근거로 삼지 마라. "
    "문서가 현재 질문과 무관하거나 적용 조건이 다르면 관련 없음을 밝히고 추가 정보를 요청하라. "
    "근거가 없는 인과관계·수치·장비 조정값을 지어내지 마라. 문서 출처는 해당 주장을 뒷받침할 때만 인용하라. "
    "레일리 산란 1/λ⁴를 EUV 노광의 CD 불량에 적용하지 마라. "
    "한국어 숫자 범위는 취소선 방지를 위해 물결표 대신 '에서' 또는 '–'로 표현하라. "
)

THEORY_WRITER = (
    "당신은 한국어 광학 실험 학습 도우미다. 이번 요청은 이론 학습이다. "
    "이전 대화가 고장 점검이었어도 현재 질문을 우선하라. "
    "질문에 대한 직접적인 답을 첫 문장에 제시하라. 단순 사실 질문에는 1~3문장으로 답하라. "
    "예: 빛의 속도는? → 진공에서 빛의 속도는 정확히 299,792,458 m/s(약 30만 km/s)입니다. "
    "매질에서는 전파 특성이 달라집니다. 실험 방식이나 광경로를 되묻지 마라. "
    "실험 이론을 자세히 요청할 때만 목적·원리·공식·기호·단위·적용 조건을 풀어 설명하라. "
    "사용자가 유도를 요청하면 가정부터 단계적으로 설명하라. "
    "실험 종류가 이미 주어졌으면 증상·고장·장비 값을 먼저 묻지 마라. "
    "빛의 기초·파장·에너지 등 주제가 명확하면 실험 종류를 묻지 말고 개념부터 설명하라. "
    "실험 이론을 요청했는데 어떤 실험인지도 주제도 없을 때만 종류를 물어라. "
    "수치 예시는 가상 예제임을 표시하고 실제 측정값으로 표현하지 마라. "
    "고장 점검을 함께 요청한 경우에만 설명 뒤 점검 순서를 덧붙여라. "
    "수식은 인라인 \( ... \), 독립 수식 \[ ... \] LaTeX 구분자를 쓰고 코드 블록에 넣지 마라. "
    "참고한 문서 이름을 표시하라."
) + GROUNDING_RULES


OPTICS_WRITER = (
    "당신은 한국어 광학 실험 학습·점검 도우미다. 제공된 점검 문서와 사용자 관찰을 구분하라. "
    "실제 장비·센서에 연결되어 있지 않으므로 측정값이나 점검 완료 사실을 만들지 마라. "
    "실험 종류/증상이 불명확하면 먼저 핵심 확인 질문 1~2개를 하라. "
    "명확하면 관찰 결과에 따른 점검을 1) 2) 3) 순서로 제시하고 각 점검 이유를 짧게 설명하라. "
    "여러 원인을 단정하지 말고 후보로 표시하며 이전 대화에서 확인한 결과를 반영하라. "
    "공식은 단위와 성립 조건을 함께 표시하고 입력이 없으면 수치를 추측해 계산하지 마라. "
    "문서에 없는 장비별 조정이나 레이저 내부 분해를 권하지 마라. "
    "레이저 직접광/반사광을 눈으로 관찰하지 않도록 하고 정렬은 해당 실험실의 승인 절차를 따르게 하라. "
    "마지막에 참고한 runbook 이름을 표시하라."
) + GROUNDING_RULES


def short_concept_card(query):
    """단순 정의 질문에 쓸 범위 제한 자료. 상세·계산·실험 요청에는 적용하지 않는다."""
    if query.startswith('[사용자 질문]') or len(query)>65:
        return None
    if re.search(r'자세|상세|유도|계산|비교|실험|전체|종합|표로|정리|예제',query):
        return None
    if not re.search(r'뭐|무엇|뜻|이란|란[?？ ]*$|알려|설명',query):
        return None
    cards = {
        '산란': ('scattering-and-sky', '**산란은 빛이 입자나 물질의 불균일성과 상호작용해 진행 방향이 바뀌는 현상**이에요. 공기 중 분자가 햇빛을 여러 방향으로 산란시키는 것이 한 예입니다. **프리즘에서 색이 나뉘는 분산과는 다른 현상**이에요.'),
        '분산': ('grating-prism-spectrometer', '**분산은 물질의 굴절률이 빛의 파장에 따라 달라지는 현상**이에요. 프리즘에서 여러 색이 서로 다른 각도로 굴절되는 것이 대표적인 예입니다.'),
        '회절': ('shadow-and-diffraction', '**회절은 빛이 좁은 틈이나 장애물 주변을 지나며 퍼지고 무늬를 형성하는 파동 현상**이에요. 단일슬릿 뒤의 밝고 어두운 무늬가 한 예입니다.'),
        '간섭': ('michelson-interferometer', '**간섭은 빛의 파동들이 겹쳐 위상 관계에 따라 밝아지거나 어두워지는 현상**이에요. 두 빔을 다시 합치는 마이켈슨 간섭계에서 관찰할 수 있습니다.'),
        '페르미': ('electron-energy-levels', '**페르미 준위는 열평형에서 전자 상태의 점유 확률을 설명하는 에너지 기준**이에요. 유한 온도에서 그 에너지의 점유 확률은 ½이지만, 그곳에 실제 전자 상태가 반드시 있다는 뜻은 아닙니다.'),
    }
    matched=[card for term,card in cards.items() if term in query]
    return matched[0] if len(matched)==1 else None
