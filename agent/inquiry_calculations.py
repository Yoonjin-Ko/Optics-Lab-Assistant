"""탐구 질문 계약: 질문 문자열 추측 없이 현재 설정으로 공식·역산을 실행한다.

단위는 UI 계약의 nm/mm/cm/m/µm/deg/mrad/eV를 따른다. 설정값은
클라이언트 계산 결과를 신뢰하지 않고 백엔드에서 유한값·범위를 검사한다.
"""
import json
import math
from pathlib import Path

CATALOG = json.loads((Path(__file__).resolve().parents[1]/'data/inquiry_catalog.json').read_text())
DOCS = dict.fromkeys(['lens','concave-lens','concave-mirror','convex-mirror'], 'lenses-and-optical-instruments')
DOCS.update(polarization='polarization-and-reflection', diffraction='shadow-and-diffraction', michelson='michelson-interferometer', xrd='xrd-bragg', fresnel='polarization-and-reflection', prism='grating-prism-spectrometer', absorption='absorption-photoelectric', camera='optical-equipment', telescope='optical-equipment', microscope='optical-equipment')

def plan_inquiry(query):
    """등록된 질문과 계약이 모두 일치할 때만 도구 경로로 보낸다."""
    from .optics import user_question
    import re
    match=re.search(r'\[탐구 계산 계약\]\n([^\n]+)',query)
    if not match:return None
    try:
        request=json.loads(match[1]);kind=request['kind'];index=request['index']
        if type(index) is not int or index<0 or CATALOG[kind][index]!=user_question(query).strip():return None
        if request.get('version')!=1 or not isinstance(request['settings'],dict):return None
        return {'operation':'inquiry','parameters':request,'origins':{},'document':DOCS[kind]}
    except (ValueError,KeyError,TypeError,IndexError):return None


