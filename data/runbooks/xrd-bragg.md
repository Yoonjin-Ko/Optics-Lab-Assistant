# XRD와 브래그 법칙

> **광학 실험 학습 노트** · 핵심을 먼저 보고, 필요한 내용만 펼쳐보세요.

- **브래그 법칙:** nλ = 2d sinθ, 측정 축은 보통 2θ.
- **시료별 비교:** 원소뿐 아니라 결정 구조·격자상수가 필요합니다.
- **앱의 범위:** 반사 위치만 계산하며 세기·물질 동정은 하지 않습니다.

<details>
<summary><strong>이론·수식·점검 절차 자세히 보기</strong></summary>

## 실험 이론
XRD는 결정에서 산란된 X선의 간섭을 관찰한다. 브래그 법칙은 특정 결정면의 보강 간섭 각도를 설명한다. 단일 면의 각도만으로 물질을 동정하거나 피크 세기를 예측할 수 없다.

## 이론과 필요한 값
\[
n\lambda=2d\sin\theta,\quad \theta=\arcsin\left(\frac{n\lambda}{2d}\right)
\]
lambda와 d는 동일 길이 단위, n은 양의 정수이다. theta는 결정면과 입사 빔 사이 각도이고 그래프 축은 보통 2theta이다. n lambda > 2d이면 해당 차수의 해가 없다.
앱 가상 실험은 단일 면의 브래그 위치만 표시한다. 피크 폭·세기·구조인자·장비 오차를 모델링하지 않는다.

## 먼저 물어볼 질문
계산 질문은 파장, 면간격, 차수를 확인한다. 실제 피크 이동이면 같은 반사인지와 측정 각도 정의·교정 여부를 확인한다.

## 점검 순서
1. theta와 2theta 및 nm·Å 단위를 구분한다(1 Å=0.1 nm).
2. 비교하는 피크의 결정면과 파장이 같은지 확인한다.
3. 단일 피크 이동만으로 원인이나 물질을 확정하지 않는다.

## 참고 자료
- IUCr: https://www.iucr.org/what-we-do/education/pamphlets/introduction-calculation-of-structure-factors

## 결정 시료 프리셋
원자 한 개의 종류만으로 XRD를 정할 수 없다. 결정 구조·격자상수·배향·파장 등이 필요하다. 앱 프리셋은 순수한 입방 결정의 근사값을 고정한 학습 모델이다. 실제 온도·응력·순도·장비 오차는 반영하지 않는다.

| 시료 | 구조 | 격자상수 a (nm) |
|---|---|---|
| Si | diamond cubic | 0.5430941 |
| Ge | diamond cubic | 0.5657820 |
| Al | FCC | 0.40495 |
| Cu | FCC | 0.3615 |

입방 결정의 d_hkl=a/sqrt(h²+k²+l²). 프리셋은 n=1로 계산하고 높은 차수는 다른 hkl 반사와 구분한다. FCC는 모두 홀수 또는 모두 짝수, diamond의 모두 짝수는 h+k+l이 4의 배수여야 허용된다. Si(200)은 이 모델에서 소멸하며 Al(200)은 허용된다.
분말의 가능한 위치 목록과 실제 단결정 웨이퍼의 θ–2θ 측정은 같지 않다. 원자 산란 인자·다중도·온도 인자·배향·장비 함수 등을 계산하지 않으므로 막대 높이는 세기가 아니다. 같은 d의 반사는 대표 hkl로 묶는다.

### 프리셋 출처
- Si·Ge: Hom, Kiszenik & Post (1975), 공개 초록에 기재된 격자상수: https://onlinelibrary.wiley.com/doi/abs/10.1107/s0021889875010965
- Al: Roach 등 (2013), Table 2 Experiment 열의 인용값: https://journals.iucr.org/j/issues/2013/06/00/he5613/index.html
- Cu: IUCr 논문의 순수 Cu 기준값 a=3.615 Å: https://journals.iucr.org/a/issues/2017/04/00/sc5103/sc5103.pdf

</details>


## 핵심 용어

| 용어 | 뜻 |
| --- | --- |
| 결정구조 | 원자·이온·분자가 공간에서 주기적으로 배열되는 방식. 격자와 그 격자점에 배치되는 원자 묶음(기저)을 함께 고려한다. XRD가 구조를 만드는 것이 아니라 회절로 구조를 추론한다. |
| 격자상수 | 단위격자의 크기와 모양을 정하는 길이 a,b,c와 각도 α,β,γ. 입방정계에서는 a=b=c이고 세 각은 90°이다. 일반적으로 면간격 d와 같은 값이 아니다. |
| 단위격자 | 반복하여 전체 결정을 구성할 수 있는 기본 공간 단위. |
| 밀러지수 | 결정면의 방향을 나타내는 정수 표기 (hkl). 입방정계에서 면간격은 d=a/√(h²+k²+l²). |
| 고니오미터 | 시료·검출기의 각도를 정밀하게 조절하고 읽는 장치. 대칭 θ–2θ 배치에서 시료면 기준 입사각은 θ, 산란각은 2θ. |
| 소멸규칙 | 단위격자 내부 원자들의 산란파 합으로 일부 반사가 사라질 수 있다. 구조인자는 원자 위치·산란인자와 관련되며 브래그 조건만으로 강도를 정할 수 없다. |

## 출처와 확인 범위

아래 자료의 해당 절·표·초록을 확인해 사실과 공식을 요약했습니다. 점검 순서·가상 사례·시각화는 앱에서 작성한 학습용 구성입니다.

| 확인 내용 | 근거 자료와 위치 |
| --- | --- |
| 브래그·구조인자 | [IUCr: Introduction to the calculation of structure factors](https://www.iucr.org/what-we-do/education/pamphlets/introduction-calculation-of-structure-factors) — Bragg equation Eq. (5), 원자 산란인자·구조인자 설명 |
| Si·Ge 값 | [Hom, Kiszenik & Post (1975), J. Appl. Cryst. 8, 457–458](https://onlinelibrary.wiley.com/doi/abs/10.1107/s0021889875010965) — 공개 Abstract |
| Al 값 | [Roach et al. (2013), J. Appl. Cryst. 46, 1755–1770](https://journals.iucr.org/j/issues/2013/06/00/he5613/index.html) — Table 2, Experiment 열 |
| Cu 값 | [Hansford et al. (2017), Acta Cryst. A73, 293–311](https://journals.iucr.org/a/issues/2017/04/00/sc5103/sc5103.pdf) — 인쇄 p.306 (PDF p.14), pure copper 기준값 문장 |

상세 서지·접근 범위는 `data/source_registry.json`에 기록합니다. 공식의 앱 내 적용 범위와 생략한 현상은 본문의 모델 설명을 따릅니다.
