# 광학장비: 카메라·망원경·현미경·노광 광학계

- **카메라:** 물체와 센서에 상을 맺는 조건을 계산합니다.
- **망원경:** 각배율과 구경에 따른 각분해능을 구분합니다.
- **현미경:** 배율을 높이는 것과 더 작은 구조를 분해하는 것은 다릅니다.
- **노광:** 기하학적 축소 선폭과 회절·공정 조건에 따른 CD를 구분합니다.

## 실험 이론과 식
### 카메라
공기 중 얇은 렌즈, 실물체 거리 u>f, 실상 거리 v:
\[
\frac1f=\frac1u+\frac1v,\quad m=-\frac vu,\quad
\mathrm{FOV}=2\tan^{-1}\frac S{2f}.
\]
**물체 거리 u를 고정하면 |m|=f/(u−f)입니다. 실상 조건 0<f<u에서 초점거리 f를 늘리면 배율의 절댓값이 커지고, 상 거리 v도 증가합니다. 센서는 새 상면으로 옮겨 다시 초점을 맞춥니다.** 센서 크기를 바꾸는 것은 물체의 상 자체를 확대하지 않고 잘라 담는 범위를 바꾸는 것입니다.

S는 센서 폭입니다. FOV 식은 무한대 초점의 근사이며 근접 촬영에서는 상 거리·렌즈 모델을 고려합니다. 크기 W의 평면 물체를 센서 폭 S에 채우는 근축 조건은 u=f(1+W/S), v=f(1+S/W)입니다.

원형 조리개의 Airy 첫 영점 지름은 무한대 초점에서
\[
d=2.44\lambda F_\#.
\]
F수와 픽셀 크기를 비교할 수 있지만 실제 해상도를 이 식 하나로 확정하지 않습니다. 유한 배율에서는 유효 F수를 검토합니다.

### Kepler식 망원경
무한대 물체·최종상 무한대인 두 볼록렌즈 모델:
\[
M_\theta=-\frac{f_o}{f_e},\quad L=f_o+f_e,\quad
D_\mathrm{exit}=\frac D{|M_\theta|},\quad\theta_R=1.22\frac\lambda D.
\]
θR은 라디안이며 1 rad≈206265초각입니다. 각배율의 음수는 도립을 뜻합니다. 구경 D를 키우면 이상적인 각분해능이 좋아지지만 대기·수차·추적·검출 조건도 중요합니다.

### 무한 보정 현미경
\[
|M_\mathrm{obj}|=\frac{f_\mathrm{tube}}{f_\mathrm{obj}},\quad
\mathrm{NA}=n\sin\theta,\quad d_\mathrm{Abbe}=\frac{\lambda_0}{2\mathrm{NA}}.
\]
배율은 중간상 기준이며 접안렌즈 각배율을 포함하지 않습니다. Abbe 식과 점광원의 Rayleigh 기준은 관찰 대상과 정의가 다릅니다. 목표 d에서 NA≥λ₀/(2d), NA>n이면 현재 매질에서는 불가능합니다. 렌즈 교체 시 NA·작동거리·보정 호환성이 자동 유지되지 않습니다.

## 채팅으로 계산하기
장비 화면에서 질문하면 전송 시점의 조건을 함께 전달합니다. 아래 형식은 앱의 수식 역산을 함께 제공합니다.

| 장비 | 질문 예시 | 계산할 값 |
|---|---|---|
| 카메라 | 피사체 폭 200 mm를 센서에 채우려면 물체 거리는? | 물체 거리·상 거리 |
| 카메라 | 회절 무늬 지름 5 μm 이하의 F수는? | F수 상한 |
| 망원경 | 목표 각배율 40배의 접안렌즈 초점거리는? | 접안렌즈·경통 길이 |
| 망원경 | 1초각을 구분할 최소 구경은? | 구경 하한 |
| 현미경 | 분해 거리 300 nm에 필요한 NA와 수광 반각은? | NA·각도·매질 가능성 |
| 현미경 | 중간상 배율 80배의 대물 초점거리는? | 대물렌즈 초점거리 |
| 노광 | 목표 CD 16 nm에 필요한 NA와 DOF는? | 최소 NA·그때의 DOF |
| 노광 | 웨이퍼 목표 선폭 25 nm의 마스크 선폭은? | 기하학적 마스크 선폭 |

