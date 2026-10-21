const assert = require('node:assert/strict');
const {opticsSimulation:simulate} = require('../optics_lab.js');
const v = {angle:90,focal:10,object:30,wavelength:532,slit:.1,distance:1};
assert.ok(simulate('polarization',v).ratio < 1e-25);
assert.equal(simulate('polarization',{...v,angle:0}).ratio,1);
assert.equal(simulate('lens',v).image,15);
assert.equal(simulate('lens',{...v,object:10}).image,null);
assert.equal(simulate('lens',{...v,object:5}).image,-10);
assert.ok(Math.abs(simulate('diffraction',v).width-10.64) < 1e-9);
assert.equal(simulate('diffraction',v).points[120].intensity,1);
assert.ok(Math.abs(simulate('diffraction',{...v,slit:.2}).width-5.32) < 1e-9);
console.log('광학 시뮬레이션 검증 통과');
assert.equal(simulate('concave-lens',v).signedF,-10);
assert.equal(simulate('concave-lens',v).image,-7.5);
assert.equal(simulate('convex-mirror',v).image,-7.5);
assert.equal(simulate('concave-mirror',v).image,15);
assert.equal(simulate('concave-mirror',{...v,object:5}).image,-10);
assert.equal(simulate('concave-mirror',{...v,object:10}).image,null);
const bragg=simulate('xrd',{...v,xray:.154,spacing:.3,order:1});
assert.ok(Math.abs(2*.3*Math.sin(bragg.theta*Math.PI/180)-.154)<1e-12);
assert.equal(simulate('xrd',{...v,xray:.4,spacing:.05,order:1}).theta,null);
assert.equal(simulate('michelson',{...v,displacement:0,visibility:1}).intensity,1);
assert.ok(Math.abs(simulate('michelson',{...v,displacement:532/4000,visibility:1}).intensity)<1e-12);
assert.equal(simulate('michelson',{...v,displacement:1,visibility:0}).intensity,.5);
console.log('XRD·마이켈슨·오목렌즈·구면거울 검증 통과');
const fr=simulate('fresnel',{...v,n1:1,n2:1.5,incidence:0});
assert.ok(Math.abs(fr.rs-.04)<1e-12);assert.ok(Math.abs(fr.rp-.04)<1e-12);
assert.ok(simulate('fresnel',{...v,n1:1,n2:1.5,incidence:Math.atan(1.5)*180/Math.PI}).rp<1e-25);
const tir=simulate('fresnel',{...v,n1:1.5,n2:1,incidence:50});assert.equal(tir.tir,true);assert.equal(tir.rs,1);assert.equal(tir.rp,1);
assert.equal(simulate('fresnel',{...v,n1:1,n2:1,incidence:80}).rs,0);
const prism=simulate('prism',{...v,apex:10});assert.ok(prism.rays[0].deviation>prism.rays[4].deviation);
const scattering=simulate('scattering',{...v,wavelength:550,opticalDepth:0});assert.equal(scattering.ratio,1);assert.equal(scattering.transmission,1);
assert.ok(simulate('scattering',{...v,wavelength:450}).ratio>simulate('scattering',{...v,wavelength:700}).ratio);
console.log('s/p 반사·전반사·프리즘·산란 검증 통과');

