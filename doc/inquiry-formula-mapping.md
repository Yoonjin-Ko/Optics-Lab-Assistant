# 탐구 질문의 공식 연결

14개 실험 화면의 **38개 탐구 질문**을 계산 목적에 연결했다. 질문 클릭은 입력창만 채우며, 보내기를 누를 때 최신 설정과 등록된 질문 ID를 함께 전달한다. 값을 바꾸면 새 설정으로 다시 계산한다.

## 처리 흐름

```text
탐구 질문 선택 → 입력창 → 보내기
 → 질문 원문·계약 버전·종류·ID 확인
 → MCP calculate_optics(operation="inquiry")
 → 서버에서 단위 계약·범위 확인 및 계산
 → 결과·공식·가정·출처 표시 (LLM 재계산 없음)
```

이 경로는 계산·설명 규칙을 코드로 작성했다. 생성 모델의 설명이 아니다. 직접 고친 질문이나 자유 질문에는 이 계약을 붙이지 않으며 기존 문서·검색·LLM 또는 지원 계산 경로를 사용한다. 모든 자연어 질문을 자동으로 수식화한 것은 아니다.

## 실험별 공식과 목적

| 실험 | 연결한 공식 | 탐구 목적 |
| --- | --- | --- |
| 볼록렌즈 | 1/f=1/u+1/v, m=−v/u | 현재 상 위치·방향·스크린 가능 여부 / m=−1 목표에서 f=u/2 역산 / 초점 통과 전후 |
| 오목렌즈 | v=fu/(u−f), f<0 | 물체 쪽 정립 허상 / u 감소 시 허상 위치·배율 변화 |
| 오목거울 | 1/f=1/u+1/v, f>0 | 거울 앞뒤의 상 / 같은 크기 실상 u=2f / 확대 허상 0<u<f |
| 볼록거울 | 1/f=1/u+1/v, f<0 | 거울 뒤 허상 위치 / 물체 접근 시 위치·배율 변화 |
| 편광판 | I/I₀=cos²θ | 절반 세기 목표 각도 / 현재 각도와 두 배 각도의 세기 비교 |
| 단일슬릿 | a sinθ₁=λ, W≈2Lλ/a | 현재 중앙 무늬 전체 폭 / 폭 두 배에 필요한 변수 변경 |
| 마이켈슨 | N=2Δx/λ, Δx=Nλ/2, Λ≈λ/(2\|α\|) | 10주기 목표 변위 / 기울기와 선형 간격 / N으로 파장 역산 |
| XRD | 2d sinθ=nλ, a=d√(h²+k²+l²) | 검출기 2θ / 파장과 피크 이동 / 현재 스캔을 피크로 가정한 d 역산 및 입방 a |
| s/p·전반사 | Snell·Fresnel 반사율, tanθB=n₂/n₁, sinθc=n₂/n₁ | s/p 반사율 비교 / 브루스터 각 / 전반사 가능 여부·임계각 |
| 프리즘 | 두 면 Snell, r₁+r₂=A, δ=i+e−A, Cauchy n(λ) | 각 면의 굴절각·편이각 / 빨강·보라 비교 / 꼭지각과 분리각 |
| 광흡수·광전효과 | Eγ=hc/λ, λ문턱=hc/E문턱, Kmax=max(0,Eγ−Φ) | 내부 들뜸과 진공 방출 구분 / 문턱 파장 / 세기와 단일 광자 에너지 구분 |
| 카메라 | v=fu/(u−f), \|m\|=f/(u−f), dAiry=2.44λF, 조도∝F⁻² | 센서 상면 / 확대 방향 / F수에 따른 밝기·회절 크기 |
| 망원경 | \|M\|=fo/\|fe\|, L=fo+fe, θR=1.22λ/D | 배율 두 배 목표 접안 f / 케플러·갈릴레이 렌즈 간격 / 구경과 분해능 |
| 현미경 | \|M\|=ftube/fobj 또는 v/fobj−1, d=λ/(2NA), NA=n sinθ | 중간상 위치·방향 / 배율 두 배 목표 대물 f / 확대와 분해능 구분 |

## 단위·조건

UI 계약 버전은 1이다. 렌즈·거울 f/u는 cm, 카메라·망원경·현미경의 길이는 mm, 슬릿은 mm·스크린 거리는 m, 광학 파장은 nm, 마이켈슨 변위는 µm·기울기는 mrad, 각도는 deg, 에너지 문턱은 eV이다. 이 단위는 임의 추정하지 않으며 버전 변경 시 프론트와 서버를 함께 변경해야 한다.

- 렌즈의 v>0은 물체 반대쪽, 거울의 v>0은 거울 앞이다. 부호를 화면 방향과 구분한다.
- 초점에서 유한 상 없음, Δx=N=0에서 파장 역산 불가, NA>n, 금지 XRD 반사·실수 해 없음 등을 별도로 처리한다.
- XRD 물질 프리셋의 d와 소멸 규칙은 서버에서 다시 계산한다. 수동 d에 미지정 (hkl)을 만들어 붙이지 않는다.
- 프리즘은 현재 UI와 같은 가상 Cauchy 모델이다. 꼭지각 변경 시 기준 입사각도 변하는 UI 조건을 명시한다.
- 마이켈슨 기울기 간격은 선형 성분 근사이다. 곡률 무늬·현장 빔 겹침과 구분한다.
- 편광판·Fresnel 값은 이상적 계산이며 현장 영점·누설 모델의 검출값이 아니다.

## 검증과 근거

- Python 테스트 **37개 통과**. 그중 새 테스트 5개가 전체 38개 질문 매핑, 설정 변경, 기존 오답 수치·방향, 경계 조건 및 실제 MCP 그래프 경로를 검사한다.
- UI에서 전송 메시지를 캡처한 **53개 사례**(기본 38개 + 설정·물질 변경 15개)를 실제 MCP로 실행해 53개 모두 계산 경로 완료. LLM을 호출하면 실패하도록 평가했다.
- 53/53은 연결·계산 실행 성공이며 일반 AI 정확도 점수가 아니다. 물리 정답은 별도의 기준값·불변 조건 테스트로 확인한다.
- 기존 JS 실험·장비·현장 조절 검사와 14개 질문 UI 표시·입력 준비 검사 통과.

[실제 결과·시간](../eval/inquiry_contract_results.json) · [재현 코드](../eval/inquiry_contract_eval.py) · [테스트](../tests/test_inquiry_calculations.py)

```bash
LANGSMITH_TRACING=false LANGCHAIN_TRACING_V2=false .venv/bin/python -m unittest discover -s tests -q
LANGSMITH_TRACING=false LANGCHAIN_TRACING_V2=false .venv/bin/python eval/inquiry_contract_eval.py
```

공식 근거는 각 실험 문서의 출처 절과 [OpenStax 얇은 렌즈](https://openstax.org/books/university-physics-volume-3/pages/2-4-thin-lenses), [편광](https://openstax.org/books/university-physics-volume-3/pages/1-7-polarization), [단일슬릿](https://openstax.org/books/university-physics-volume-3/pages/4-1-single-slit-diffraction), [원형 구경·분해능](https://openstax.org/books/university-physics-volume-3/pages/4-5-circular-apertures-and-resolution)을 참고한다.
