/** 빔스플리터에서 각 거울까지의 기준 편도 거리(mm)와 미동 Δx(µm). */
function michelsonGeometry(v={}) {
 const arm1=Number(v.arm1Distance??100),arm2=Number(v.arm2Distance??100.02);
 const gap=Number(((arm2-arm1)*1000).toFixed(9));
 const displacement=Number(v.displacement??0),currentGap=gap+displacement;
 return {arm1,arm2,currentArm2:arm2+displacement/1000,gap,currentGap,opl:2*currentGap,phaseCycles:2*(currentGap-20)*1000/Number(v.wavelength??532)};
}
if(typeof module!=='undefined')module.exports.michelsonGeometry=michelsonGeometry;

/* 이상적 광학 모델. 모든 길이는 표시 단위에서 SI로 변환한다. */
/**
 * 선택한 가상 실험의 이론값과 AI에 전달할 요약을 계산한다.
 *
 * @param {string} kind - 메뉴의 실험 ID (fresnel, prism, scattering, lens 등).
 * @param {Object} values - 슬라이더 값. 파장 nm, 렌즈 거리 cm 등 화면 단위를 사용한다.
 * @returns {Object} 실험별 수치, 그래프 좌표 및 summary 문자열.
 * 실제 측정·장비 제어는 하지 않는다. 길이 단위 변환은 각 분기에서 수행한다.
 */