def calculate_inquiry(request):
    """공식에 기반한 결과를 설명과 함께 반환한다. LLM 재계산은 필요 없다."""
    base={'operation':'inquiry','ok':False,'status':'invalid_input'}
    try:
        k=request['kind'];i=request['index'];p=request['settings']
        if type(i) is not int or not 0<=i<len(CATALOG[k]):raise ValueError('등록되지 않은 질문')
        def num(key,low=None,high=None):
            x=p.get(key)
            if type(x) not in (int,float) or not math.isfinite(x):raise ValueError(key+': 유한 숫자가 필요합니다.')
            if low is not None and x<low or high is not None and x>high:raise ValueError(key+': 허용 범위 밖입니다.')
            return x
        def positive(key):
            x=num(key)
            if x<=0:raise ValueError(key+': 양수가 필요합니다.')
            return x
        def enum(key,choices):
            x=p.get(key)
            if x not in choices:raise ValueError(key+': 지원하지 않는 종류입니다.')
            return x
        def fmt(x):return f'{x:.6g}'
        def asin(x):
            if abs(x)>1+1e-12:raise ValueError('굴절/회절 조건의 실수 해가 없습니다.')
            return math.asin(max(-1,min(1,x)))
        rad=math.radians;deg=math.degrees
        source=DOCS[k];formula='';answer='';assumption='이상적 교육 모델의 입력 기반 이론값이며 실측이 아닙니다.'
        if k in ('lens','concave-lens','concave-mirror','convex-mirror'):
            f=positive('focal')*(-1 if k in ('concave-lens','convex-mirror') else 1);u=positive('object');mirror='mirror' in k
            formula='1/f=1/u+1/v, m=−v/u'
            v=None if math.isclose(u,f,rel_tol=1e-12) else f*u/(u-f)
            if i==0:
                if v is None:answer='물체가 초점에 있어 유한한 상이 생기지 않습니다. 출사광은 평행합니다.'
                else:
                    side=('거울 앞' if v>0 else '거울 뒤') if mirror else ('렌즈의 물체 반대쪽' if v>0 else '렌즈의 물체 쪽')
                    answer=f'현재 상은 **{side} {fmt(abs(v))} cm**에 생깁니다. 배율 m={fmt(-v/u)}이며 '+('도립 실상으로 스크린에 맺힙니다.' if v>0 else '정립 허상으로 광선의 역연장선이 만납니다. 스크린에 직접 맺히지 않습니다.')
            elif k=='lens' and i==1:
                formula+='; m=−1 ⇒ u=v=2f'
                answer=f'물체 거리 {fmt(u)} cm를 고정하면 **초점거리 f={fmt(u/2)} cm**로 맞춥니다. 목표 상 거리도 {fmt(u)} cm이고, 배율은 −1입니다.'
            elif k=='lens':answer=f'현재 f={fmt(f)} cm입니다. u>f에서는 반대쪽 도립 실상, u=f에서는 유한한 상 없음, 0<u<f에서는 물체 쪽 정립 확대 허상입니다. 초점 부근에서 상 거리는 발산하며 연속적인 유한 위치로 통과하지 않습니다.'
            elif k=='concave-mirror' and i==1:answer=f'물체를 **거울 앞 u=2f={fmt(2*f)} cm**에 둡니다. 상도 같은 위치에 생기며 배율 −1의 도립 실상입니다.'
            elif k=='concave-mirror':answer=f'물체를 **거울과 초점 사이 0<u<{fmt(f)} cm**에 둡니다. 상은 거울 뒤 정립 확대 허상입니다. u=f에서는 유한한 상이 없습니다.'
            else:answer=f'물체 거리 u를 줄이면 허상은 '+('거울' if mirror else '렌즈')+f'에 가까워지고 커집니다. |v|=|f|u/(u+|f|), m=|f|/(u+|f|)이므로 현재 |v|={fmt(abs(v))} cm, m={fmt(-v/u)}에서 |v|는 감소하고 m은 증가합니다. 정립 축소 허상은 유지됩니다.'
        elif k=='polarization':
            a=num('angle');ratio=math.cos(rad(a))**2;formula='I/I₀=cos²θ'
            answer=('이상적인 분석기에서 최대 투과 세기의 절반은 **상대각 45° 또는 135° (180° 주기)**입니다. 현재 '+fmt(a)+'°에서 I/I₀='+fmt(ratio)+'입니다.' if i==0 else f'두 배가 되지 않습니다. 현재 {fmt(a)}°에서 I/I₀={fmt(ratio)}, 각도 두 배인 {fmt(2*a)}°에서는 {fmt(math.cos(rad(2*a))**2)}입니다. cos² 의존성이므로 선형 비례가 아닙니다.')
            assumption+=' 현장 조절의 누설·축 영점 오차를 제외한 이상 편광판 기준입니다.'
        elif k=='diffraction':
            w=positive('wavelength');a=positive('slit');L=positive('distance');width=2*L*w*.001/a;formula='a sinθ₁=λ; W≈2Lλ/a'
            answer=(f'파장 λ={fmt(w)} nm, 슬릿 폭 a={fmt(a)} mm, 거리 L={fmt(L)} m가 필요합니다. **중앙 밝은 무늬 전체 폭 W≈{fmt(width)} mm**, 첫 암선은 중심에서 ±{fmt(width/2)} mm입니다.' if i==0 else f'현재 폭 W≈{fmt(width)} mm를 두 배로 하려면, 다른 값은 고정하고 λ를 {fmt(2*w)} nm 또는 L을 {fmt(2*L)} m로 늘리거나 a를 {fmt(a/2)} mm로 줄입니다.')
            if p.get('slitMode')=='double':
                d=positive('slitSeparation')
                if d<=a:raise ValueError('이중슬릿 중심 간격은 슬릿 폭보다 커야 합니다.')
                fringe=w*.001*L/d
                formula+='; Δy≈λL/d; I/I(0)=sinc²(πa sinθ/λ)cos²(πd sinθ/λ)'
                answer=answer.replace('중앙 밝은 무늬 전체 폭','회절 포락선 중앙 전체 폭')
                answer+=f' 현재 이중슬릿 간섭 간격은 **{fmt(fringe)} mm**입니다. 이 간격과 회절 포락선 전체 폭을 구분합니다. 간섭 간격을 두 배로 하려면 λ 또는 L을 두 배, 혹은 중심 간격 d를 절반으로 바꾸며 d>a를 유지합니다.' if i==1 else f' 현재 이중슬릿에서는 포락선 안에 **간격 {fmt(fringe)} mm**의 간섭무늬가 생깁니다. 포락선 폭과 간섭 간격은 다른 값입니다.'
            assumption+=' 원거리·작은 각도 근사이며 조절 범위와 λ/a≪1 조건을 별도로 확인합니다.'
        elif k=='michelson':
            w=positive('wavelength');dx=num('displacement',0);tx=num('mirrorTiltX');ty=num('mirrorTiltY');N=2*dx*1000/w;formula='N=2Δx/λ; Δx=Nλ/2; Λ≈λ/(2|α|)'
            if i==0:answer=f'무늬 **10주기**가 지나가려면 거울을 추가로 **{fmt(10*w/2000)} µm** 옮깁니다. 왕복 광경로 변화가 거울 변위의 두 배이기 때문입니다. 현재 λ={fmt(w)} nm입니다.'
            elif i==1:
                tilt=math.hypot(tx,ty);answer=('현재 상대 기울기 0으로 선형 기울기 무늬의 간격은 무한대입니다.' if tilt==0 else f'현재 기울기 크기 {fmt(tilt)} mrad에서 선형 무늬 간격은 약 {fmt(w/(2000*tilt))} mm입니다.')+' 기울기를 키우면 간격이 줄고, 기울기 벡터를 회전하면 무늬 방향도 변합니다. 빔 겹침이 부족하면 대비가 떨어집니다.'
            else:answer=(f'λ=2Δx/N으로 역산합니다. 현재 Δx={fmt(dx)} µm, 이론 N={fmt(N)}을 대입하면 **λ={fmt(w)} nm**입니다. 이 N은 같은 모델로 계산한 값이므로 독립적인 파장 측정은 아닙니다.' if N>0 else 'λ=2Δx/N을 사용하지만 현재 Δx=0, N=0이므로 역산할 수 없습니다. 0이 아닌 변위와 독립적으로 센 무늬 수가 필요합니다.')
            assumption+=' 공기 n≈1, 한 팔 거울의 작은 기울기·왕복 경로 기준입니다. 간격은 선형 성분이며 원형 곡률 무늬와 다릅니다.'
        elif k=='fresnel':
            n1=positive('n1');n2=positive('n2');a=num('incidence',0,89.999999);s=n1/n2*math.sin(rad(a));tir=s>1;ci=math.cos(rad(a));ct=0 if tir else math.sqrt(max(0,1-s*s))
            rs=1 if tir else ((n1*ci-n2*ct)/(n1*ci+n2*ct))**2;rp=1 if tir else ((n2*ci-n1*ct)/(n2*ci+n1*ct))**2
            formula='n₁sinθᵢ=n₂sinθₜ; Rₛ=|(n₁cosθᵢ−n₂cosθₜ)/(n₁cosθᵢ+n₂cosθₜ)|²; Rₚ=|(n₂cosθᵢ−n₁cosθₜ)/(n₂cosθᵢ+n₁cosθₜ)|²; tanθB=n₂/n₁; sinθc=n₂/n₁ (n₁>n₂)'
            if i==0:answer=f'현재 Rₛ={fmt(rs)}, Rₚ={fmt(rp)}로 '+('두 반사율이 같습니다.' if math.isclose(rs,rp,abs_tol=1e-12) else ('s' if rs>rp else 'p')+'편광이 더 많이 반사됩니다.')
            elif i==1:answer=('두 매질 굴절률이 같아 모든 입사각에서 반사가 없습니다. 특정 브루스터 각으로 구분할 필요가 없습니다.' if n1==n2 else f'법선 기준 입사각을 **브루스터 각 {fmt(deg(math.atan(n2/n1)))}°**로 맞춥니다. 이상적인 비흡수 유전체 경계에서 p 반사율이 0입니다.')
            else:answer=(f'전반사가 가능합니다. 임계각은 **{fmt(deg(math.asin(n2/n1)))}°**이며 입사각이 이를 초과해야 합니다.' if n1>n2 else f'현재 n₁={fmt(n1)}≤n₂={fmt(n2)}이므로 **전반사가 불가능하고 임계각도 없습니다**.')
            assumption+=' 등방성 비자성·비흡수 유전체의 이상적 경계이며 현장 각도 영점 오차와 편광 혼합은 제외합니다.'
        elif k=='absorption':
            mode=enum('absorptionType',['metal','semiconductor','insulator']);t=positive('threshold');w=positive('absorptionWave');energy=1239.841984/w;cut=1239.841984/t;formula='Eγ=hc/λ; λ문턱=hc/E문턱; Kmax=max(0,Eγ−Φ) (금속)'
            if i==0:answer=f'현재 모드는 **'+('금속 표면의 진공 방출' if mode=='metal' else '물질 내부 밴드 간 들뜸')+f'**입니다. 광자 에너지 {fmt(energy)} eV, '+('일함수 Φ' if mode=='metal' else '밴드갭 Eg')+f'={fmt(t)} eV로 '+('에너지 조건을 만족합니다.' if energy>=t else '문턱 에너지가 부족합니다.')+(' 내부 들뜸을 물질 밖 방출로 해석하면 안 됩니다.' if mode!='metal' else f' 최대 운동에너지는 {fmt(max(0,energy-t))} eV입니다.')
            elif i==1:answer=f'현재 문턱 {fmt(t)} eV에 대응하는 파장은 **{fmt(cut)} nm**입니다. 에너지를 문턱보다 높이려면 이보다 짧은 파장을 선택합니다. 등호에서는 '+('최대 방출 운동에너지가 0입니다.' if mode=='metal' else '이상적 에너지 문턱에 도달합니다.')
            else:answer=f'**이 단일 광자 모델에서는 불가능합니다.** 세기를 높여도 광자 한 개의 에너지 {fmt(energy)} eV는 변하지 않습니다. 세기는 광자 유입률을 바꾸며, '+('현재 금속의 방출 여부는 Eγ와 일함수로 결정합니다.' if mode=='metal' else '현재 비금속 모드는 진공 방출을 계산하지 않습니다.')
            assumption+=' 실제 흡수율·전이 확률·간접 전이·다광자 효과·전류는 예측하지 않습니다.'
        elif k=='camera':
            f=positive('f');u=positive('u');F=positive('fNumber');w=positive('wave');formula='v=fu/(u−f); |m|=f/(u−f); dAiry=2.44λF; 상면 조도∝1/F²'
            if u<=f:raise ValueError('현재 카메라 모델은 u>f의 실상 조건이 필요합니다.')
            v=f*u/(u-f)
            if i==0:answer=f'선명한 상은 **렌즈 뒤 {fmt(v)} mm**에 생깁니다. 센서를 이 상면에 놓습니다. 현재 배율 m={fmt(-v/u)}입니다.'
            elif i==1:answer=f'물체 거리 {fmt(u)} mm를 고정하면 **초점거리를 늘리되 f<u를 유지**합니다. 현재 f={fmt(f)} mm, |m|={fmt(v/u)}입니다. f 증가 시 |m|가 커지고 상면 v도 멀어지므로 센서 초점을 다시 맞춰야 합니다.'
            else:answer=f'F수를 높이면 **상면 밝기는 감소하고 회절 무늬는 커집니다**. 현재 F/{fmt(F)}, λ={fmt(w)} nm에서 Airy 첫 영점 지름은 {fmt(2.44*w*F/1000)} µm입니다. F수를 두 배로 하면 밝기는 약 1/4, 지름은 두 배입니다.'
            assumption+=' 근축·원형 입사동공·회절 한계이며 수차와 유한 배율 유효 F수는 생략합니다.'
        elif k=='telescope':
            fo=positive('objective');fe=positive('eyepiece');D=positive('diameter');w=positive('wave');g=enum('telescopeModel',['kepler','galilean'])=='galilean';M=fo/fe;formula='|M|=fo/|fe|; L=fo+fe (접안 f 부호 포함); θR=1.22λ/D'
            if i==0:answer=f'배율 {fmt(M)}배를 두 배로 하려면 접안 초점거리의 절댓값을 **{fmt(fe/2)} mm**로 줄입니다. '+('갈릴레이식 접안은 음의 초점거리입니다.' if g else '케플러식 접안은 양의 초점거리입니다.')+f' 새 렌즈 간격은 {fmt(fo+(-1 if g else 1)*fe/2)} mm입니다.'
            elif i==1:
                L=fo+(-fe if g else fe)
                if L<=0:raise ValueError('갈릴레이식은 대물 초점거리가 접안 초점거리 절댓값보다 커야 합니다.')
                answer=f'현재 '+('갈릴레이식' if g else '케플러식')+f'의 렌즈 간격은 **{fmt(L)} mm**입니다. '+('L=fo−|fe|' if g else 'L=fo+fe')+'로 최종상이 무한대인 조건입니다.'
            else:answer=f'초점거리 비를 유지하고 **대물 구경 D를 늘리면** 더 작은 각도 차이를 분해합니다. 현재 D={fmt(D)} mm에서 Rayleigh 각분해능은 약 {fmt(1.22*w*1e-6/D*206264.806)}초각입니다. 배율을 올리는 것만으로 분해능이 개선되지는 않습니다.'
            assumption+=' 무한대 물체·최종상 무한대, 공기 중 회절 한계이며 대기와 수차는 제외합니다.'
        elif k=='microscope':
            f=positive('microF');t=positive('tube');na=positive('microNA');n=positive('medium');w=positive('wave');finite=enum('microscopeModel',['finite','infinity'])=='finite'
            if na>n:raise ValueError('NA는 매질 굴절률 n을 초과할 수 없습니다.')
            if finite and t<=f:raise ValueError('유한 경통 모델은 상 거리 v>f가 필요합니다.')
            M=t/f-(1 if finite else 0);formula='|M|=ftube/fobj (무한 보정), |M|=v/fobj−1 (유한); dAbbe=λ/(2NA); NA=n sinθ'
            if i==0:answer=('중간상은 **대물렌즈 뒤 '+fmt(t)+' mm**의 상면에 생깁니다.' if finite else '중간상은 **튜브렌즈 뒤 초점거리 '+fmt(t)+' mm**의 후초점면에 생깁니다. 대물렌즈에서 '+fmt(f)+' mm 뒤가 아닙니다.')+f' 시료에 대해 도립이며 중간상 배율의 크기는 {fmt(M)}배입니다.'
            elif i==1:answer=f'중간상 배율 {fmt(M)}배를 두 배로 하려면 대물 초점거리를 **{fmt(t/(2*M+(1 if finite else 0)))} mm**로 바꿉니다. '+('고정한 튜브 입력은 대물에서 상면까지 거리 v입니다.' if finite else '튜브렌즈 초점거리를 고정한 무한 보정 모델입니다.')+' 시료 초점은 새 대물에 맞춰야 합니다.'
            else:answer=f'**확대와 분해능은 다릅니다.** 현재 중간상 배율은 {fmt(M)}배, NA={fmt(na)}에서 Abbe 분해 거리는 **{fmt(w/(2*na))} nm**입니다. NA를 늘리거나 파장을 줄여야 더 작은 구조를 구분하며, 단순 확대는 새 세부 정보를 만들지 않습니다.'
            assumption+=' 근축·이상적 중간상이며 접안 각배율·수차는 제외합니다.'
        elif k=='xrd':
            w=positive('xray');d=positive('spacing');order=positive('order');two=num('scanTwoTheta',0,179.999999);formula='2d sinθ=nλ; d=nλ/[2sin(2θ/2)]; a=d√(h²+k²+l²) (입방정)'
            presets={'Si':(.5430941,'diamond'),'Ge':(.5657820,'diamond'),'Al':(.40495,'fcc'),'Cu':(.3615,'fcc')}
            material=p.get('material','custom');hkl=None
            if material in presets:
                hkl=p.get('plane')
                if not isinstance(hkl,str) or len(hkl)!=3 or not hkl.isdigit() or int(hkl)==0:raise ValueError('유효한 입방 결정면 (hkl)이 필요합니다.')
                indices=list(map(int,hkl));a,structure=presets[material]
                odd=all(c%2 for c in indices);even=all(c%2==0 for c in indices)
                if not (odd or even and (structure=='fcc' or sum(indices)%4==0)):raise ValueError('선택한 결정면은 현재 구조의 이상적 소멸 규칙상 금지 반사입니다.')
                d=a/math.sqrt(sum(c*c for c in indices));order=1
            elif material!='custom':raise ValueError('등록되지 않은 XRD 물질입니다.')
            if not float(order).is_integer():raise ValueError('회절 차수는 양의 정수여야 합니다.')
            if i==0:answer=f'현재 선택 면간격 d={fmt(d)} nm에서 **검출기 2θ={fmt(2*deg(asin(order*w/(2*d))))}°**입니다. θ는 결정면 기준 브래그 각이고 검출기 축은 그 두 배입니다.'
            elif i==1:answer=f'면간격과 차수를 고정하면 파장이 길어질수록 **피크가 큰 2θ 쪽으로 이동**합니다. 현재 λ={fmt(w)} nm입니다. nλ>2d가 되면 실수 브래그 해가 없어집니다.'
            else:
                if two==0:raise ValueError('2θ=0에서는 유한한 면간격을 역산할 수 없습니다.')
                inferred=order*w/(2*math.sin(rad(two/2)));answer=f'현재 스캔 축 2θ={fmt(two)}°를 피크 위치라고 가정하면 **d={fmt(inferred)} nm**입니다. 이 스캔 위치가 실제 피크인지 확인해야 합니다. '
                answer+=(f'입방정 ({hkl})이 지정되어 a={fmt(inferred*math.sqrt(sum(int(c)**2 for c in hkl)))} nm입니다.' if hkl else '입방 결정계와 (hkl)이 지정되지 않아 격자상수 a는 결정할 수 없습니다.')
            assumption+=' 이상적 브래그 위치만 계산하며 피크 세기·폭·물질 동정은 계산하지 않습니다.'
        elif k=='prism':
            A=rad(num('apex',1,89));rotation=rad(num('prismRotation',-10,10));w=positive('wavelength');inc=asin((1.5+.004/.55**2)*math.sin(A/2))+rotation
            def trace(wave):
                n=1.5+.004/(wave/1000)**2;r1=asin(math.sin(inc)/n);r2=A-r1;e=asin(n*math.sin(r2));return n,deg(r1),deg(r2),deg(e),deg(inc+e-A)
            formula='n(λ)=1.50+0.004/λ[µm]²; sin i=n sin r₁; r₁+r₂=A; sin e=n sin r₂; δ=i+e−A'
            n,r1,r2,e,delta=trace(w)
            if i==0:answer=f'현재 λ={fmt(w)} nm에서 입사각 i={fmt(deg(inc))}°, 첫 굴절각 r₁={fmt(r1)}°, 두 번째 내부 입사각 r₂={fmt(r2)}°, 출사 굴절각 e={fmt(e)}°입니다. **편이각 δ={fmt(delta)}°**입니다. 각 면의 각도는 그 면 법선 기준입니다.'
            elif i==1:answer=f'이 정상 분산 모델에서는 **보라가 빨강보다 더 많이 꺾입니다**. 같은 입사 배치에서 400 nm 편이각 {fmt(trace(400)[4])}°, 700 nm는 {fmt(trace(700)[4])}°입니다.'
            else:answer=f'현재 A={fmt(deg(A))}°에서 400–700 nm의 편이각 차이는 {fmt(trace(400)[4]-trace(700)[4])}°입니다. 꼭지각 변경은 두 면 굴절각을 모두 바꾸므로 Snell 법칙으로 재계산합니다. 이 UI는 550 nm 최소 편이 기준 입사각도 함께 바꾸므로 입사각 고정 실험과 구분해야 합니다. 전반사 조건에서는 출사 해가 없습니다.'
            assumption+=' 가상 Cauchy 유리이며 실제 유리 재료값이 아닙니다. 입력 프리즘 회전을 포함합니다.'
        if not answer:raise ValueError('계산 목적이 등록되지 않았습니다.')
        return {**base,'ok':True,'status':'calculated','kind':k,'index':i,'question':CATALOG[k][i],'inputs':p,'answer':answer,'formula':formula,'assumptions':assumption,'source':'optics://documents/'+source}
    except (KeyError,TypeError,ValueError,ZeroDivisionError,OverflowError) as exc:
        return {**base,'message':str(exc),'formula':'입력의 단위·정의역 확인','source':'optics://documents/experiment-intake'}


def format_inquiry(data):
    if not data.get('ok'):return '**계산 조건을 확인해 주세요.** '+data.get('message','입력이 부족합니다.')
    source=data['source'].rsplit('/',1)[-1]
    return data['answer']+'\n\n공식: '+data['formula']+'\n\n'+data['assumptions']+f'\n\n출처: [{source}](/documents/{source}) · MCP 탐구 계산'