const {opticsApparatus:apparatus}=require('../optics_lab.js');
for (const kind of ['michelson','xrd','fresnel','scattering','prism']) {
 const settings={...v,displacement:2,spacing:.3,n1:1,n2:1.5,incidence:45,apex:10,opticalDepth:.2};
 const svg=apparatus(kind,settings,simulate(kind,settings));
 assert.ok(svg.startsWith('<svg'));
 assert.ok(!svg.includes('NaN'));
 assert.ok(svg.includes('검출기') || svg.includes('스크린'));
}
console.log('5개 실험 장치 개념도 검증 통과');
const {xrdMaterials,xrdAllowed}=require('../optics_lab.js');
assert.equal(xrdAllowed([2,0,0],'diamond'),false);
assert.equal(xrdAllowed([2,0,0],'fcc'),true);
assert.equal(xrdAllowed([2,2,0],'diamond'),true);
assert.equal(xrdAllowed([1,0,0],'fcc'),false);
const expected111={Si:28.44,Ge:27.28,Al:38.47,Cu:43.32};
for(const material of xrdMaterials()){
 const result=simulate('xrd',{...v,material:material.id,plane:'111',xray:.15406});
 assert.ok(Math.abs(result.twoTheta-expected111[material.id])<.03);
 assert.ok(result.peaks.every(p=>xrdAllowed(p.hkl.split('').map(Number),material.structure)));
 assert.ok(result.peaks.every(p=>Math.abs(2*p.spacing*Math.sin(p.twoTheta/2*Math.PI/180)-.15406)<1e-12));
}
assert.equal(simulate('xrd',{material:'Si',plane:'200',xray:.15406}).theta,null);
console.log('Si·Ge·Al·Cu 피크 위치·소멸 규칙 검증 통과');
const centerSteps=[0,.25,.5,.75,1].map(c=>simulate('michelson',{...v,wavelength:532,displacement:c*532/2000,visibility:1}));
[1,.5,0,.5,1].forEach((expected,i)=>assert.ok(Math.abs(centerSteps[i].intensity-expected)<1e-10));
for(const s of centerSteps){assert.equal(s.radial.length,601);assert.ok(s.radial.every(p=>p.gray>=0&&p.gray<=255));assert.ok(Math.abs(s.radial[0].intensity-s.intensity)<1e-10);}
assert.ok(simulate('michelson',{...v,displacement:1,visibility:0}).radial.every(s=>Math.abs(s.intensity-.5)<1e-10));
console.log('마이켈슨 ¼주기·중심 세기·원형 세기 분포 검증 통과');
const mono=simulate('prism',{...v,apex:10,prismMode:'mono',wavelength:632.8});
assert.equal(mono.rays.length,1);assert.equal(mono.rays[0].lambda,632.8);assert.equal(mono.spread,0);
assert.ok(simulate('prism',{...v,apex:10,prismMode:'mono',wavelength:450}).rays[0].deviation>mono.rays[0].deviation);
assert.ok(simulate('diffraction',{...v,wavelength:650}).width>simulate('diffraction',{...v,wavelength:450}).width);
assert.ok(simulate('michelson',{...v,displacement:1,wavelength:450}).cycles>simulate('michelson',{...v,displacement:1,wavelength:650}).cycles);
assert.equal(simulate('polarization',{...v,wavelength:450}).ratio,simulate('polarization',{...v,wavelength:650}).ratio);
console.log('파장 선택·프리즘 단색광·회절/간섭 파장 의존성 검증 통과');
const excite=simulate('absorption',{absorptionType:'semiconductor',threshold:1.5,absorptionWave:532});
assert.equal(excite.allowed,true);assert.equal(excite.emits,false);assert.equal(excite.kinetic,null);
assert.equal(simulate('absorption',{absorptionType:'semiconductor',threshold:1.5,absorptionWave:1550}).allowed,false);
assert.equal(simulate('absorption',{absorptionType:'metal',threshold:4.5,absorptionWave:532}).emits,false);
const emitted=simulate('absorption',{absorptionType:'metal',threshold:4.5,absorptionWave:193});
assert.equal(emitted.emits,true);assert.ok(Math.abs(emitted.kinetic-(1239.841984/193-4.5))<1e-12);
assert.equal(simulate('absorption',{absorptionType:'insulator',threshold:8,absorptionWave:193}).allowed,false);
assert.equal(simulate('absorption',{absorptionType:'insulator',threshold:8,absorptionWave:100}).allowed,true);
console.log('내부 들뜸·표면 방출·문턱 조건 검증 통과');
const mid=simulate('absorption',{absorptionType:'semiconductor',threshold:1.5,fermiPosition:.5,electronTemperature:300,absorptionWave:532});
assert.equal(mid.fermiEnergy,.75);assert.ok(mid.conductionOccupation<.0001);assert.ok(mid.valenceOccupation>.9999);
const higher=simulate('absorption',{absorptionType:'semiconductor',threshold:1.5,fermiPosition:.9,electronTemperature:300,absorptionWave:532});assert.ok(higher.conductionOccupation>mid.conductionOccupation);
const warmer=simulate('absorption',{absorptionType:'semiconductor',threshold:1.5,fermiPosition:.5,electronTemperature:600,absorptionWave:532});assert.ok(warmer.conductionOccupation>mid.conductionOccupation);
assert.equal(simulate('absorption',{absorptionType:'metal',threshold:4.5,absorptionWave:193}).conductionOccupation,.5);
console.log('페르미 준위·온도·점유 확률 검증 통과');