function opticsSimulation(kind, values) {
  if(kind==='equipment')return equipmentSimulation(values);
  const {angle, focal, object, wavelength, slit, distance} = values;
  // 밴드 사이 들뜸과 진공 방출은 서로 다른 문턱을 사용한다. 실제 흡수율·수명은 계산하지 않는다.
  if(kind==='absorption') {
    const {absorptionType='semiconductor',threshold=1.5,absorptionWave=532,fermiPosition=.5,electronTemperature=300}=values;
    const energy=1239.841984/absorptionWave;
    const intensity=Math.max(0,Math.min(10,Number(values.intensity??1)));
    const packetCount=Math.round(intensity*3);
    const allowed=energy>=threshold;
    const kinetic=absorptionType==='metal'?Math.max(0,energy-threshold):null;
    const label=values.materialLabel || {semiconductor:'가상 반도체',metal:'가상 금속',insulator:'가상 부도체'}[absorptionType];
    // 페르미 준위는 점유 확률의 기준이다. 밴드갭 안에 실제 허용 상태가 있다는 뜻은 아니다.
    const fermiEnergy=absorptionType==='metal'?0:threshold*fermiPosition;
    const occupation=(e)=>1/(1+Math.exp(Math.max(-700,Math.min(700,(e-fermiEnergy)/(8.617333262e-5*electronTemperature)))));
    const conductionOccupation=occupation(absorptionType==='metal'?0:threshold);
    const valenceOccupation=occupation(0);
    return {energyScene:absorptionEnergyScene(values),intensity,packetCount,emissionCount:absorptionType==='metal'&&energy>threshold?packetCount:0,energy,allowed,kinetic,fermiEnergy,conductionOccupation,valenceOccupation,cutoff:1239.841984/threshold,emits:absorptionType==='metal'&&energy>threshold,
      summary:`광흡수·광전효과 실험: 현재 모드=${absorptionType}, ${absorptionType==='metal'?'금속 표면 밖 진공 방출 모델':'물질 내부 밴드 간 들뜸 모델, 진공 방출을 다루지 않음'}. ${label}, 상대 광자 유입률=${intensity} (표시 광자 묶음 ${packetCount}개, 실제 전류 아님), λ=${absorptionWave} nm, 광자 에너지=${energy.toFixed(3)} eV, ${absorptionType==='metal'?'일함수 Φ':'밴드갭 Eg'}=${threshold} eV, 문턱 파장=${(1239.841984/threshold).toFixed(2)} nm. 점유 확률 참고 모델 T=${electronTemperature} K, EF=${fermiEnergy.toFixed(3)} eV (금속은 EF=0 기준, 비금속은 Ev=0 기준), f(Ec)=${conductionOccupation.toExponential(3)}. 이 확률은 전자 농도·광흡수 확률이 아니다. ${absorptionType==='metal'?`최대 방출 운동에너지=${kinetic.toFixed(3)} eV, ${energy>threshold?'진공 방출 에너지 조건 충족':'양의 운동에너지 방출 조건 미충족'}`:allowed?'이상적인 밴드 간 들뜸 조건 충족. 물질 밖 방출은 의미하지 않음.':'이상적인 밴드 간 들뜸 에너지 부족. 모든 흡수가 없다는 뜻은 아님.'} 입력한 문턱 외의 실제 재료 응답·흡수율·양자효율·전류·전자 수명·간접천이·결함은 모델링하지 않은 학습용 문턱 모델이다.`};
  }
  // 입사면 기준 s/p 반사율: 스넬 법칙으로 굴절각을 얻고 전반사는 별도로 처리한다.
  if (kind === 'fresnel') {
    const {n1=1,n2=1.5,incidence=45}=values;
    const radians=incidence*Math.PI/180;
    const st=n1/n2*Math.sin(radians);
    const tir=st>1;
    const ct=tir?0:Math.sqrt(Math.max(0,1-st*st));
    const ci=Math.cos(radians);
    const rs=n1===n2?0:tir?1:((n1*ci-n2*ct)/(n1*ci+n2*ct))**2;
    const rp=n1===n2?0:tir?1:((n2*ci-n1*ct)/(n2*ci+n1*ct))**2;
    const critical=n1>n2?Math.asin(n2/n1)*180/Math.PI:null;
    const brewster=Math.atan(n2/n1)*180/Math.PI;
    // 그래프는 현재 입사각 한 점이 아니라 0~89.5° 전체의 반사율을 계산한다.
    const curve=(p)=>Array.from({length:180},(_,i)=>{
      const a=i*.5*Math.PI/180, u=n1/n2*Math.sin(a), c=Math.cos(a),t=Math.sqrt(Math.max(0,1-u*u));
      const r=n1===n2?0:u>=1?1:p?((n2*c-n1*t)/(n2*c+n1*t))**2:((n1*c-n2*t)/(n1*c+n2*t))**2;
      return `${i?'L':'M'}${35+i/179*430},${185-150*r}`;
    }).join(' ');
    return {polarization3d:polarizationScene(values),rs,rp,tir,critical,brewster,transmitted:tir?null:Math.asin(Math.min(1,st))*180/Math.PI,sPath:curve(false),pPath:curve(true),summary:`s·p 편광 반사·전반사 실험: λ=${wavelength} nm, 비흡수 유전체 n₁=${n1}, n₂=${n2}, 법선 기준 입사각 ${incidence}°. Rₛ=${rs.toFixed(4)}, Rₚ=${rp.toFixed(4)}, ${tir?'전반사':`굴절각 ${(Math.asin(Math.min(1,st))*180/Math.PI).toFixed(2)}°`}. 브루스터 각 ${brewster.toFixed(2)}°, 임계각 ${critical===null?'없음':critical.toFixed(2)+'°'}. 굴절률은 사용자가 정한 고정값이며 파장 분산·위상·소멸파는 모델에 포함하지 않았다.`};
  }
  // 두 경계의 Snell 법칙. 각도에 따라 화면 분산폭을 재정규화하지 않는다.
  if (kind === 'prism') {
    const {apex=60,prismMode='white'}=values;
    const A=apex*Math.PI/180;
    const refIndex=1.50+.004/.55**2;
    const incoming=Math.asin(refIndex*Math.sin(A/2))+Number(values.prismRotation||0)*Math.PI/180;
    const deviationAt=(index)=>{const r1=Math.asin(Math.sin(incoming)/index);return (incoming+Math.asin(index*Math.sin(A-r1))-A)*180/Math.PI;};
    const colors=['#8a4ab5','#326ed2','#299a68','#dbab27','#cc4c41'];
    const rays=(prismMode==='mono'?[wavelength]:[400,450,530,590,700]).map((lambda,i)=>{
      const index=1.50+.004/(lambda/1000)**2;
      const deviation=deviationAt(index);
      return {lambda,index,deviation,color:prismMode==='mono'?wavelengthColor(lambda):colors[i],endY:100+250*Math.tan(deviation*Math.PI/180)};
    });
    const halfWidth=170*Math.tan(A/2),entryY=145;
    const entryX=240-(entryY-55)*Math.tan(A/2);
    const incidentDirection=A/2-incoming;
    const sourceY=entryY+(20-entryX)*Math.tan(incidentDirection);
    const trace=(lambda)=>{
      const index=1.50+.004/(lambda/1000)**2;
      const r1=Math.asin(Math.sin(incoming)/index),r2=A-r1;
      const exitAngle=Math.asin(index*Math.sin(r2));
      const insideDirection=A/2-r1,outsideDirection=exitAngle-A/2;
      const travel=(240+(entryY-55)*Math.tan(A/2)-entryX)/(Math.cos(insideDirection)-Math.sin(insideDirection)*Math.tan(A/2));
      const exitX=entryX+travel*Math.cos(insideDirection),exitY=entryY+travel*Math.sin(insideDirection);
      const screenY=exitY+(520-exitX)*Math.tan(outsideDirection);
      return {lambda,index,deviation:deviationAt(index),color:wavelengthColor(lambda),exitX,exitY,displayY:screenY,
        entryRefraction:r1*180/Math.PI,exitIncidence:r2*180/Math.PI,exitRefraction:exitAngle*180/Math.PI,
        path:`M${entryX} ${entryY}L${exitX} ${exitY}L520 ${screenY}`};
    };
    const spectrum=Array.from({length:61},(_,i)=>trace(400+i*5));
    for(const ray of rays)Object.assign(ray,trace(ray.lambda));
    const reference=trace(550),exitX=reference.exitX;
    const normal=(x,y,d)=>`M${x-35*Math.cos(d)} ${y-35*Math.sin(d)}L${x+35*Math.cos(d)} ${y+35*Math.sin(d)}`;
    const entryNormal=normal(entryX,entryY,A/2),exitNormal=normal(reference.exitX,reference.exitY,-A/2);
    const reflectedDirection=Math.PI+A/2+incoming;
    const reflectionPath=`M${entryX} ${entryY}L${entryX+65*Math.cos(reflectedDirection)} ${entryY+65*Math.sin(reflectedDirection)}`;
    return {sourceY,entryY,entryNormal,exitNormal,reflectionPath,incomingAngle:incoming*180/Math.PI,reference,prismPoints:`240,55 ${240-halfWidth},225 ${240+halfWidth},225`,entryX,exitX,spectrum,rays,spread:rays.length>1?rays[0].deviation-rays[rays.length-1].deviation:0,summary:`프리즘 분산 실험: ${prismMode==='mono'?'단색광 '+wavelength+' nm':'백색광의 대표 5개 파장'}, 꼭지각 A=${apex}°, 가상 Cauchy 굴절률 n(λ)=1.50+0.004/λ[µm]². 550 nm 최소 편이 기준에서 프리즘 회전 ${Number(values.prismRotation||0)}°를 더한 입사각으로 두 면 Snell 법칙 계산. ${rays.map(r=>`${r.lambda} nm: n=${r.index.toFixed(4)}, δ=${r.deviation.toFixed(3)}°`).join('; ')}. 분산을 설명해줘. 실제 유리나 특정 입사 배치의 정밀 예측은 아니다.`};
  }
  // 산란 계수의 상대비와 직접광 감쇠를 구한다. 측면 검출 세기와 혼동하지 않는다.
  if (kind === 'scattering') {
    const {opticalDepth=.2}=values;
    const ratio=(550/wavelength)**4;
    const transmission=Math.exp(-opticalDepth*ratio);
    const points=Array.from({length:101},(_,i)=>{
      const lambda=380+i*3.7;
      return `${i?'L':'M'}${35+i/100*430},${185-150*(380/lambda)**4}`;
    }).join(' ');
    return {ratio,transmission,path:points,blueRed:(700/450)**4,summary:`레일리 산란 학습 모델: λ=${wavelength} nm, 550 nm 기준 광학 두께 τ=${opticalDepth}. 산란 계수 비 (550/λ)^4=${ratio.toFixed(3)}, 직접광 투과율 exp[−τ(550/λ)^4]=${transmission.toFixed(4)}. 450 nm와 700 nm의 산란 계수 비=${((700/450)**4).toFixed(3)}. 하늘이 파란 이유와 노을을 설명해줘. 단일 산란·상대 계수 모델이며 실제 하늘 색이나 관측 산란광 밝기를 계산하지 않는다.`};
  }
  if (kind === 'polarization') {
    const ratio = Math.cos(angle * Math.PI / 180) ** 2;
    return {ratio, summary: `편광 실험 (이상적 선편광·분석기), λ=${wavelength} nm (파장 의존성 생략): 상대각 ${angle}°, 입사 세기 I₀ 기준 I/I₀=${ratio.toFixed(4)} (${(ratio*100).toFixed(2)}%). 파장 의존성은 생략한 이상적 모델이다.`};
  }
  // arcsin의 정의역을 먼저 검사한다. 조건 불충족을 0° 피크로 표현하면 안 된다.
  if (kind === 'xrd') {
    const {xray=0.15406,spacing:manualSpacing=0.3,order=1,material='custom',plane='111'}=values;
    const preset=xrdMaterials().find(m=>m.id===material);
    const indices=plane.split('').map(Number);
    const allowed=!preset || xrdAllowed(indices,preset.structure);
    const spacing=preset?preset.a/Math.hypot(...indices):manualSpacing;
    const actualOrder=preset?1:order;
    const ratio=actualOrder*xray/(2*spacing);
    const theta=allowed && ratio<=1?Math.asin(ratio)*180/Math.PI:null;
    const twoTheta=theta===null?null:2*theta;
    const peaks=preset?xrdPeaks(preset,xray):[];
    const sample=preset?`${preset.name} (${preset.structure}), a=${preset.a} nm, (${plane})`:'수동 면간격 모드: 결정구조·격자상수 a·결정면(hkl)은 미지정, d만 직접 설정';
    const scanTwoTheta=Number(values.scanTwoTheta??twoTheta??30);
    const angularError=twoTheta===null?null:scanTwoTheta-twoTheta;
    return {scanTwoTheta,angularError,theta,twoTheta,spacing,preset,allowed,peaks,summary:`XRD 브래그 법칙: ${sample}, 현재 스캔 2θ=${scanTwoTheta.toFixed(3)}°, 선택 반사와의 각도 차이=${angularError===null?'정의되지 않음':angularError.toFixed(3)+'°'}, 파장 λ=${xray} nm, d=${spacing.toFixed(6)} nm, n=${actualOrder}. ${!allowed?'이상적 결정의 소멸 규칙상 금지 반사.':theta===null?'nλ>2d이므로 해가 없음.':`θ=${theta.toFixed(3)}°, 2θ=${twoTheta.toFixed(3)}°.`} ${peaks.length?'가능한 분말 반사 위치: '+peaks.map(p=>`(${p.hkl}) ${p.twoTheta.toFixed(3)}°`).join(', '):''} 근사 격자상수를 고정한 이상적 분말 피크 위치 계산이며 세기·폭·실제 단결정 웨이퍼의 측정 피크는 예측하지 않는다.`};
  }
  if (kind === 'michelson') {
    const {displacement=0, visibility=1,mirrorTiltX=0,mirrorTiltY=0}=values;
    const cycles=2*displacement*1000/wavelength;
    const geometry=michelsonGeometry(values);
    const phase=2*Math.PI*geometry.phaseCycles;
    const intensity=(1+visibility*Math.cos(phase))/2;
    // 등경사 간섭의 유효 팔 길이 차이를 20 µm + Δx로 두고, f=100 mm 초점면을 본다.
    // I(r)=(1+V cos[4πt cos(θ)/λ−φ_ref])/2. 각 반경의 세기를 직접 칠해 알파 중첩을 피한다.
    const baseGap=geometry.gap, focalMm=100, radiusMm=30;
    const phaseAt=(r)=>4*Math.PI*(baseGap+displacement)*1000/wavelength*Math.cos(Math.atan(r*radiusMm/focalMm))-4*Math.PI*20*1000/wavelength;
    // 거울 기울기는 반사광 각도를 약 2배 바꾼다. mrad→rad, 화면 mm→nm.
    const tilted=mirrorTiltX!==0||mirrorTiltY!==0;
    const field=(x,y)=>(1+visibility*Math.cos(phaseAt(Math.hypot(x,y))+4*Math.PI*1e6/wavelength*(mirrorTiltX*.001*x*radiusMm+mirrorTiltY*.001*y*radiusMm)))/2;
    let fringeImage='';
    if(tilted){
      const size=100;let pixels='';
      for(let y=0;y<size;y++)for(let x=0;x<size;x++){
        const nx=(x+.5-size/2)/(size/2),ny=(y+.5-size/2)/(size/2);
        if(nx*nx+ny*ny>1)continue;
        pixels+=`<rect x="${x}" y="${y}" width="1" height="1" fill="${wavelengthColor(wavelength,field(nx,ny))}"/>`;
      }
      fringeImage='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><filter id="soft"><feGaussianBlur stdDeviation=".25"/></filter></defs><rect width="100" height="100" fill="#0d1822"/><g filter="url(#soft)">${pixels}</g></svg>`);
    }
    const radial=Array.from({length:601},(_,i)=>{
      const value=(1+visibility*Math.cos(phaseAt(i/600)))/2;
      const channel=Math.round(255*value);
      return {offset:i/6,gray:channel,intensity:value,color:wavelengthColor(wavelength,value)};
    });
    const profile=Array.from({length:301},(_,i)=>{
      const r=Math.abs(i-150)/150;
      const value=field((i-150)/150,0);
      return `${i?'L':'M'}${30+i/300*440},${110-value*85}`;
    }).join(' ');
    return {geometry,phaseCycles:geometry.phaseCycles,cycles,intensity,radial,profile,fringeImage,tilted,completed:Math.floor(cycles+1e-9),fraction:cycles-Math.floor(cycles),summary:`Michelson 간섭계: 공기 근사, λ=${wavelength} nm, 기준 위치 대비 거울 이동 Δx=${displacement} µm. 광경로 변화 2Δx=${2*displacement} µm, 무늬 이동 N=${cycles.toFixed(4)}주기, 관찰점 정규화 세기=${intensity.toFixed(4)}, 가시도 V=${visibility}, M₂ 거울 기울기 X=${mirrorTiltX} mrad, Y=${mirrorTiltY} mrad. 각도에 따른 화면 선형 위상을 합산한다. 빔스플리터→M₁ 거리 L₁=${geometry.arm1} mm, 빔스플리터→M₂ 기준 거리 L₂=${geometry.arm2} mm. 현재 편도 거리 차이=${geometry.currentGap} µm, 왕복 광로차=${geometry.opl} µm. 무늬는 등경사 모델로 편도 차이 (L₂−L₁)+Δx, 관찰 렌즈 f=100 mm, 반경 30 mm, 기준점 위상 보정을 가정한다. 이상적 위상 단면의 요약이며 공간 빔 겹침은 별첨 현장 조절 모델을 따른다. 광원의 결맞음 길이·파면 수차는 생략했다.`};
  }
  if (['lens','concave-lens','concave-mirror','convex-mirror'].includes(kind)) {
    const mirror=kind.includes('mirror');
    const diverging=['concave-lens','convex-mirror'].includes(kind);
    // 발산 계열은 음의 초점거리. 거울·렌즈의 화면 방향은 장치도에서 따로 변환한다.
    const signedF=diverging?-focal:focal;
    const name={lens:'볼록렌즈','concave-lens':'오목렌즈','concave-mirror':'오목거울','convex-mirror':'볼록거울'}[kind];
    // s=f일 때 유한한 상이 없으므로 null을 사용해 무한대·NaN의 화면 출력을 막는다.
    const image = Math.abs(object-signedF)<1e-8 ? null : signedF*object/(object-signedF);
    const magnification = image === null ? null : -image/object;
    return {image, magnification, signedF, mirror, name, summary: `${name} 실험 (근축 근사, λ=${wavelength} nm, 색수차·재료 분산 생략): f=${signedF} cm, 물체 거리 s=${object} cm. ${image === null ? '물체가 초점에 있어 유한한 위치에 상이 맺히지 않음.' : `상 거리 s′=${image.toFixed(2)} cm, 배율 M=${magnification.toFixed(2)}, ${image>0?'도립 실상':'정립 허상'}.`} 이 결과를 설명해줘.`};
  }
  // 단일·이중슬릿의 유한 폭 회절 포락선: 첫 최소 사이 전체 폭과 sinc² 세기 곡선을 계산한다.
  const double=values.slitMode==='double',separation=Number(values.slitSeparation??.3);
  const width = 2*wavelength*1e-9*distance/(slit*1e-3)*1000;
  const points = Array.from({length:241},(_,i)=>{
    const x=(i-120)/120*20; // 스크린 중심에서 mm
    const theta=Math.atan(x/1000/distance);
    // 스크린 위치 mm를 m로 바꾸고, 각도에 따른 위상 인자를 구한다.
    const beta=Math.PI*(slit*1e-3)*Math.sin(theta)/(wavelength*1e-9);
    const envelope=Math.abs(beta)<1e-10?1:(Math.sin(beta)/beta)**2;
    const intensity=envelope*(double?Math.cos(Math.PI*separation*1e-3*Math.sin(theta)/(wavelength*1e-9))**2:1);
    return {x,intensity};
  });
  return {width,fringeSpacing:double?wavelength*1e-6*distance*1000/separation:null,points,path:points.map((p,i)=>`${i?'L':'M'}${30+(p.x+20)/40*440},${190-p.intensity*155}`).join(' '),summary:`${double?'이중슬릿 간섭·유한 폭 회절':'단일슬릿 회절'} (이상적 원거리·작은 각도 근사): ${double?'슬릿 중심 간격 d='+separation+' mm, 간섭 간격 Δy≈'+(wavelength*.001*distance/separation).toFixed(4)+' mm, ':''}파장 ${wavelength} nm, 슬릿 폭 ${slit} mm, 스크린 거리 ${distance} m. 중앙 최대 전체 폭 W≈${width.toFixed(3)} mm. 이 결과와 조건 변경 효과를 설명해줘.`};
}
if (typeof module !== 'undefined') module.exports = {opticsSimulation,michelsonGeometry};

/* 자체 생성한 SVG 장치 개념도. 사용자 문자열은 삽입하지 않는다. */
/**
 * 실험기구 배치와 광경로를 보여주는 자체 SVG 개념도를 만든다.
 *
 * @param {string} kind - 장치도를 지원하는 실험 ID.
 * @param {Object} v - 현재 슬라이더 값. 문자열 입력은 SVG에 직접 넣지 않는다.
 * @param {Object} result - opticsSimulation에서 계산한 수치.
 * @returns {string} SVG 마크업. 장치도를 제공하지 않는 실험은 빈 문자열.
 * 광선 간격·거울 이동 등은 가독성을 위해 확대할 수 있으며 기구 도면이 아니다.
 */
