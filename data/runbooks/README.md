# 광학 학습·점검 문서

`agent/optics.py`가 질문과 제한된 대화 맥락에서 문서 ID를 선택합니다. MCP Resource `optics://documents/{topic}`는 같은 이름의 Markdown을 읽습니다. 브라우저 문서 페이지는 AI 호출 없이 직접 읽습니다.

| 분야 | 문서 |
| --- | --- |
| 기초 | [빛·파장·에너지·길이 척도](light-fundamentals.md) |
| 입문 | [실험 종류·관찰 정보 정리](experiment-intake.md) |
| 분광 | [회절격자·프리즘](grating-prism-spectrometer.md) |
| 회절 | [그림자·슬릿](shadow-and-diffraction.md) |
| 간섭 | [마이켈슨 간섭계](michelson-interferometer.md) |
| 상 형성 | [렌즈·광학장치](lenses-and-optical-instruments.md) |
| 반사 | [편광·반사·전반사](polarization-and-reflection.md) |
| 광속 | [빛의 속도 측정](speed-of-light.md) |
| 결정 | [XRD·브래그 법칙](xrd-bragg.md) |
| 산란 | [산란·하늘색 이론](scattering-and-sky.md) |
| 전자 | [광흡수·광전효과](absorption-photoelectric.md), [전자·에너지 준위](electron-energy-levels.md) |
| 장비 | [카메라·망원경·현미경](optical-equipment.md) |
| 노광 | [노광·정밀장비 핵심 정리](lithography-process.md), [CD 이상 해석](lithography-cd.md) |
| 측정 | [측정·불확도](measurement-and-uncertainty.md) |
| 모델 | [데이터·모델 검증](data-and-model-validation.md), [Ising·Monte Carlo](ising-and-monte-carlo.md) |

문서는 센서 데이터나 실제 장비 매뉴얼이 아닙니다. 실험별 공식·적용 조건을 확인하고 장비별 작업에는 해당 실험실의 승인된 절차를 사용합니다. 파일명 변경 시 매핑·문서 API 허용 목록·테스트를 함께 수정합니다.

## 용어 색인

`data/optics_terms.json`은 실험 용어·동의어·정의·연결 문서를 관리합니다. 각 실험 문서의 ‘핵심 용어’에 같은 정의를 수록하며 테스트에서 동기화와 검색 연결을 확인합니다. 질문별 정답을 반환하는 분기가 아닌 문서 검색용 지식 자료입니다.

## 출처 관리

18개 학습 문서의 근거 자료·절·표·접근 범위는 [출처 레지스트리](../source_registry.json)에 기록합니다. 각 문서 하단에서도 확인할 수 있습니다. [출처 점검 기록](../../doc/source-audit.md)은 수치의 성격과 검증 범위를 설명합니다.

## 탐구 질문 검증

[실모델 검증 기록](../../doc/inquiry-validation.md)에 질문별 원답·응답 시간·내용 판정을 기록합니다. 형식 검사 통과와 물리 내용 정답은 구분합니다. 실패한 답변도 기록에서 제외하지 않습니다.