숫자 하나의 목표와 단위를 명확하게 써 주세요. 여러 목표·복잡한 표현은 자동 역산이 인식하지 못할 수 있습니다. 이 경우 AI는 부족한 조건과 식을 확인해야 하며, 임의의 정밀값을 만들면 안 됩니다. 그 외 파생값도 문서와 주어진 조건으로 질문할 수 있지만 자동 검산 범위 밖에서는 결과를 독립 확인해야 합니다.

## 참고 자료
- [MIT · 광학 강의 자료](https://ocw.mit.edu/courses/2-71-optics-spring-2009/)



## 핵심 용어

| 용어 | 뜻 |
| --- | --- |
| 대물구경 | 대물렌즈·거울의 빛을 받아들이는 유효 지름. 집광량과 회절 한계에 영향을 주며 초점거리·접안렌즈 크기와는 별개다. |
| 대물렌즈 | 물체 쪽에서 빛을 받아 상 형성에 관여하는 렌즈. |
| 접안렌즈 | 눈 쪽에서 중간상 또는 광학계 출사광을 관찰하도록 하는 렌즈. 망원경 종류에 따라 양·음의 초점거리를 쓸 수 있다. |
| 센서폭 | 상을 기록하는 센서의 가로 유효 길이. 초점거리와 함께 기록되는 화각을 결정한다. |
| F수 | 초점거리/입사동공 지름. 이상적 조건에서 같은 노출시간의 상면 조도는 대략 1/(F수)²에 비례한다. |
| 튜브렌즈 | 무한 보정 현미경에서 대물이 내보낸 평행광으로 중간상을 형성하는 렌즈. |
| 개구수 | NA=n sinα. 매질 굴절률 n과 수광 원뿔 반각 α로 정의하며 수광과 분해능에 관련된다. |

## 출처와 확인 범위

아래 자료의 해당 절·표·초록을 확인해 사실과 공식을 요약했습니다. 점검 순서·가상 사례·시각화는 앱에서 작성한 학습용 구성입니다.

| 확인 내용 | 근거 자료와 위치 |
| --- | --- |
| 카메라 근축 상 | [OpenStax: Thin Lenses](https://openstax.org/books/university-physics-volume-3/pages/2-4-thin-lenses) — §2.4 |
| 망원경·현미경의 기본 구성 | [OpenStax: Microscopes and Telescopes](https://openstax.org/books/university-physics-volume-3/pages/2-8-microscopes-and-telescopes) — §2.8 |
| 각분해능 | [OpenStax: Circular Apertures and Resolution](https://openstax.org/books/university-physics-volume-3/pages/4-5-circular-apertures-and-resolution) — §4.5, Eq. 4.5 |
| 추가 강의 안내 | [MIT OCW 2.71 Optics (2009), Lecture Slides](https://ocw.mit.edu/courses/2-71-optics-spring-2009/pages/lecture-slides/) — 강의 목록 1–5, 14–17 |
| Abbe형 분해능과 개구수의 적용 조건 | [Nikon MicroscopyU: Resolution](https://www.microscopyu.com/microscopy-basics/resolution) — Formula 1–2 |
| 무한 보정 대물렌즈와 튜브렌즈 구성 | [Nikon MicroscopyU: Infinity Optical Systems](https://www.microscopyu.com/microscopy-basics/infinity-optical-systems) — 무한 보정 대물렌즈·튜브렌즈 구성 설명 |

상세 서지·접근 범위는 `data/source_registry.json`에 기록합니다. 공식의 앱 내 적용 범위와 생략한 현상은 본문의 모델 설명을 따릅니다.