function opticsApparatus(kind, v, result) {
  if(result?.equipment)return result.apparatus;
  const num=(value)=>Number.isFinite(Number(value))?Number(value):0;
  const line=(x1,y1,x2,y2,color='#efbc52',width=3,extra='')=>`<line x1="${num(x1)}" y1="${num(y1)}" x2="${num(x2)}" y2="${num(y2)}" stroke="${color}" stroke-width="${width}" ${extra}/>`;
  const text=(x,y,s)=>`<text x="${x}" y="${y}">${s}</text>`;
  const box=(x,y,w,h,label)=>`<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="4" fill="url(#metal)" stroke="#647f95"/>${text(x+w/2,y+h/2+4,label)}`;
  const base=`<defs><linearGradient id="metal" x2="0" y2="1"><stop stop-color="#f1f7fb"/><stop offset=".5" stop-color="#c4d3df"/><stop offset="1" stop-color="#e6eef4"/></linearGradient><pattern id="bench" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="11" cy="11" r="1.2" fill="#b6c7d5"/></pattern></defs><rect width="600" height="330" fill="#f5f9fc"/><rect x="14" y="38" width="572" height="267" rx="7" fill="url(#bench)" stroke="#c5d5df"/>`;
  let body='';
  if(kind==='michelson') {
    const mirrorX=410+num(v.displacement)*24;
    const tiltDisplay=18*Math.tanh(num(v.mirrorTiltX)*2); // 실제 미세 기울기를 시각적으로 확대한다.
    body=text(300,22,'MICHELSON / 광학 테이블 평면도')+
      box(35,144,92,42,'LASER')+line(127,165,275,165)+
      line(275,165,mirrorX,165,'#d97a52',3)+line(mirrorX,172,275,172,'#e9ab73',2,'stroke-dasharray="5 3"')+
      line(275,165,275,75,'#399bc4',3)+line(281,75,281,165,'#399bc4',2,'stroke-dasharray="5 3"')+
      line(275,172,275,258,'#69a783',4)+
      `<rect x="256" y="145" width="39" height="39" fill="#b9e4f1" fill-opacity=".55" stroke="#4187a1"/>`+
      line(258,182,292,148,'#337b9c',3)+line(247,72,303,72,'#547187',7)+
      `<g data-michelson-mirror="true" role="slider" tabindex="0" aria-label="이동 거울 M2 좌우 조절" aria-valuenow="${num(v.displacement)}" aria-valuemin="0" aria-valuemax="5" style="cursor:ew-resize;touch-action:none"><rect x="${mirrorX-15}" y="128" width="30" height="76" fill="transparent"/>`+`<g transform="rotate(${tiltDisplay} ${mirrorX} 165)">`+line(mirrorX,138,mirrorX,194,'#547187',7)+`</g>`+`</g>`+
      box(mirrorX-32,209,66,20,'미동대')+line(mirrorX,194,mirrorX,209,'#7e92a3',2)+
      (result.practicalSnapshot?.detectorImage?`<rect x="237" y="257" width="77" height="35" fill="#102434"/><image x="257" y="258" width="34" height="34" href="${result.practicalSnapshot.detectorImage}"/>`:(`<defs><radialGradient id="michelson-device-fringes">${result.radial.map(s=>`<stop offset="${s.offset}%" stop-color="${s.color}"/>`).join('')}</radialGradient></defs><rect x="237" y="257" width="77" height="35" rx="3" fill="#142e3e" stroke="#7897a8"/><circle cx="276" cy="274" r="16" fill="url(#michelson-device-fringes)"/>`+
      (result.fringeImage?`<image x="260" y="258" width="32" height="32" href="${result.fringeImage}"/>`:'')))+
      text(183,134,'빔스플리터 50/50')+text(277,57,'기준 거울 M₁')+text(474,120,'M₂ · 좌우 드래그')+text(365,239,`Δx = ${num(v.displacement).toFixed(2)} µm`)+text(361,275,'스크린 / 검출기')+text(145,218,'실선: 진행 · 점선: 복귀')+text(300,322,'위치·X 기울기는 확대 표시 · Y 기울기는 평면 밖 회전');
  } else if(kind==='xrd') {
    // 대칭 θ–2θ 배치: 시료면은 수평, 광원과 검출기 팔이 각각 θ로 배치된다.
    const theta=num(result.scanTwoTheta)/2,rad=theta*Math.PI/180;
    const sourceX=300-150*Math.cos(rad),sourceY=190-150*Math.sin(rad);
    const detX=300+150*Math.cos(rad),detY=sourceY;
    body=text(300,22,'XRD / 대칭 θ–2θ 고니오미터')+
      `<path d="M100 190A200 160 0 0 1 500 190" fill="none" stroke="#9cb3c4" stroke-dasharray="4 5"/>`+
      line(sourceX,sourceY,300,190,'#b67ab3',3)+line(300,190,detX,detY,result.theta===null?'#aaa':'#d6944b',3,result.theta===null?'stroke-dasharray="5 4"':'')+
      box(sourceX-40,sourceY-19,80,38,'X선 광원')+`<g data-xrd-detector="true" role="slider" tabindex="0" aria-label="검출각 2세타 조절" aria-valuenow="${result.scanTwoTheta}" aria-valuemin="0" aria-valuemax="180" style="cursor:grab;touch-action:none">`+box(detX-37,detY-19,74,38,'검출기 ↔')+`</g>`+
      box(260,230,80,26,'회전 스테이지')+line(300,201,300,230,'#758ea1',6)+
      `<g>`+[0,1,2,3].map(i=>line(250,186+i*(6+num(v.spacing)*9),350,186+i*(6+num(v.spacing)*9),'#488ba7',2)).join('')+`</g>`+
      text(300,282,'결정 시료 · 평행한 결정면')+text(216,164,'θ')+text(385,164,'θ')+text(300,60,`현재 검출각 2θ = ${num(result.scanTwoTheta).toFixed(2)}°`)+text(300,322,'검출기 드래그: 대칭 θ–2θ 연동 · 이론 각도와 현재 각도는 별개');
  } else if(kind==='fresnel') {
    const rad=num(v.incidence)*Math.PI/180;
    const sx=300-135*Math.sin(rad),sy=170-135*Math.cos(rad);
    const rx=300+135*Math.sin(rad),ry=sy;
    const tr=num(result.transmitted)*Math.PI/180;
    body=text(300,22,'FRESNEL / 평면 매질 블록과 각도계')+
      `<rect x="85" y="170" width="430" height="115" rx="4" fill="#afd7e8" fill-opacity=".6" stroke="#679cb4"/><circle cx="300" cy="170" r="110" fill="none" stroke="#9cb4c3"/>`+
      line(300,40,300,285,'#7e92a3',1,'stroke-dasharray="5 4"')+
      line(sx,sy,300,170,'#e2a43f',4)+line(300,170,rx,ry,'#c96b59',2+4*num((result.rs+result.rp)/2))+
      (result.tir?'':line(300,170,300+95*Math.sin(tr),170+95*Math.cos(tr),'#318fb7',3))+
      box(sx-34,sy-15,68,30,'광원')+box(rx-20,ry-25,60,24,'검출기 R')+
      text(146,154,`n₁ = ${num(v.n1).toFixed(2)}`)+text(150,202,`n₂ = ${num(v.n2).toFixed(2)}`)+text(420,265,result.tir?'전반사: 전파 투과광 없음':'굴절광')+
      text(300,312,`입사면 = 화면 / s: 화면에 수직 ⊙ / p: 화면 안 ↔`);
  } else if(kind==='prism') {
    body=text(300,22,'PRISM / 슬릿 · 콜리메이터 · 프리즘 · 스크린')+
      box(26,136,70,42,v.prismMode==='mono'?'단색 광원':'백색 광원')+line(96,157,270,157,v.prismMode==='mono'?wavelengthColor(v.wavelength):'#d2b96e',6)+
      line(127,124,127,150,'#566f83',5)+line(127,164,127,193,'#566f83',5)+text(128,217,'입구 슬릿')+
      `<ellipse cx="191" cy="157" rx="8" ry="40" fill="#b5dceb" stroke="#518ca8"/>`+text(190,100,'콜리메이터')+
      `<path d="M306 85L226 223.56H386Z" fill="#b8dfec" fill-opacity=".7" stroke="#4d8ca7" stroke-width="2"/>`+
      box(267,230,82,19,'회전 테이블')+text(306,274,`A = ${num(v.apex)}°`)+
      `<rect x="529" y="104" width="12" height="152" fill="#fafbff" stroke="#819bad"/>`+
      (v.prismMode==='mono'?result.rays:result.spectrum).map(r=>{const y=r.displayY;return `<path d="M310 156L535 ${y-1.2}L535 ${y+1.2}L310 159Z" fill="${r.color}" opacity=".65"/>`+line(531,y,539,y,r.color,3);}).join('')+
      text(457,76,v.prismMode==='mono'?'단색광: 하나의 색':'백색광 → 연속 스펙트럼')+text(484,270,'빨강 위 / 보라 아래')+
      text(518,88,'스크린')+text(438,286,'색별 분리 간격 확대 · 각도 실척 아님')+text(300,322,'내부 경로는 생략한 장치 개념도 / 550 nm 기준 고정 입사각');
  } else if(kind==='scattering') {
    const t=num(result.transmission),strength=Math.min(.85,.12+num(v.opticalDepth)*.3);
    body=text(300,22,'SCATTERING / 산란 셀과 두 방향 검출')+
      box(25,142,75,40,'단색 광원')+line(100,162,186,162,'#e0b44c',5)+
      `<rect x="188" y="94" width="200" height="134" rx="5" fill="#d0e9f3" fill-opacity=".5" stroke="#6c9ab1"/>`+
      Array.from({length:24},(_,i)=>`<circle cx="${201+(i*47)%174}" cy="${109+(i*31)%100}" r="2.5" fill="#8ab1c7" opacity="${strength}"/>`).join('')+
      line(188,162,388,162,'#d4af54',4)+line(388,162,470,162,'#d4af54',4,`opacity="${Math.max(.03,t)}"`)+
      line(288,162,288,62,'#4b9fc9',3,`opacity="${strength}" stroke-dasharray="4 3"`)+
      box(461,142,106,40,'직접광 검출기')+box(242,43,92,30,'90° 검출기')+
      text(288,253,'산란 셀 / 희박한 미세 산란체')+text(450,216,`T = ${(t*100).toFixed(1)}%`)+
      text(300,283,`선택 파장 ${num(v.wavelength)} nm · 광학 두께 ${num(v.opticalDepth).toFixed(2)}`)+text(300,322,'측면 광선은 방향 표시: 90° 검출 세기를 정량 예측하지 않음');
  } else return '';
  return `<svg viewBox="0 0 600 340" role="img" aria-label="실험 장치와 광경로 개념도">${base}${body}</svg>`;
}
if (typeof module !== 'undefined') module.exports.opticsApparatus=opticsApparatus;