// 세기는 광자 묶음 수에만 영향: 문턱·최대 운동에너지는 그대로다.
const dim=simulate('absorption',{absorptionType:'metal',threshold:4.5,absorptionWave:193,intensity:1});
const bright=simulate('absorption',{absorptionType:'metal',threshold:4.5,absorptionWave:193,intensity:10});
assert.equal(dim.kinetic,bright.kinetic);assert.equal(bright.emissionCount,dim.emissionCount*10);
assert.equal(simulate('absorption',{absorptionType:'metal',threshold:4.5,absorptionWave:650,intensity:10}).emissionCount,0);
assert.equal(simulate('absorption',{absorptionType:'metal',threshold:4.5,absorptionWave:193,intensity:0}).emissionCount,0);
const spectrum=simulate('prism',{apex:10,prismMode:'white'}).spectrum;
assert.equal(spectrum.length,61);assert.ok(spectrum[0].displayY-spectrum.at(-1).displayY>0);
assert.ok(spectrum.every(r=>Number.isFinite(r.displayY)&&r.displayY>30&&r.displayY<270));
console.log('세기·광전 방출 문턱·연속 프리즘 스펙트럼 검증 통과');
const sceneS=simulate('fresnel',{...v,n1:1,n2:1.5,incidence:45,polMode:'s',viewYaw:-30}).polarization3d;
const sceneP=simulate('fresnel',{...v,n1:1,n2:1.5,incidence:45,polMode:'p',viewYaw:30}).polarization3d;
assert.ok(sceneS.includes('Es ⟂ 입사면'));assert.ok(!sceneS.includes('Ep ∥ 입사면'));
assert.ok(sceneP.includes('Ep ∥ 입사면'));assert.notEqual(sceneS,sceneP);
for(const incidence of [0,45,89.5])assert.ok(!simulate('fresnel',{...v,incidence}).polarization3d.includes('NaN'));
const sixty=simulate('prism',{...v,apex:60,prismMode:'mono',wavelength:550});
const n550=1.5+.004/.55**2;
assert.ok(Math.abs(sixty.rays[0].deviation-(2*Math.asin(n550*.5)*180/Math.PI-60))<1e-9);
console.log('3D 편광 방향·회전·60도 프리즘 Snell 계산 검증 통과');

const prism30=simulate('prism',{...v,apex:30}),prism60=simulate('prism',{...v,apex:60});
assert.notEqual(prism30.prismPoints,prism60.prismPoints);
assert.notEqual(prism30.spectrum[0].displayY,prism60.spectrum[0].displayY);
assert.ok(prism60.spectrum[0].displayY-prism60.spectrum.at(-1).displayY > prism30.spectrum[0].displayY-prism30.spectrum.at(-1).displayY);
console.log('프리즘 각도에 따른 외형·출사 위치·색 분리폭 변화 검증 통과');
assert.ok(!apparatus('prism',{apex:60,prismMode:'white'},simulate('prism',{...v,apex:60})).includes('width="177" height="155"'));
console.log('프리즘 장치를 덮는 배경 제거 검증 통과');
for(const apex of [30,60,70]) {
 const traced=simulate('prism',{...v,apex});
 for(const ray of traced.spectrum) {
  const rad=Math.PI/180;
  assert.ok(Math.abs(Math.sin(traced.incomingAngle*rad)-ray.index*Math.sin(ray.entryRefraction*rad))<1e-10);
  assert.ok(Math.abs(ray.index*Math.sin(ray.exitIncidence*rad)-Math.sin(ray.exitRefraction*rad))<1e-10);
  assert.ok(Math.abs(ray.entryRefraction+ray.exitIncidence-apex)<1e-10);
  assert.ok(Math.abs(Math.atan2(ray.displayY-ray.exitY,520-ray.exitX)/rad-(ray.exitRefraction-apex/2))<1e-10);
 }
}
console.log('프리즘 실제 광선 경로·두 면 Snell 법칙·법선 기준 각도 검증 통과');
