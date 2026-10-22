const assert=require('node:assert/strict');
const {opticsSimulation:sim,opticsPractical:practice,opticsPracticalControls:controls}=require('../optics_lab.js');
const base={angle:45,focal:10,object:30,wavelength:532,slit:.1,distance:1,scanTwoTheta:30,xray:.154,spacing:.3,order:1,microF:4,tube:200,microNA:.65,medium:1,wave:550,n1:1,n2:1.5,incidence:45,apex:60,prismMode:'white',f:50,u:1000,fNumber:4,sensor:36,objective:500,eyepiece:25,diameter:80,displacement:0,visibility:1,threshold:1.12,absorptionWave:532,absorptionType:'semiconductor',fermiPosition:.5,electronTemperature:300};
function run(kind,settings={},change={}){const p={...base,...change};const r=sim(['camera','telescope','microscope'].includes(kind)?'equipment':kind,{...p,equipmentType:kind});return practice(kind,p,r,settings);}
const aligned=run('michelson'),offset=run('michelson',{beamX:6,beamY:4});
assert.equal(aligned.state.overlap,1);assert.ok(offset.state.overlap<.01);assert.equal(aligned.state.beamSeparation,0);
assert.equal(run('michelson',{beamX:-2},{mirrorTiltX:1}).state.beamSeparation,0);
assert.ok(run('michelson',{waist2:4}).state.overlap<1);
assert.notEqual(run('michelson',{view:'interference'}).svg,run('michelson',{view:'interference',beamX:6}).svg);
assert.ok(run('michelson',{view:'interference'},{mirrorTiltX:1}).state.pixelAverage<1);
assert.equal(run('lens',{screen:15}).state.blur,0);assert.ok(run('lens',{screen:25}).state.blur>0);
assert.equal(run('concave-lens').state.real,false);assert.equal(run('concave-lens').state.visible,true);assert.equal(run('concave-lens',{eyeOffset:4,eyeDistance:5}).state.visible,false);
assert.ok(run('camera',{screen:70}).state.blur>run('camera',{screen:52.6315789474}).state.blur);
assert.equal(run('microscope').state.blur,0);assert.ok(run('microscope',{sampleDefocus:3}).state.blur>0);
assert.equal(run('telescope').state.vergence,0);assert.notEqual(run('telescope',{eyepieceOffset:5}).state.vergence,0);
assert.ok(run('telescope',{pupilOffset:5}).state.signal<run('telescope').state.signal);
assert.ok(run('diffraction',{beamOffset:.4}).state.transmitted<run('diffraction').state.transmitted/100);
assert.equal(run('diffraction',{steering:2}).state.center,2);
assert.ok(run('polarization',{leak:.05},{angle:90}).state.signal>.049);
const brewster=Math.atan(1.5)*180/Math.PI;
assert.ok(run('fresnel',{mixing:10},{incidence:brewster}).state.signal>run('fresnel',{mixing:0},{incidence:brewster}).state.signal);
assert.ok(run('xrd',{height:1}).state.center<run('xrd').state.center);
assert.ok(Math.abs(run('xrd',{zero:1}).state.center-run('xrd').state.center-1)<1e-10);
assert.ok(run('absorption',{thickness:10}).state.transmitted<run('absorption',{thickness:1}).state.transmitted);
assert.equal(run('absorption',{retarding:0},{absorptionType:'metal',threshold:2,absorptionWave:400}).state.collected,true);
assert.equal(run('absorption',{retarding:2},{absorptionType:'metal',threshold:2,absorptionWave:400}).state.collected,false);
for(const apex of [30,60,70])for(const prismRotation of [-5,0,5])for(const wavelength of [380,550,750]){
 const r=sim('prism',{...base,apex,prismRotation,wavelength,prismMode:'mono'});assert.ok(Number.isFinite(r.reference.deviation));assert.ok(!r.rays[0].path.includes('NaN'));
}
assert.notEqual(sim('prism',{...base,prismRotation:0}).rays[0].path,sim('prism',{...base,prismRotation:3}).rays[0].path);
for(const kind of ['michelson','polarization','diffraction','xrd','fresnel','prism','lens','concave-lens','concave-mirror','convex-mirror','camera','telescope','microscope','absorption']){
 for(const control of controls(kind))for(const value of [control.min,control.max]){
  const r=run(kind,{[control.key]:value});assert.ok(!r.svg.includes('NaN'),kind+': '+control.key);assert.ok(r.metrics.every(m=>m.value===null||Number.isFinite(m.value)),kind+': finite');
 }
}
console.log('14종 실험 현장 조절: 빔 겹침·기울기·초점·구경·검출각·누설·흡수·저지 전압 및 조절 끝값 통과');
// 기본 관찰은 합성 간섭이며, 위상·기울기·팔 길이 차이가 실제 검출 이미지를 바꾼다.
const rings=run('michelson',{view:'interference'});
assert.equal(rings.state.observationFocal,10);
assert.equal(rings.state.observationExtent,4);
assert.notEqual(rings.detectorImage,run('michelson',{view:'interference'},{displacement:.133}).detectorImage);
assert.notEqual(rings.detectorImage,run('michelson',{view:'interference',armDifference:0}).detectorImage);
assert.notEqual(run('michelson',{view:'interference',armDifference:0}).detectorImage,run('michelson',{view:'interference',armDifference:0,beamX:-.36},{mirrorTiltX:.18}).detectorImage);
assert.equal(run('michelson',{view:'alignment'}).state.observationExtent,12);
{
 const {michelsonGeometry}=require('../optics_lab.js');
 const g=michelsonGeometry({arm1Distance:100,arm2Distance:100.02,displacement:1,wavelength:532});
 assert.equal(g.currentGap,21);assert.equal(g.opl,42);assert.equal(g.currentArm2,100.021);
 const common=michelsonGeometry({arm1Distance:100.05,arm2Distance:100.07,wavelength:532});
 assert.equal(common.gap,20);
 const first=run('michelson',{arm1Distance:100,arm2Distance:100.02}),next=run('michelson',{arm1Distance:100,arm2Distance:100.021});
 assert.notEqual(first.detectorImage,next.detectorImage);
 assert.equal(next.state.geometry.opl,42);
}