/** 실온 부근 문헌값을 반올림한 학습용 입방 결정 프리셋. a의 단위는 nm. */
function xrdMaterials() {
  return [
    {id:'Si',name:'실리콘 Si',structure:'diamond',a:.5430941},
    {id:'Ge',name:'게르마늄 Ge',structure:'diamond',a:.5657820},
    {id:'Al',name:'알루미늄 Al',structure:'fcc',a:.40495},
    {id:'Cu',name:'구리 Cu',structure:'fcc',a:.3615},
  ];
}
/** FCC는 모두 홀수/모두 짝수, diamond의 모두 짝수는 h+k+l=4m도 만족해야 한다. */
function xrdAllowed(hkl,structure) {
  if(hkl.length!==3 || !hkl.some(n=>n>0) || hkl.some(n=>!Number.isInteger(n)||n<0))return false;
  const odd=hkl.every(n=>n%2===1),even=hkl.every(n=>n%2===0);
  return odd || (even && (structure==='fcc' || hkl.reduce((a,b)=>a+b,0)%4===0));
}
/** h,k,l≤5의 반사 위치를 계산한다. 같은 d의 반사는 한 대표 표기로 묶고 세기는 계산하지 않는다. */
function xrdPeaks(material,wavelength) {
  const peaks=[],seen=new Set();
  for(let h=1;h<=5;h++)for(let k=0;k<=h;k++)for(let l=0;l<=k;l++) {
    if(!xrdAllowed([h,k,l],material.structure))continue;
    const q=h*h+k*k+l*l;if(seen.has(q))continue;seen.add(q);
    const spacing=material.a/Math.sqrt(q),r=wavelength/(2*spacing);
    if(r<=1)peaks.push({hkl:`${h}${k}${l}`,spacing,twoTheta:2*Math.asin(r)*180/Math.PI});
  }
  return peaks.sort((a,b)=>a.twoTheta-b.twoTheta);
}
if(typeof module!=='undefined')Object.assign(module.exports,{xrdMaterials,xrdAllowed,xrdPeaks});

/** 가시광 파장을 설명용 RGB로 변환한다. 디스플레이 색은 실측 색도·시감도를 뜻하지 않는다. */
function wavelengthColor(lambda,intensity=1) {
  let r=0,g=0,b=0;
  if(lambda<440){r=(440-lambda)/60;b=1;}
  else if(lambda<490){g=(lambda-440)/50;b=1;}
  else if(lambda<510){g=1;b=(510-lambda)/20;}
  else if(lambda<580){r=(lambda-510)/70;g=1;}
  else if(lambda<645){r=1;g=(645-lambda)/65;}
  else r=1;
  return `rgb(${[r,g,b].map(c=>Math.round(Math.max(0,Math.min(1,c))*255*Math.max(0,Math.min(1,intensity)))).join(',')})`;
}
if(typeof module!=='undefined')module.exports.wavelengthColor=wavelengthColor;

/** 근축·회절 한계 기반 교육 모델. 실제 제조사 광학 설계는 재현하지 않는다. */
function equipmentSimulation(v={}) {
  const type=v.equipmentType||'camera';
  if(!['camera','telescope','microscope'].includes(type))throw new Error('지원하지 않는 광학장비입니다.');
  const defaults={f:50,u:1000,sensor:36,fNumber:4,objective:500,eyepiece:25,diameter:80,microF:4,tube:200,microNA:.65,medium:1,wave:550};
  const p={telescopeModel:'kepler',microscopeModel:'infinity',...defaults,...v};
  const fmt=(x)=>Number.isFinite(x)?Number(x.toFixed(4)):null;
  const metrics=[],hints=[];let title,detail,solution='';
  if(type==='camera') {
    title='카메라 · 얇은 렌즈';const image=p.u>p.f?p.f*p.u/(p.u-p.f):null;
    metrics.push(['상 거리',image,'mm'],['횡배율',image===null?null:-image/p.u,'배'],['수평 화각',2*Math.atan(p.sensor/(2*p.f))*180/Math.PI,'°']);
    detail=`초점거리 f=${p.f} mm, 물체 거리 u=${p.u} mm, 센서 폭=${p.sensor} mm, F수=${p.fNumber}. 1/f=1/u+1/v, m=-v/u. 물체는 실상 조건 u>f 필요. 센서는 계산된 상면에 둔다. |m|=f/(u−f)이므로 u 고정·0<f<u에서 f를 늘리면 |m|가 증가한다. 센서도 새 상면 v로 이동해야 한다.`;
    hints.push('피사체 폭 200 mm를 센서에 꽉 채우려면 물체 거리는 몇 mm여야 해?','회절 무늬 지름을 센서에서 5 μm 이하로 하려면 F수는 얼마 이하여야 해?');
  } else if(type==='telescope') {
    const g=p.telescopeModel==='galilean';title=g?'망원경 · 갈릴레이식':'망원경 · 케플러식';metrics.push(['각배율',(g?1:-1)*p.objective/p.eyepiece,'배'],['경통 길이',p.objective+(g?-1:1)*p.eyepiece,'mm']);
    detail=`대물렌즈 f_o=${p.objective} mm, 접안렌즈 f_e=${p.eyepiece} mm, 대물 구경 D=${p.diameter} mm, 진공 파장=${p.wave} nm. 무한대 물체·최종상 무한대·공기·이상적인 ${p.telescopeModel==='galilean'?'갈릴레이식, 오목 접안렌즈, 정립상. L=f_o−|f_e|':'케플러식, 볼록 접안렌즈, 도립상. L=f_o+f_e'}. |각배율|=f_o/|f_e|.`;
    hints.push('목표 각배율 40배에 필요한 접안렌즈 초점거리는?','1초각의 두 점을 구분하려면 대물렌즈 구경이 몇 mm 이상이어야 해?');
  } else if(type==='microscope') {
    title=p.microscopeModel==='finite'?'현미경 · 유한 경통':'현미경 · 무한 보정';metrics.push(['대물 배율',p.microscopeModel==='finite'?p.tube/p.microF-1:p.tube/p.microF,'배'],['Abbe 분해 거리',p.wave/(2*p.microNA),'nm']);
    detail=`대물렌즈 초점거리=${p.microF} mm, 튜브렌즈 초점거리=${p.tube} mm, 대물 NA=${p.microNA}, 매질 n=${p.medium}, 진공 파장=${p.wave} nm. ${p.microscopeModel==='finite'?'튜브 입력은 대물에서 상면까지 거리 v. 얇은 렌즈의 |M|=v/f_obj−1.':'중간상 배율 M=f_tube/f_obj.'} 분해능은 Abbe d=λ/(2NA). 배율은 접안렌즈 각배율을 포함하지 않는다.`;
    hints.push('목표 분해 거리 300 nm에 필요한 NA와 수광 반각은?','중간상 배율 80배를 만들려면 대물렌즈 초점거리는?');
  }
  const q=String(v.question||'');
  const number=(unit)=>{const m=q.match(new RegExp('(\\d+(?:\\.\\d+)?)\\s*(?:'+unit+')','i'));return m?Number(m[1]):null;};
  const targetNm=number('nm|나노미터');const targetUm=number('μm|µm|um|마이크로미터');const targetM=number('배');
  if(q && type==='camera') {
    if(/피사체|물체.*폭/.test(q)&&number('mm')>0) {const w=number('mm');solution=`목표 물체 폭 W=${w} mm. 센서 폭 S=${p.sensor} mm에 채우려면 |m|=S/W, u=f(1+W/S)=${fmt(p.f*(1+w/p.sensor))} mm, v=f(1+S/W)=${fmt(p.f*(1+p.sensor/w))} mm. 근축·평면 물체 가정.`;}
    else if(/회절|airy|에어리/i.test(q)&&(targetUm||targetNm)>0) {const d=targetUm||targetNm/1000;solution=`Airy 첫 영점 지름 d=2.44λF수. d≤${d} μm에 필요한 F수≤${fmt(d/(2.44*p.wave/1000))}. 현재 파장 ${p.wave} nm. 유한 배율의 유효 F수·수차는 생략.`;}
  } else if(q && type==='telescope') {
    if(/초각/.test(q)&&number('초각')>0){const a=number('초각');solution=`Rayleigh 각분해능 θ=1.22λ/D. 목표 ${a}초각에서 D≥${fmt(1.22*p.wave*1e-6/(a*Math.PI/(180*3600)))} mm. 대기·수차·검출 조건 생략.`;}
    else if(targetM>0)solution=`|M|=f_o/f_e. 목표 ${targetM}배에서 f_e=${fmt(p.objective/targetM)} mm, 무한대 초점 경통 길이=${fmt(p.objective+(p.telescopeModel==='galilean'?-1:1)*p.objective/targetM)} mm. 상은 ${p.telescopeModel==='galilean'?'정립':'도립'}.`;
  } else if(q && type==='microscope') {
    if(/분해|해상|NA|개구수/i.test(q)&&targetNm>0){const na=p.wave/(2*targetNm);solution=`Abbe d=λ/(2NA). 목표 d=${targetNm} nm에서 NA≥${fmt(na)}. ${na>p.medium?'현재 매질 n='+p.medium+'에서 NA>n이므로 이 조건은 불가능.':`현재 n=${p.medium}에서 최소 수광 반각 θ=${fmt(Math.asin(na/p.medium)*180/Math.PI)}°. NA는 n sinθ.`}`;}
    else if(targetM>0)solution=`${p.microscopeModel==='finite'?'튜브 입력은 대물에서 상면까지 거리 v. 얇은 렌즈의 |M|=v/f_obj−1.':'중간상 배율 M=f_tube/f_obj.'} 목표 ${targetM}배에 필요한 f_obj=${fmt(p.tube/(targetM+(p.microscopeModel==='finite'?1:0)))} mm. ${p.microscopeModel==='finite'?'유한 상 거리 v를 고정한 계산.':'무한 보정 튜브렌즈 모델.'} 대물렌즈 교체 시 NA·수차·보정 호환성은 별도 확인.`;
  }
  const instrument=type==='camera'?null:instrumentScene(p,type);
  return {instrumentGeometry:instrument?.geometry,equipment:true,type,title,metrics:metrics.map(([label,value,unit])=>({label,value:fmt(value),unit})),hints,solution,apparatus:type==='camera'?cameraScene(p):instrument.svg,summary:`${title}. ${detail} 기본 계산: ${metrics.map(([label,value,unit])=>`${label}=${fmt(value)??'유효하지 않음'} ${unit}`).join('; ')}. ${solution?'질문에 대한 수식 계산 검산: '+solution:''} 사용자가 요청한 파생값은 가정·단위·식을 밝히고 계산하세요. 정보가 부족하면 필요한 값만 질문하세요. 모든 역산은 이상 모델이며 실제 장비 설정 권고가 아닙니다.`};
}

