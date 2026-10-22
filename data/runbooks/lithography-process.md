# 노광 · 정밀장비 핵심 정리

**빛으로 패턴을 옮기고, 치수·초점·위치를 측정해 품질을 확인합니다.**

## 1. 패턴은 어떻게 만들어질까?

PR 도포 → 베이크 → 정렬·노광 → 필요 시 노광 후 베이크 → 현상 → 검사 → 후속 식각.

- **노광**은 빛으로 PR의 화학적 반응을 유도하는 단계입니다. 식각은 재료를 제거하는 별도 단계입니다.
- **양성 PR**은 노광된 부분이 현상에서 더 잘 제거되고, **음성 PR**은 노광된 부분이 남습니다.
- 패턴이 넓어졌다면 **현상 후 PR인지, 식각 후 구조인지** 먼저 구분합니다.

축소 투영의 기하학적 관계는 다음과 같습니다.
\[
w_{\mathrm{wafer}}\approx\frac{w_{\mathrm{mask}}}{R}
\]

**R**은 축소비의 크기입니다. 예를 들어 4배 축소에서 마스크의 400 nm는 기하학적으로 100 nm에 대응합니다. 실제 패턴은 회절·PR 반응·공정 조건의 영향도 받습니다.

## 2. 해상도와 초점은 함께 봐야 합니다

\[
NA=n\sin\alpha,\qquad CD\approx k_1\frac{\lambda_0}{NA}
\]

- **NA**: 개구수. n은 상측 매질의 굴절률, α는 광선 원뿔의 반각입니다.
- **λ₀**: 진공 파장. **CD**: 정의한 패턴의 임계 치수입니다.
- **k₁**: 조명·마스크·PR·공정 등에 영향을 받는 계수입니다.
- **파장을 줄이거나 NA를 높이면** 작은 패턴 형성에 유리합니다.

고정된 매질과 같은 허용 기준에서 초점 심도의 경향은 다음과 같습니다.
\[
DOF\propto\frac{\lambda_0}{NA^2}
\]

**NA를 높이면 해상도는 좋아지지만 초점 허용 범위는 좁아집니다.** 계수와 매질 조건 없이 이 식으로 실제 장비의 허용 초점 오차를 확정할 수는 없습니다.

예: λ₀=193 nm, k₁=0.30이면 NA=1.0에서 CD≈57.9 nm, NA=1.35에서 ≈42.9 nm입니다. 이론적 스케일 비교이며 실제 공정 선폭 보장값은 아닙니다.

## 3. 선폭·위치·노광량을 구분합니다

| 지표 | 뜻 | 확인할 값 |
| --- | --- | --- |
| CD | 선폭·홀 크기 등 패턴 치수 | 목표 대비 측정 치수 |
| Overlay | 서로 다른 층의 상대 위치 오차 | x·y 방향 정렬 차이 |
| Focus | 영상이 맺히는 초점 조건 | 높이·평탄도·초점 편차 |
| Dose | 면적당 노광 에너지 | 광세기와 노광 시간 |

\[
\Delta CD=CD_{\mathrm{measured}}-CD_{\mathrm{target}},\qquad
\epsilon_{CD}=\frac{\Delta CD}{CD_{\mathrm{target}}}\times100\%
\]

목표 100 nm, 측정 115 nm라면 **+15 nm, +15%**입니다. 이 수치만으로 노광량 부족을 단정하지 않습니다.

\[
\Delta r=\sqrt{(\Delta x)^2+(\Delta y)^2},\qquad
D=\int I(t)\,dt\approx It
\]

Δr은 두 층 사이 위치 오차의 크기입니다. D는 노광량, I는 면적당 광출력입니다. 일정한 I=10 mW/cm²로 2초 노광하면 D=20 mJ/cm²입니다. **CD 변화와 위치 이동은 다른 문제**입니다.

## 4. 정밀 위치 측정과 환경 영향

마이켈슨형 왕복 광로에서 거울 변위와 위상 변화의 관계는 다음과 같습니다.
\[
\Delta\phi=\frac{4\pi n\Delta x}{\lambda_0},\qquad
\Delta x=\frac{N\lambda_0}{2n}
\]

**N**은 지나간 간섭 주기의 수입니다. 공기에서 n≈1, λ₀=632.8 nm이면 한 주기는 거울 변위 약 **316.4 nm**에 해당합니다. 매질 굴절률·진동·광로 변화도 위상에 영향을 줍니다. 실제 스테이지 계측계 전체를 설명하는 식은 아닙니다.

\[
\Delta L\approx\alpha_T L\Delta T
\]

αT는 선팽창계수입니다. 길이 L인 구조물은 온도 변화 ΔT에 따라 팽창할 수 있습니다. **온도 안정성도 위치 정확도와 연결**됩니다.

## 5. 정렬·교정·검증의 차이

- **정렬:** 기준에 맞춰 상대 위치·방향을 맞춥니다.
- **교정:** 기준값과 측정값의 관계 및 불확도를 확인합니다. 조정과는 구별합니다.
- **검증:** 정해진 요구사항을 충족하는지 확인합니다.

문제가 생기면 **측정 단계 → 목표·측정값 → 발생 범위 → 변경 이력 → 확인한 사실** 순서로 정리합니다. 장비 허용치와 조정값은 승인된 기준을 사용합니다.

### 적용 범위

공개된 광학 원리의 학습용 요약입니다. 수차·공정 창·PR 화학·장비별 제어를 모두 포함하지 않으며, 실제 정비·설정 절차를 대신하지 않습니다.

### 참고

- [EPFL — Photolithography introduction](https://www.epfl.ch/research/facilities/cmi/process/photolithography/introductiontophotolithography/)


## 핵심 용어

| 용어 | 뜻 |
| --- | --- |
| 오버레이 | 서로 다른 층 패턴의 상대 위치 정렬 오차. 선폭 변화와 구분한다. |
| 초점심도 | 허용 영상·공정 품질을 유지할 수 있는 초점 방향 범위. 매질·허용 기준이 고정되면 대략 λ/NA² 경향을 갖는다. |

## 출처와 확인 범위

아래 자료의 해당 절·표·초록을 확인해 사실과 공식을 요약했습니다. 점검 순서·가상 사례·시각화는 앱에서 작성한 학습용 구성입니다.

| 확인 내용 | 근거 자료와 위치 |
| --- | --- |
| 공정 흐름·PR | [EPFL CMi: Introduction to Photolitography](https://www.epfl.ch/research/facilities/cmi/process/photolithography/introductiontophotolithography/) — Introduction, Photoresist chemistry, Photolithography steps |
| 일반 광학 분해능 | [OpenStax: Circular Apertures and Resolution](https://openstax.org/books/university-physics-volume-3/pages/4-5-circular-apertures-and-resolution) — §4.5, Eq. 4.5 |
| 교정·검증 | [JCGM 200:2012, International vocabulary of metrology](https://www.bipm.org/documents/20126/2071204/JCGM_200_2012.pdf) — §2.13, 2.15, 2.26, 2.39, 2.44–2.45 |
| CD=k₁λ/NA, DOF=k₂λ/NA²와 공정 의존 계수 | [H. Kirchauer: Optical Lithography, §2.1](https://iue.tuwien.ac.at/phd/kirchauer/node16.html) — Eq. 2.1–2.2 |

상세 서지·접근 범위는 `data/source_registry.json`에 기록합니다. 공식의 앱 내 적용 범위와 생략한 현상은 본문의 모델 설명을 따릅니다.
