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
- Si·Ge: Hom, Kiszenik & Post (1975), 표에 공개된 격자상수: https://journals.iucr.org/paper?buy=yes&cnor=a12735
- Al: International Tables 표의 300 K 근사값: https://onlinelibrary.wiley.com/iucr/itc/Cb/ch4o4v0001/table4o4o2o1/
- Cu: IUCr 논문의 순수 Cu 기준값 a=3.615 Å: https://journals.iucr.org/a/issues/2017/04/00/sc5103/sc5103.pdf

</details>