/** 회전 가능한 직교 투영: 입사면 xy, 경계면 xz, s축 z. */
function polarizationScene({n1=1,n2=1.5,incidence=45,polMode='both',viewYaw=-30,viewTilt=25,polPhase=0}={}) {
 const a=incidence*Math.PI/180,yaw=viewYaw*Math.PI/180,tilt=viewTilt*Math.PI/180;
 const project=([x,y,z])=>{const X=x*Math.cos(yaw)+z*Math.sin(yaw),Z=-x*Math.sin(yaw)+z*Math.cos(yaw);return [300+X,215-y*Math.cos(tilt)+Z*Math.sin(tilt)];};
 const point=v=>project(v).map(x=>x.toFixed(2)).join(',');
 const line=(a,b,c,w=2,dash='')=>`<path d="M${point(a)}L${point(b)}" stroke="${c}" stroke-width="${w}" fill="none" ${dash?'stroke-dasharray="5 4"':''}/>`;
 const text=(v,t,c='#dceafa')=>{const [x,y]=project(v);return `<text x="${x}" y="${y}" fill="${c}" font-size="12" style="fill:${c};font-size:12px">${t}</text>`;};
 const ki=[Math.sin(a),-Math.cos(a),0],kr=[Math.sin(a),Math.cos(a),0],mul=(v,t)=>v.map(x=>x*t);
 const polygon=(vs,c)=>`<polygon points="${vs.map(point).join(' ')}" fill="${c}" fill-opacity=".18" stroke="${c}"/>`;
 let body=polygon([[-220,0,-110],[220,0,-110],[220,0,110],[-220,0,110]],'#88c5da')+polygon([[-190,0,0],[-190,175,0],[190,175,0],[190,0,0]],'#cfb4e9');
 body+=line([0,-130,0],[0,180,0],'#c3cfde',1,true)+text([0,185,0],'법선 n̂');
 body+=line(mul(ki,-185),[0,0,0],'#ffe093',4)+line([0,0,0],mul(kr,180),'#ffe093',3);
 body+=text(mul(ki,-185),'입사광 k →')+text(mul(kr,175),'반사광 →');
 const st=n1/n2*Math.sin(a),tir=st>1,ci=Math.cos(a),ct=tir?0:Math.sqrt(Math.max(0,1-st*st));
 const kt=tir?null:[st,-ct,0];
 if(kt)body+=line([0,0,0],mul(kt,140),'#8ce0d4',3)+text(mul(kt,145),'굴절·투과광 →');
 else body+=text([60,-100,0],'전반사: 전파하는 굴절파 없음');
 // p 기저를 각 진행 벡터에 수직으로 잡고, 같은 기저 규약의 Fresnel 전기장 계수를 적용한다.
 const wave=(k,E,begin,end,coefficient,color)=>{
   if(Math.abs(coefficient)<1e-8)return '';
   let path='';for(let i=0;i<=100;i++){const t=begin+(end-begin)*i/100,amp=22*coefficient*Math.sin(t*.13-polPhase);const v=mul(k,t).map((x,j)=>x+E[j]*amp);path+=`${i?'L':'M'}${point(v)}`;}
   return `<path d="${path}" fill="none" stroke="${color}" stroke-width="2.5"/>`;
 };
 for(const mode of ['s','p'])if(polMode==='both'||polMode===mode) {
   const color=mode==='s'?'#54c6ff':'#ff9c80';
   const basis=k=>mode==='s'?[0,0,1]:[-k[1],k[0],0];
   const denominator=mode==='s'?n1*ci+n2*ct:n2*ci+n1*ct;
   const r=tir?1:n1===n2?0:mode==='s'?(n1*ci-n2*ct)/denominator:(n2*ci-n1*ct)/denominator;
   const t=tir?0:n1===n2?1:2*n1*ci/denominator;
   body+=wave(ki,basis(ki),-180,-8,1,color)+wave(kr,basis(kr),8,170,r,color);
   if(kt)body+=wave(kt,basis(kt),8,130,t,color);
   for(const [k,distance,coefficient] of [[ki,-85,1],[kr,90,r],...(kt?[[kt,80,t]]:[])]){
     if(Math.abs(coefficient)<1e-8)continue;
     const center=mul(k,distance),E=basis(k),tip=center.map((x,j)=>x+E[j]*32*coefficient);
     body+=line(center,tip,color,3)+text(tip,mode==='s'?'Es ⟂ 입사면':'Ep ∥ 입사면',color);
   }
 }
 body+=text([-200,140,0],'입사면: k와 법선을 포함', '#dfc5fa')+text([-170,0,105],'물질 경계면','#a8dbea');
 return `<svg class="sim-svg polarization-3d" viewBox="0 0 600 430" role="img" aria-label="회전형 3차원 s p 편광 전기장 방향"><rect width="600" height="430" rx="8" fill="#14283e"/>${body}<text x="20" y="28" style="fill:white;font-size:12px">파랑 s: 입사면 밖 / 주황 p: 입사면 안 · 둘 다 E ⟂ k</text><text x="20" y="405" style="fill:#d4e4f1;font-size:12px">진폭: 전기장 Fresnel 계수 · 전반사 위상차·소멸파 생략</text></svg>`;
}

/** 공개 원리 기반 장비 단면. 부품 배치·반사 횟수·길이는 실제 설계와 다르다. */

/** 동일 물체 평면을 센서 크기로 잘라 보여주는 근축 카메라 모델. */
function cameraScene(p) {
 const image=p.u>p.f?p.f*p.u/(p.u-p.f):null;
 if(image===null)return '<svg class="sim-svg" viewBox="0 0 760 160"><text x="25" y="70">물체 거리가 초점거리보다 커야 실상을 표시할 수 있습니다.</text></svg>';
 const coverage=p.sensor*p.u/image,scale=700/coverage,sensorHalf=p.sensor*1.1;
 const relativeLight=16/(p.fNumber*p.fNumber);
 const darkness=relativeLight<1?1-relativeLight:0;
 const lightWash=relativeLight>1?Math.min(.9,1-1/relativeLight):0;
 const opening=42/p.fNumber;
 const diameter=p.f/p.fNumber;
 const txt=(x,y,t,size=15)=>`<text x="${x}" y="${y}" style="fill:#d8e8f8;font-size:${size}px;text-anchor:start">${t}</text>`;
 const span=45+Math.min(65,coverage/12),aperture=Math.max(3,Math.min(32,p.f/p.fNumber*.5));
 const world=Array.from({length:41},(_,i)=>{const x=(i-20)*100;return `<path d="M${x} -120V120" stroke="#9fc8d8" stroke-width=".8"/><path d="M${x-25} 55V-15H${x+25}V55Z" fill="${i%2?'#cf855b':'#668f9c'}"/><path d="M${x-35} -15L${x} -55L${x+35} -15Z" fill="#435d79"/><rect x="${x-5}" y="25" width="10" height="30" fill="#e1d1aa"/><circle cx="${x+38}" cy="5" r="12" fill="#5c967d"/><path d="M${x+38} 15V55" stroke="#8b775f" stroke-width="4"/>`;}).join('');
 return `<svg class="sim-svg camera-preview" viewBox="0 0 760 585" role="img" aria-label="센서 가로 길이에 연동되는 촬영 범위와 사진 미리보기">
 <defs><clipPath id="camera-crop"><rect x="30" y="285" width="700" height="225" rx="5"/></clipPath></defs>
 <rect width="760" height="585" rx="10" fill="#13293e"/>${txt(25,30,'카메라 · 센서를 넓히면 같은 위치에서 더 넓게 담깁니다',19)}
 <circle cx="690" cy="122" r="48" fill="#708293" stroke="#bbd0e0" stroke-width="2"/>
 <circle cx="690" cy="122" r="${opening}" fill="#f4d787"/>
 ${Array.from({length:6},(_,i)=>{const a=i*Math.PI/3;return `<path d="M${690+opening*Math.cos(a)} ${122+opening*Math.sin(a)}L${690+46*Math.cos(a+.7)} ${122+46*Math.sin(a+.7)}" stroke="#334d64" stroke-width="2"/>`;}).join('')}
 ${txt(592,60,'조리개 정면 · f/'+p.fNumber,15)}
 ${txt(560,193,'구멍 지름 D = '+diameter.toFixed(2)+' mm',13)}
 <path d="M100 ${145-span}L390 145L630 ${145-sensorHalf}V${145+sensorHalf}L390 145L100 ${145+span}Z" fill="#78c7ea" opacity=".17"/>
 <path d="M100 ${145-span}L390 145L630 ${145+sensorHalf}M100 ${145+span}L390 145L630 ${145-sensorHalf}" stroke="#8dcfe8" stroke-width="2" fill="none"/>
 <path d="M100 ${145-span}V${145+span}" stroke="#e6b98a" stroke-width="5"/>
 <ellipse cx="390" cy="145" rx="12" ry="58" fill="#a3d6ee" fill-opacity=".4" stroke="#a3d6ee"/>
 <path d="M390 85V${145-aperture}M390 ${145+aperture}V205" stroke="#728a9a" stroke-width="8"/>
 <path d="M630 ${145-sensorHalf}V${145+sensorHalf}" stroke="#ffc976" stroke-width="9"/>
 ${txt(35,230,'피사체 평면')}${txt(325,230,'렌즈 / 조리개')}${txt(570,230,'센서 '+p.sensor+' mm')}
 ${txt(30,266,'사진 미리보기 · 같은 건물/눈금, 촬영되는 범위만 변경',16)}
 <g clip-path="url(#camera-crop)"><rect x="30" y="285" width="700" height="225" fill="#c5e3ee"/>
 <g transform="translate(380 393) scale(${scale})"><rect x="-25000" y="55" width="50000" height="5000" fill="#8ead8c"/>${world}<path d="M-25000 55H25000" stroke="#456e67" stroke-width="2"/></g>
 <rect x="30" y="285" width="700" height="225" fill="black" opacity="${darkness}"/><rect x="30" y="285" width="700" height="225" fill="white" opacity="${lightWash}"/>
 <path d="M370 393H390M380 383V403" stroke="white" stroke-width="1"/></g>
 <rect x="30" y="285" width="700" height="225" fill="none" stroke="#89aac3"/>
 ${txt(30,538,'촬영 폭 '+coverage.toFixed(1)+' mm · f/4 대비 빛 '+relativeLight.toFixed(3)+'배 · '+(Math.log2(relativeLight)).toFixed(2)+' EV',15)}
 ${txt(30,565,'F수=f/D · 값이 작으면 구멍이 커져 밝아짐 · 고정 노출, 밝기/과노출 표현은 개념 예시',12)}
 </svg>`;
}

/** 에너지 예산과 공간 이동을 분리한다. 내부 전자의 초과 에너지 배분은 예측하지 않는다. */
function absorptionEnergyScene(v) {
 const E=1239.841984/v.absorptionWave,T=v.threshold,metal=v.absorptionType==='metal';
 const allowed=metal?E>T:E>=T,progress=Math.max(0,Math.min(1,v.absorptionProgress||0));
 const max=Math.max(E,T,1)*1.25,y=e=>265-180*e/max;
 const lift=allowed?Math.max(0,Math.min(1,(progress-.3)/.5)):0;
 const electronEnergy=metal?E*lift:T*lift;
 const shortage=Math.max(0,T-E),excess=Math.max(0,E-T);
 const text=(x,y,t,size=13,color='#dceafa')=>`<text x="${x}" y="${y}" style="fill:${color};font-size:${size}px;text-anchor:start">${t}</text>`;
 const photonX=35+Math.min(1,progress/.3)*110;
 const electronX=metal&&allowed?470+Math.max(0,(progress-.5)/.5)*130:470;
 const ticks=Array.from({length:5},(_,i)=>{const e=max*i/4;return `<path d="M45 ${y(e)}H300" stroke="#34516b"/>${text(8,y(e)+4,e.toFixed(1),10)}`;}).join('');
 return `<svg class="sim-svg absorption-energy-scene" viewBox="0 0 680 420" role="img" aria-label="물질 문턱과 광자 에너지를 비교하는 전자 들뜸 실험">
 <rect width="680" height="420" rx="8" fill="#14283e"/>${text(20,28,'왼쪽: 에너지(eV) / 오른쪽: 물질 내부·외부',17)}
 ${ticks}<path d="M45 65V265" stroke="#96b2c8"/>
 <path d="M55 ${y(T)}H300" stroke="#a3c3e7" stroke-width="3"/>${text(60,y(T)-9,(metal?'진공 준위 Evac':'전도대 바닥 Ec')+' = '+T.toFixed(3)+' eV',12)}
 <path d="M55 265H300" stroke="#75b8de" stroke-width="4"/>${text(60,288,metal?'EF = 0 기준':'가전자대 꼭대기 Ev = 0',12)}
 <path d="M95 265V${y(E)}" stroke="#f2cd76" stroke-width="7"/>${text(110,y(E)+5,'광자 '+E.toFixed(3)+' eV',12,'#f2cd76')}
 <circle cx="260" cy="${y(electronEnergy)}" r="8" fill="#61caff" stroke="white"/>
 ${text(60,312,allowed?(metal?'문턱 초과: Kmax = '+excess.toFixed(3)+' eV':'문턱 충족: 전자·정공 생성의 에너지 조건'):'에너지 부족: '+shortage.toFixed(3)+' eV',12)}
 <rect x="370" y="92" width="160" height="180" rx="5" fill="#294d68" stroke="#6f9dbd"/>
 <path d="M530 75V285" stroke="#b4d3e8" stroke-width="3"/>${text(378,77,'물질 내부')}${text(542,77,'물질 밖 / 진공')}
 <path d="M325 185H445" stroke="#f2cd76" stroke-dasharray="4 5"/>
 ${progress>0&&progress<.32?`<circle cx="${photonX+300}" cy="185" r="6" fill="#f2cd76"/>`:''}
 <circle cx="${electronX}" cy="${metal?185:230-lift*100}" r="8" fill="#61caff" stroke="white"/>
 ${metal?'<rect x="622" y="130" width="7" height="110" fill="#87abc3"/>':`<path d="M400 230H515M400 130H515" stroke="#8aaeca" stroke-width="3"/>${lift>0?'<circle cx="470" cy="230" r="8" fill="none" stroke="#e6a779" stroke-dasharray="3 3"/>':''}`}
 ${text(370,310,metal?(allowed?'표면 밖 방출의 에너지 조건 충족':'단일 광자 방출 불가'):'내부 들뜸 ≠ 진공 방출',12)}
 ${text(20,347,metal?'남는 에너지 = 방출 전자의 최대 운동에너지':'초과 에너지 E−Eg = '+excess.toFixed(3)+' eV: 전자·정공 운동에너지 등에 분배',12)}
 ${text(20,375,'세로축 자동 확대: 에너지 상한 아님 · 파란 점=전자 · 노란색=광자',11)}
 ${text(20,399,'시간·입자 수·이동 거리는 개념 표시. 실제 흡수율·직접/간접 전이율·수명은 예측하지 않음.',11)}
 </svg>`;
}

