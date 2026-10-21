const assert=require('node:assert/strict');
const {opticsSimulation:sim,opticsApparatus}=require('../optics_lab.js');
const eq=v=>sim('equipment',v);
const near=(a,b)=>assert.ok(Math.abs(a-b)<.001,`${a} != ${b}`);
near(eq({equipmentType:'camera'}).metrics[0].value,52.6316);
assert.ok(eq({equipmentType:'camera',question:'피사체 폭 200 mm를 센서에 채우려면?'}).solution.includes('327.7778'));
assert.ok(eq({equipmentType:'camera',u:50,f:50}).metrics[0].value===null);
assert.ok(eq({equipmentType:'camera',question:'회절 무늬 지름 5 μm 이하의 F수는?'}).solution.includes('3.7258'));
assert.ok(eq({equipmentType:'telescope',question:'목표 각배율 40배 접안렌즈는?'}).solution.includes('12.5 mm'));
assert.ok(eq({equipmentType:'telescope',question:'1초각을 구분할 최소 구경은?'}).solution.includes('138.4037'));
assert.ok(eq({equipmentType:'microscope',question:'목표 분해 거리 100 nm에 필요한 NA?'}).solution.includes('불가능'));
assert.ok(eq({equipmentType:'microscope',medium:1.515,question:'분해 거리 300 nm의 NA와 수광 반각은?'}).solution.includes('수광 반각'));
assert.ok(eq({equipmentType:'microscope',question:'목표 중간상 배율 80배의 대물렌즈는?'}).solution.includes('2.5 mm'));
for(const equipmentType of ['camera','telescope','microscope']) {
 const r=eq({equipmentType});assert.ok(!r.apparatus.includes('NaN'));assert.equal(opticsApparatus('equipment',{},r),r.apparatus);
 assert.equal(r.hints.length,2);assert.ok(r.summary.includes('실제 장비 설정 권고가 아닙니다'));
}
assert.notEqual(eq({equipmentType:'camera',u:1000}).apparatus,eq({equipmentType:'camera',u:2000}).apparatus);
console.log('3종 장비·6종 역산·불가능 조건·광경로 조건 연동 검증 통과');
const narrowCamera=eq({equipmentType:'camera',sensor:12});
const wideCamera=eq({equipmentType:'camera',sensor:36});
assert.notEqual(narrowCamera.apparatus,wideCamera.apparatus);
assert.ok(narrowCamera.apparatus.includes('228.0 mm'));
assert.ok(wideCamera.apparatus.includes('684.0 mm'));
for(const change of [{f:100},{u:2000},{fNumber:16}])assert.notEqual(wideCamera.apparatus,eq({equipmentType:'camera',sensor:36,...change}).apparatus);
console.log('카메라 센서·초점거리·거리·조리개 사진 미리보기 연동 검증 통과');
for(const telescopeModel of ['kepler','galilean'])for(const diameter of [20,80,300])for(const objective of [100,2000])for(const eyepiece of [5,80]){
 const r=eq({equipmentType:'telescope',telescopeModel,diameter,objective,eyepiece});
 assert.ok(r.instrumentGeometry.rayRadius<r.instrumentGeometry.objectiveRadius);
 assert.ok(r.instrumentGeometry.outRadius<r.instrumentGeometry.eyepieceRadius);
 assert.ok(!r.apparatus.includes('NaN'));
}
const small=eq({equipmentType:'telescope',diameter:20}),large=eq({equipmentType:'telescope',diameter:300});
assert.ok(large.instrumentGeometry.objectiveRadius>small.instrumentGeometry.objectiveRadius);
const galilean=eq({equipmentType:'telescope',telescopeModel:'galilean',objective:500,eyepiece:25});
assert.equal(galilean.metrics[0].value,20);assert.equal(galilean.metrics[1].value,475);
const finite=eq({equipmentType:'microscope',microscopeModel:'finite',microF:4,tube:200});
assert.equal(finite.metrics[0].value,49);assert.ok(!finite.apparatus.includes('data-optic="tube"'));
assert.ok(eq({equipmentType:'microscope'}).apparatus.includes('data-optic="tube"'));
console.log('굴절망원경 2종·광학현미경 2종·구경 변화·극단 조절에서 광선의 유효 구경 통과 검증');