/** 근축 광선의 렌즈 교차점을 같은 구경 좌표로 계산한다. 축 방향은 화면에 맞춰 축척한다. */
function instrumentScene(p,type) {
 const telescope=type==='telescope',galilean=p.telescopeModel==='galilean',finite=p.microscopeModel==='finite';
 const title=telescope?(galilean?'굴절망원경 · 갈릴레이식':'굴절망원경 · 케플러식'):(finite?'광학현미경 · 유한 경통':'광학현미경 · 무한 보정');
 const txt=(x,y,t)=>`<text x="${x}" y="${y}" style="fill:#355774;font:13px Arial,sans-serif;text-anchor:middle">${t}</text>`;
 const line=(pts,c,dash=false)=>`<polyline points="${pts.map(([x,y])=>`${x},${y}`).join(' ')}" fill="none" stroke="${c}" stroke-width="2" ${dash?'stroke-dasharray="4 4"':''}/>`;
 const lens=(x,h,id,concave=false)=>concave?`<path data-optic="${id}" d="M${x-8} ${155-h}Q${x+1} 155 ${x-8} ${155+h}H${x+8}Q${x-1} 155 ${x+8} ${155-h}Z" fill="#c8e5f2" stroke="#537f9f"/>`:`<ellipse data-optic="${id}" cx="${x}" cy="155" rx="9" ry="${h}" fill="#c8e5f2" stroke="#537f9f"/>`;
 let body='',geometry={};
 if(telescope){
  const H=p.diameter*.23,rayH=H*.8,fo=p.objective,fe=p.eyepiece,L=(galilean?fo-fe:fo+fe)+Number(p.eyepieceOffset||0);
  const x1=150,x2=x1+330*L/(fo+fe),focus=x1+330*fo/(fo+fe),outH=rayH*fe/fo;
  // 접안렌즈의 표시 크기는 고정한다. 지원 범위의 최대 출사 광선 높이(44.16)를 수용한다.
  const eyepieceH=52;geometry={objectiveRadius:H+8,rayRadius:rayH,eyepieceRadius:eyepieceH,outRadius:outH};
  body+=`<rect x="${x1}" y="${155-H-15}" width="${x2-x1}" height="${2*H+30}" rx="7" fill="#e7edf3" stroke="#c0cdd7"/>`;
  for(const sign of [-1,0,1]){const y=155+sign*rayH,out=155+sign*rayH*(1-L/fo),slope=-sign*rayH/fo-(out-155)/(galilean?-fe:fe),end=out+slope*(570-x2)*(fo+fe)/330;body+=line([[25,y],[x1,y],[x2,out],...(Math.abs(out-155)<=eyepieceH?[[570,end]]:[])],sign===0?'#dda757':'#5489b5');if(galilean)body+=line([[x2,out],[focus,155]],'#9b7fa8',true);}
  body+=lens(x1,H+8,'objective')+lens(x2,eyepieceH,'eyepiece',galilean)+`<circle cx="${focus}" cy="155" r="4" fill="#b69262"/>`;
  body+=txt(150,60,'大物 구경 D = '+p.diameter+' mm').replace('大物','대물')+txt(x1,270,'대물: 볼록렌즈')+txt(x2,292,galilean?'접안: 오목렌즈':'접안: 볼록렌즈')+txt(390,45,galilean?'정립상 · 내부 실상 없음':'도립상 · 두 렌즈 사이 실상')+txt(330,328,'대물 구경: 집광 폭 변화 · 접안렌즈 크기 고정 · 렌즈 크기는 개념 축척');
 }else{
  const h=18+42*p.microNA/p.medium,rayH=h*.82,x1=180;
  // 각 구간은 별도 축척이다. 시료를 초점 조건에 자동 배치하며 같은
  // 시료 높이를 유지해 f_obj와 f_tube 변경에 따른 상 크기를 비교한다.
  const magnification=finite?p.tube/p.microF-1:p.tube/p.microF;
  const objectDistance=finite?p.microF*p.tube/(p.tube-p.microF):p.microF;
  const objectX=x1-3*objectDistance,x2=330,imageX=finite?300+.65*p.tube:x2+.6*p.tube;
  const objectH=.5,imageH=objectH*magnification,imageY=155+imageH;
  geometry={objectiveRadius:h,rayRadius:rayH,magnification,objectDistance,imageX,imageHeight:imageH};
  body+=`<rect x="${objectX-22}" y="197" width="44" height="12" fill="#899dac"/><path d="M${objectX} 197V${155-objectH}" stroke="#b98362" stroke-width="3"/><circle cx="${objectX}" cy="${155-objectH}" r="3" fill="#c56c43"/>`;
  for(const sign of [-1,0,1]){
   const y=155+sign*rayH;
   // 무한 보정 구간의 광선은 서로 평행하고 튜브렌즈 뒤에서 한 점에 모인다.
   const tubeY=y+imageH*80/p.tube;
   body+=finite?line([[objectX,155-objectH],[x1,y],[imageX,imageY]],'#5489b5'):line([[objectX,155-objectH],[x1,y],[x2,tubeY],[imageX,imageY]],'#5489b5');
  }
  body+=lens(x1,h,'objective')+(finite?'':lens(x2,h+65,'tube'))+`<path d="M${imageX} 80V240" stroke="#8b9eb0" stroke-width="3"/><path data-image-height="${imageH}" d="M${imageX} 155V${imageY}l-5 -7m5 7 5 -7" fill="none" stroke="#c56c43" stroke-width="3"/>`;
  body+=txt(objectX,245,'시료')+txt(x1,270,'대물 f = '+p.microF+' mm')+txt(finite?410:x2,58,finite?'대물이 직접 실상 형성':'튜브렌즈 f = '+p.tube+' mm')+txt(imageX,260,'중간상 '+magnification.toFixed(1)+'배')+txt(330,302,'주황색: 같은 시료의 도립 중간상 · 시료 위치는 초점 조건에 자동 배치')+txt(330,328,'구간별 축척이 다름 · 초점거리를 바꿔 중간상 크기와 광선 비교');
 }
 return {geometry,svg:`<svg class="sim-svg instrument-scene" viewBox="0 0 600 350" role="img" aria-label="${title} 장치와 유효 구경 광선"><rect width="600" height="350" rx="8" fill="#f2f6fa"/>${txt(300,24,title)}<path d="M20 155H580" stroke="#b1c0cf" stroke-dasharray="5 5"/>${body}</svg>`};
}

/** 실험 조절 항목. 이상적 이론 그래프와 구분되는 검출/정렬 학습 모델이다. */
function opticsPracticalControls(kind,metal=false){
 const c=(key,label,min,max,step,value,unit='')=>({key,label,min,max,step,value,unit});
 const focus=[c('screen','스크린 위치',1,100,.1,15,'cm'),c('aperture','유효 구경',.2,4,.1,1,'cm')];
 const map={
 michelson:[c('arm1Distance','빔스플리터 → M₁ 거울 거리',99.9,100.1,.0001,100,'mm'),c('arm2Distance','빔스플리터 → M₂ 거울 거리 · 기준',99.9,100.1,.0001,100.02,'mm'),c('beamX','귀환빔 위치 보정 X',-8,8,.05,0,'mm'),c('beamY','귀환빔 위치 보정 Y',-8,8,.05,0,'mm'),c('waist1','M₁ 빔 반경',1,4,.1,2,'mm'),c('waist2','M₂ 빔 반경',1,4,.1,2,'mm'),c('balance','M₂ / M₁ 광량',.05,1,.01,1)],
 polarization:[c('axisError','분석기 영점 오차',-15,15,.1,0,'°'),c('leak','교차 편광판 누설 비율',0,.1,.001,0)],
 diffraction:[c('beamOffset','슬릿에 대한 입사빔 중심',-.4,.4,.005,0,'mm'),c('steering','입사 빔 조향각',-5,5,.05,0,'mrad'),c('background','검출기 배경광',0,.15,.005,0)],
 xrd:[c('zero','검출각 영점 오차',-1.5,1.5,.01,0,'°'),c('height','시료 높이 오차',-1,1,.01,0,'mm'),c('acceptance','검출 각도 허용폭 σ',.05,1,.01,.2,'°')],
 fresnel:[c('zero','입사각 눈금 영점 오차',-3,3,.05,0,'°'),c('mixing','p축에서 벗어난 편광축',0,90,.5,0,'°')],
 prism:[c('rotation','프리즘 회전 · 기준 입사 대비',-5,5,.1,0,'°'),c('detectorOffset','스크린 수직 위치 보정',-30,30,.5,0,'mm')],
 camera:[c('screen','센서의 렌즈 뒤 위치',1,1100,.1,52.6,'mm')],
 telescope:[c('eyepieceOffset','접안렌즈 위치 오차',-20,20,.1,0,'mm'),c('pupilOffset','눈의 출사동공 중심 이탈',-6,6,.05,0,'mm')],
 microscope:[c('sampleDefocus','시료 상하 미동',-8,8,.05,0,'µm')],
 absorption:metal?[c('retarding','수집 전극의 저지 전압',0,10,.01,0,'V')]:[c('thickness','시료 두께',.1,10,.1,1,'µm'),c('alpha','가상 흡수계수 α',.05,2,.05,.5,'µm⁻¹')]
 };
 if(['concave-lens','convex-mirror'].includes(kind))return [c('eyeDistance','눈과 광학소자 거리',5,80,.5,20,'cm'),c('eyeOffset','눈의 광축 이탈',-4,4,.05,0,'cm'),c('aperture','유효 구경',.2,4,.1,1,'cm')];
 return map[kind]||focus;
}

/** 표준 근축식·Gaussian 빔 합성·검출기 수용각을 이용한 실습 화면.
 * 표시 크기/색/초점 흐림은 학습용 축척이며 실제 장비 예측은 아니다.
 */
let michelsonPaintCache=null;
function opticsPractical(kind,p,r,settings={}){
 const defaults=Object.fromEntries(opticsPracticalControls(kind,p.absorptionType==='metal').map(c=>[c.key,c.value]));
 const s={...defaults,...settings}, metrics=[],f=x=>Number(x.toFixed(4));
 const txt=(x,y,t,size=13)=>`<text x="${x}" y="${y}" fill="#dceaf5" font-size="${size}" text-anchor="middle" style="fill:#dceaf5;font:${size}px Arial,sans-serif;text-anchor:middle">${t}</text>`;
 const line=(x1,y1,x2,y2,color='#75b8dc',width=2)=>`<path d="M${x1} ${y1}L${x2} ${y2}" stroke="${color}" stroke-width="${width}" fill="none"/>`;
 let body='',note='',state={},title='검출 화면',height=260,detectorImage='';
 const bar=(label,value,y,color='#74c8df')=>txt(125,y+14,label,12)+`<rect x="235" y="${y}" width="300" height="17" fill="#294052"/><rect x="235" y="${y}" width="${300*Math.max(0,Math.min(1,value))}" height="17" fill="${color}"/>`+txt(385,y+38,(value*100).toFixed(1)+'%',12);
 const trace=(fn,max=1)=>Array.from({length:241},(_,i)=>`${i?'L':'M'}${40+i*520/240},${210-150*fn(i/240)/max}`).join(' ');
 if(kind==='michelson'){
  // M₂ 회전은 반사각을 2배 바꾸고, 1m 유효 전파 뒤 빔 중심도 이동시킨다.
  const dx=s.beamX+2*Number(p.mirrorTiltX||0),dy=s.beamY+2*Number(p.mirrorTiltY||0);
  const w1=s.waist1,w2=s.waist2,sep=Math.hypot(dx,dy),overlap=2*w1*w2/(w1*w1+w2*w2)*Math.exp(-sep*sep/(w1*w1+w2*w2));
  const geometry=michelsonGeometry({...p,...s});
  // 이전 저장 입력은 호환하되 새 화면에서는 두 거리로부터 차이를 계산한다.
  if(settings.armDifference!==undefined){geometry.gap=Number(settings.armDifference);geometry.currentGap=geometry.gap+Number(p.displacement||0);geometry.opl=2*geometry.currentGap;geometry.phaseCycles=2*(geometry.currentGap-20)*1000/p.wavelength;}
  const mode=s.view||'interference';
  const extent=mode==='alignment'?12:4,n=mode==='alignment'?96:192,pitch=2*extent/n,k=2*Math.PI/(p.wavelength/1e6),tx=Number(p.mirrorTiltX||0)*.002,ty=Number(p.mirrorTiltY||0)*.002;
  const sinc=x=>Math.abs(x)<1e-10?1:Math.sin(x)/x;
  const pixelAverage=sinc(k*tx*pitch/2)*sinc(k*ty*pitch/2),groups={};
  const paintKey=JSON.stringify([mode,dx,dy,w1,w2,s.balance,p.wavelength,mode==='alignment'?0:geometry.phaseCycles,p.displacement,geometry.currentGap,tx,ty,p.visibility]);
  let raster;
  if(michelsonPaintCache?.key===paintKey){raster=michelsonPaintCache.raster;detectorImage=michelsonPaintCache.image;}else{
  for(let iy=0;iy<n;iy++)for(let ix=0;ix<n;ix++){
   const x=(ix+.5)/n*2*extent-extent,y=(iy+.5)/n*2*extent-extent;
   const a=Math.exp(-2*(x*x+y*y)/(w1*w1)),b=s.balance*Math.exp(-2*((x-dx)**2+(y-dy)**2)/(w2*w2));
   let color;
   if(mode==='alignment')color=`rgb(${Math.round(255*Math.sqrt(b))},${Math.round(220*Math.sqrt(Math.max(a,b)))},${Math.round(255*Math.sqrt(a))})`;
   else{
    const phase=2*Math.PI*geometry.phaseCycles+k*(tx*x+ty*y)+4*Math.PI*geometry.currentGap*1e3/p.wavelength*(Math.cos(Math.atan(Math.hypot(x,y)/10))-1);
    const v=Math.max(0,(a+b+2*Number(p.visibility??1)*Math.sqrt(a*b)*pixelAverage*Math.cos(phase))/4);
    const level=Math.round(Math.sqrt(Math.min(1,v))*63)/63;color=wavelengthColor(p.wavelength,level);
   }
   (groups[color]??=[]).push(`M${ix} ${iy}h1v1h-1z`);
  }
  raster=Object.entries(groups).map(([color,path])=>`<path shape-rendering="crispEdges" fill="${color}" d="${path.join('')}"/>`).join('');
  detectorImage='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${n} ${n}">${raster}</svg>`);
  michelsonPaintCache={key:paintKey,raster,image:detectorImage};
  }
  const cx=300,cy=178,scale=11;
  body+=`<svg x="168" y="46" width="264" height="264" viewBox="0 0 ${n} ${n}">${raster}</svg>`;
  if(mode==='alignment')body+=line(cx-7,cy,cx+7,cy,'#71e8ff')+line(cx,cy-7,cx,cy+7,'#71e8ff')+line(cx+dx*scale-7,cy+dy*scale,cx+dx*scale+7,cy+dy*scale,'#ffd090')+line(cx+dx*scale,cy+dy*scale-7,cx+dx*scale,cy+dy*scale+7,'#ffd090');
  if(mode==='alignment')body+=`<circle data-return-beam="true" cx="${cx+dx*scale}" cy="${cy+dy*scale}" r="15" fill="transparent" tabindex="0" role="button" aria-label="M₂ 귀환빔. 끌거나 방향키로 위치 보정" style="cursor:grab"/>`;
  if(mode==='alignment')body+=txt(92,120,'M₁ 기준빔',14)+txt(92,143,'청록색 경로',12)+txt(512,120,'M₂ 귀환빔',14)+txt(512,143,'주황색 경로',12);
  else body+=txt(80,120,'합성광',14)+txt(520,120,`${p.wavelength} nm`,14);
  body+=txt(300,338,mode==='alignment'?'화면 범위 ±12 mm · 색은 경로 구분용':'간섭 관측 확대 · 화면 범위 ±4 mm',12);
  state={beamSeparation:sep,beamDX:dx,beamDY:dy,overlap,pixelAverage,geometry,observationExtent:extent,observationFocal:10};height=360;title=mode==='alignment'?'두 귀환빔 정렬':'겹친 영역의 간섭';
  metrics.push(['M₁까지 편도 거리',geometry.arm1,'mm'],['M₂까지 현재 편도 거리',geometry.currentArm2,'mm'],['두 거리 차이 · M₂−M₁',geometry.currentGap,'µm'],['왕복 광로차 · 공기 근사',geometry.opl,'µm'],['두 빔 중심 간격',sep,'mm'],['위치·빔 폭 겹침 지표',overlap*100,'%']);
  note='기본 화면은 두 귀환빔이 겹친 원형 간섭무늬입니다. 정렬 확인 모드에서는 두 광점의 중심과 폭을 맞춥니다. 위치 보정은 조향 거울쌍의 효과, M₂ 각도는 방향·빔 중심을 함께 바꿉니다. 같은 중심이어도 각도·폭·광량이 다르면 무늬가 달라집니다. 거울 변위는 밝고 어두운 고리를 이동시키고 M₂ 기울기는 위상 기울기와 빔 중심을 함께 바꿉니다. 관측 렌즈 f=10 mm, 두 거울까지 거리 차이 (L₂−L₁)+Δx의 등경사 위상을 Gaussian 빔에 합성한 교육 모델입니다. 정렬 화면 ±12 mm와 간섭 확대 화면 ±4 mm의 배율이 다릅니다.';
 }else if(['lens','concave-lens','concave-mirror','convex-mirror','camera','microscope'].includes(kind)){
  let image=r.image,aperture=s.aperture,screen=s.screen,unit='cm';
  if(kind==='camera'){image=p.u>p.f?p.f*p.u/(p.u-p.f):null;aperture=p.f/p.fNumber;unit='mm';}
  if(kind==='microscope'){
   const finite=p.microscopeModel==='finite',base=finite?p.microF*p.tube/(p.tube-p.microF):p.microF;
   const u=base+s.sampleDefocus/1000,q=1/u-1/p.microF,a=1+80*q;
   image=finite?-1/q:-a/(q-a/p.tube);screen=p.tube;aperture=2*p.microF*p.microNA/p.medium*(finite?1:Math.abs(a));unit='mm';
  }
  if(Number.isFinite(image)&&image<0&&s.eyeDistance!==undefined){
   const radius=s.aperture/2*(1+s.eyeDistance/Math.abs(image)),visible=Math.abs(s.eyeOffset)<radius;
   const angular=Math.abs(r.magnification)/(s.eyeDistance+Math.abs(image));
   body=`<rect x="160" y="45" width="280" height="170" fill="#050b12" stroke="#6489a2"/>`+(visible?`<text x="300" y="145" text-anchor="middle" fill="#d9f4ff" font-family="serif" font-size="${Math.max(15,Math.min(110,angular*2200))}" style="fill:#d9f4ff;font:${Math.max(15,Math.min(110,angular*2200))}px Georgia,serif">F</text>`:txt(300,130,'눈이 출사 광선 다발을 벗어남',16));
   state={image,real:false,visible,angular};title='눈의 위치를 옮겨 허상 보기';metrics.push([kind==='concave-lens'?'렌즈의 물체 쪽 허상 거리':'거울 뒤 허상 거리',Math.abs(image),'cm'],['눈에서의 각크기 · 표식 높이 1 cm',angular*1000,'mrad']);
   note='허상은 눈으로 볼 수 있지만 스크린에 직접 받을 수 없습니다. 눈을 광축 밖으로 옮기면 유한 구경을 통과한 광선 다발을 놓칩니다. F는 정립 허상이며 크기는 각크기의 확대 표시입니다.';
  }else{
  const real=Number.isFinite(image)&&image>0,blur=real?Math.abs(aperture*(1-screen/image)):null;
  const blurPx=real?Math.min(20,blur*(kind==='microscope'?5:kind==='camera'?6:16)):0;
  body+=`<defs><filter id="focus-practice-${kind}" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="${blurPx}"/></filter></defs><rect x="160" y="45" width="280" height="170" fill="#050b12" stroke="#6489a2"/>`;
  body+=real?`<g filter="url(#focus-practice-${kind})"><text x="300" y="130" text-anchor="middle" dominant-baseline="middle" fill="#d9f4ff" font-size="92" font-family="serif" style="fill:#d9f4ff;font:92px Georgia,serif" transform="rotate(180 300 130)">F</text></g>`:txt(300,132,'무늬가 맺히는 실상면 없음',17);
  title=kind==='microscope'?'시료 미동에 따른 고정 중간상면':'스크린·센서의 초점 맞추기';
  metrics.push(['고정 검출면 위치',screen,unit]);if(real)metrics.push(['현재 선명한 상면',image,unit],['기하학적 흐림 원 지름',blur,unit]);
  state={image,screen,blur,real};note='실상면과 검출면이 일치하면 기하학적 흐림이 줄어듭니다. 허상은 스크린으로 받을 수 없습니다. F는 초점 확인 표식이며 표시 흐림은 확대 축척입니다. 수차·회절 PSF는 포함하지 않습니다.';
  }
 }else if(kind==='polarization'){
  const actual=p.angle+s.axisError,signal=s.leak+(1-s.leak)*Math.cos(actual*Math.PI/180)**2;
  body=bar('분석기 투과광',signal,70)+txt(300,180,'눈금 각도와 실제 투과축 차이를 조절해 소광을 찾아보세요.');state={actualAngle:actual,signal};metrics.push(['실제 두 축 상대각',actual,'°'],['검출 세기 비',signal,'']);note='누설 비율은 유한 소광비를 모사하는 입력입니다. 이상적 말뤼스 그래프와 실제 조절 검출값을 구분합니다.';
 }else if(kind==='diffraction'){
  const double=p.slitMode==='double',d=Number(p.slitSeparation??.3),a=p.slit,w=double?.5:.12,steps=200;
  const power=offset=>{let sum=0;for(let i=0;i<steps;i++){const x=offset-a/2+(i+.5)*a/steps;sum+=Math.exp(-2*(x-s.beamOffset)**2/w**2)*a/steps/(w*Math.sqrt(Math.PI/2));}return sum;};
  const left=power(double?-d/2:0),right=double?power(d/2):0,transmitted=left+right;
  const center=p.distance*s.steering,fn=x=>{
    const theta=Math.atan((x-center)/(1000*p.distance)),beta=Math.PI*a*Math.sin(theta)/(p.wavelength*1e-6);
    const envelope=Math.abs(beta)<1e-8?1:(Math.sin(beta)/beta)**2;
    const phase=2*Math.PI*d*Math.sin(theta)/(p.wavelength*1e-6);
    return envelope*(double?(left+right+2*Math.sqrt(left*right)*Math.cos(phase))/2:left)+s.background;
  };
  // 정면에서 보는 관찰 스크린. 가로축은 검출 위치, 세로축은 긴 슬릿 방향이다.
  const strips=Array.from({length:1200},(_,i)=>{const x=(i+.5)/1200*40-20;return `<rect x="${50+i*500/1200}" y="65" width="${500/1200+.02}" height="150" fill="${wavelengthColor(p.wavelength,Math.sqrt(Math.min(1,Math.max(0,fn(x)))))}"/>`;}).join('');
  body=`<rect x="48" y="63" width="504" height="154" fill="#000" stroke="#7896a9"/>`+strips+txt(50,238,'−20 mm',12)+txt(300,238,'0',12)+txt(550,238,'+20 mm',12);
  state={transmitted,center,left,right};metrics.push(['슬릿 통과 광량',transmitted*100,'%'],['무늬 중심 이동',center,'mm']);
  if(double)metrics.push(['간섭무늬 간격',p.wavelength*.001*p.distance/d,'mm']);
  title=double?'이중슬릿 · 스크린 정면의 간섭무늬':'단일슬릿 · 스크린 정면의 회절무늬';
  note='스크린을 빛이 도달하는 관찰면에서 정면으로 본 화면입니다. 세로 줄은 긴 슬릿의 방향이며 가로 밝기만 계산합니다. '+(double?'유한 슬릿 폭의 회절 포락선 안에 두 슬릿의 간섭무늬가 생깁니다. 두 슬릿의 조명 불균형은 대비를 낮춥니다.':'중앙 밝은 띠와 양쪽의 약한 부극대가 나타납니다.')+' 빔 조향은 무늬를 이동시킵니다. 원거리·균일한 슬릿 내부 조명의 근사이며 밝기는 관찰용 제곱근 감마입니다. 실제 촬영 이미지가 아닙니다.';
 }else if(kind==='xrd'){
  const center=r.twoTheta===null?null:r.twoTheta+s.zero-2*s.height/200*Math.cos(r.theta*Math.PI/180)*180/Math.PI;
  const response=center===null?0:Math.exp(-.5*((p.scanTwoTheta-center)/s.acceptance)**2);
  body=bar('검출각 일치도',response,65)+txt(300,175,'주황: 현재 검출각 / 청록: 이동한 반사 위치');
  if(center!==null)body+=line(50+500*p.scanTwoTheta/180,190,50+500*p.scanTwoTheta/180,225,'#ffbb78',4)+line(50+500*center/180,190,50+500*center/180,225,'#79ddf0',4);
  state={center,response};if(center!==null)metrics.push(['오차를 포함한 반사 위치',center,'°']);metrics.push(['검출각 일치도',response*100,'%']);note='대칭 θ–2θ, 고니오미터 반경 200 mm, 높이 오차 Δ(2θ)=−2h cosθ/R의 근사입니다. 일치도는 지정한 각도 수용폭의 Gaussian 응답이며 실제 XRD 세기나 피크 폭 데이터가 아닙니다.';
 }else if(kind==='fresnel'){
  const a=Math.max(0,Math.min(89.5,p.incidence+s.zero)),u=p.n1/p.n2*Math.sin(a*Math.PI/180),ci=Math.cos(a*Math.PI/180),ct=Math.sqrt(Math.max(0,1-u*u));
  const rs=p.n1===p.n2?0:u>1?1:((p.n1*ci-p.n2*ct)/(p.n1*ci+p.n2*ct))**2,rp=p.n1===p.n2?0:u>1?1:((p.n2*ci-p.n1*ct)/(p.n2*ci+p.n1*ct))**2;
  const signal=rp*Math.cos(s.mixing*Math.PI/180)**2+rs*Math.sin(s.mixing*Math.PI/180)**2;
  body=bar('혼합 편광 반사 검출',signal,70)+txt(300,180,'편광축이 어긋나면 브루스터 각에서도 s 성분이 남습니다.');state={actualAngle:a,signal};metrics.push(['실제 법선 기준 입사각',a,'°'],['반사 검출 비율',signal*100,'%']);note='p편광축 오차를 s/p 세기 혼합으로 계산합니다. 회전 시야와 편광축 조절은 별개입니다.';
 }else if(kind==='prism'){
  const rays=r.rays.map(ray=>({lambda:ray.lambda,y:ray.displayY-s.detectorOffset}));
  body+=`<rect x="200" y="35" width="200" height="185" fill="#050a12" stroke="#7596ac"/>`;
  for(let i=0;i<r.rays.length;i++){const ray=r.rays[i],y=(rays[i].y-40)*.75;if(y>=35&&y<=220)body+=line(205,y,395,y,ray.color,7);}
  state={incomingAngle:r.incomingAngle,screenCenters:rays.map(ray=>ray.y),captured:rays.filter(x=>{const y=(x.y-40)*.75;return y>=35&&y<=220;}).length};metrics.push(['스크린 안 대표 파장',state.captured,'개']);note='회전은 위 장치의 입사·굴절·출사 경로를 함께 바꿉니다. 스크린 위치가 벗어나면 일부 빛을 놓칠 수 있습니다. 스크린 보정은 그림 좌표 1단위=1 mm로 가정한 확대 표시이며 실제 장치 치수가 아닙니다.';
 }else if(kind==='telescope'){
  const signedFe=p.telescopeModel==='galilean'?-p.eyepiece:p.eyepiece,u=signedFe+s.eyepieceOffset,vergence=Math.abs(u)<1e-10?null:1/signedFe-1/u;
  const exitDiameter=p.diameter/(p.objective/p.eyepiece),pupilRadius=exitDiameter/2,eyeRadius=1.5;
  let transmitted=0,total=0;for(let iy=-30;iy<=30;iy++)for(let ix=-30;ix<=30;ix++){const x=ix/30*pupilRadius,y=iy/30*pupilRadius;if(x*x+y*y<=pupilRadius*pupilRadius){total++;if((x-s.pupilOffset)**2+y*y<=eyeRadius*eyeRadius)transmitted++;}}
  const signal=total?transmitted/total:0;
  body+=`<circle cx="300" cy="125" r="${Math.min(80,pupilRadius*20)}" fill="#69d7ef" fill-opacity=".5"/><circle cx="${300+s.pupilOffset*20}" cy="125" r="30" fill="none" stroke="#ffd08b" stroke-width="3"/>`+txt(300,235,'청록: 출사동공 / 주황: 눈의 동공(지름 3 mm)');state={vergence,signal};metrics.push(['렌즈 간 실제 설정 거리',p.objective+(p.telescopeModel==='galilean'?-p.eyepiece:p.eyepiece)+s.eyepieceOffset,'mm'],['눈에 들어오는 광량 비',signal*100,'%']);if(vergence!==null)metrics.push(['출사 광속 버전스',vergence*1000,'m⁻¹']);note='접안 위치가 맞으면 출사 광선이 평행합니다(버전스 0). 눈을 출사동공 중심에서 벗어나게 하면 시야가 어두워집니다. 눈의 조절·수차는 생략합니다.';
 }else if(kind==='absorption'){
  if(p.absorptionType==='metal'){
   const collected=r.emits&&r.kinetic>s.retarding,remaining=Math.max(0,(r.kinetic||0)-s.retarding);
   body+=line(150,55,150,205,'#8ec9dd',8)+line(450,55,450,205,'#ffd192',8)+line(165,130,collected?440:295,130,collected?'#8ee9ff':'#ed9875',4)+txt(300,65,!r.emits?'현재 에너지에서 양의 운동에너지 방출 없음':collected?'수집 전극까지 도달':'방출 후 전극 도달 전 저지')+txt(150,235,'금속 표면')+txt(450,235,'수집 전극');if(r.emits&&Number(p.intensity??1)>0)body+=`<circle r="5" fill="#96e4ff"><animateMotion dur="1.8s" repeatCount="indefinite" path="${collected?'M170 130L435 130':'M170 130L295 130L170 130'}"/></circle>`;state={collected,remaining};metrics.push(['최대 전자의 잔여 운동에너지',remaining,'eV']);note='Φ를 넘겨 방출되어도 저지 전압이 Kmax/e 이상이면 수집되지 않습니다. 최대 에너지 전자 하나의 도달 조건이며 실제 전류–전압 곡선을 예측하지 않습니다.';
  }else{
   const transmitted=Math.exp(-s.alpha*s.thickness),absorbed=1-transmitted;
   body=bar('시료 통과광',transmitted,55)+bar('시료 흡수광',absorbed,135,'#efb471');state={transmitted,absorbed};metrics.push(['광학 두께 αt',s.alpha*s.thickness,''],['투과율',transmitted*100,'%']);note='입력한 가상 α에 대한 Beer–Lambert I/I₀=exp(−αt). α는 실제 물질 데이터나 밴드갭으로 계산한 값이 아닙니다. 흡수와 밴드 간 들뜸·진공 방출 조건을 구분합니다.';
  }
 }
 return {title,state,detectorImage,metrics:metrics.map(([label,value,unit])=>({label,value:Number.isFinite(value)?f(value):null,unit})),note,svg:`<svg class="sim-svg practical-screen" viewBox="0 0 600 ${height}" role="img" aria-label="${title}"><rect width="600" height="${height}" rx="8" fill="#102434"/>${txt(300,27,title,16)}${body}</svg>`,summary:`현장 조절 학습 모델 (${kind}): ${Object.entries(s).map(([k,v])=>`${k}=${v}`).join(', ')}. ${metrics.map(([label,value,unit])=>`${label}=${Number.isFinite(value)?f(value):'없음'} ${unit}`).join('; ')}. ${note}`};
}
if(typeof module!=='undefined')Object.assign(module.exports,{opticsPractical,opticsPracticalControls});
