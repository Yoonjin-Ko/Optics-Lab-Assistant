"""화면 설정의 정의·값 조회. 서로 다른 물리량을 LLM이 같은 값으로 대체하지 않는다."""
import json
import math
import re
from .optics import user_question

# 이름, 단위, 정의, 별칭. 값은 저장하지 않고 요청 스냅샷에서 읽는다.
PARAMETERS = {
 'michelson': {
  'practical.arm1Distance':('빔스플리터 → M₁ 거울 거리','mm','빔스플리터에서 M₁ 거울까지의 편도 거리 L₁입니다. 광원부터의 거리가 아닙니다.','M₁ 거울 거리|M1 거울 거리|M₁까지 거리|M1까지 거리|M₁ 거울까지|M1 거울까지'),
  'practical.arm2Distance':('빔스플리터 → M₂ 거울 거리 · 기준','mm','거울 미동 Δx=0일 때 빔스플리터에서 M₂까지의 편도 거리 L₂입니다. 현재 M₂ 거리는 이 값에 Δx를 단위 변환해 더합니다.','M₂ 거울 거리|M2 거울 거리|M₂까지 거리|M2까지 거리|M₂ 거울까지|M2 거울까지'),
  'derived.opl':('왕복 광로차 · 공기 근사','µm','공기 n≈1에서 두 팔의 왕복 광학적 경로 길이 차이입니다. 2[(L₂−L₁)+Δx]로 계산합니다.','왕복 광로차|광로차|광경로 차이'),

  'practical.armDifference':('두 거울까지의 거리 차이 · 기준','µm','거울 이동 Δx=0일 때 빔스플리터에서 각 거울까지의 거리 차이 L₂−L₁입니다. 공기에서 왕복 광로차는 이 값의 약 두 배입니다. 등경사 원형 무늬의 곡률을 정하는 모델 입력이며, 추가 거울 이동량 Δx와 다른 값입니다.','두 거울까지의 거리 차이|두 거울까지 거리 차이|두 거리 차이|팔 길이 차이|초기 팔 길이 차이|초기 팔길이 차이|기준 유효 팔 길이 차이|기존 유효 팔 길이 차이|기준 팔 길이 차이'),
  'values.displacement':('거울 이동 Δx','µm','기준 위치에서 한쪽 거울을 추가로 움직인 거리입니다. 공기 근사에서 왕복 광경로 변화는 2Δx입니다.','거울 이동|거울 변위|Δx'),
  'values.mirrorTiltX':('M₂ 기울기 X','mrad','M₂의 X축 미세 기울기입니다. 반사 방향 변화는 작은 각도에서 약 두 배이며 빔 중심과 간섭 위상 기울기를 함께 바꿉니다.','M₂ 기울기 X|거울 기울기 X'),
  'values.mirrorTiltY':('M₂ 기울기 Y','mrad','M₂의 Y축 미세 기울기입니다. X 기울기와 함께 무늬 방향과 빔 중심을 바꿉니다.','M₂ 기울기 Y|거울 기울기 Y'),
  'practical.beamX':('귀환빔 위치 보정 X','mm','조향 거울쌍의 효과를 나타내는 X 위치 보정값입니다. 검출면 실제 중심 차이는 이 값에 M₂ 기울기로 인한 이동을 더합니다.','귀환빔 위치 보정 X'),
  'practical.beamY':('귀환빔 위치 보정 Y','mm','조향 거울쌍의 효과를 나타내는 Y 위치 보정값입니다. 거울 기울기와 별도로 중심을 보정합니다.','귀환빔 위치 보정 Y'),
  'practical.waist1':('M₁ 빔 반경','mm','기준빔의 Gaussian 세기가 중심의 1/e²로 감소하는 반경입니다.','M₁ 빔 반경'),
  'practical.waist2':('M₂ 빔 반경','mm','귀환빔의 Gaussian 세기가 중심의 1/e²로 감소하는 반경입니다.','M₂ 빔 반경'),
  'practical.balance':('M₂ / M₁ 광량','','두 팔의 상대 광량 비입니다. 두 빔의 광량 균형은 간섭 대비에 영향을 줍니다.','광량 비|광량비|M₂ / M₁ 광량'),
 },
}
DOCS={'michelson':'michelson-interferometer'}

def _normalize(text):return re.sub(r'\s+','',text).lower()

def plan_parameter_query(query):
    question=user_question(query)
    if not re.search(r'뭐|무엇|뜻|의미|정의|설명|얼마|몇',question):return None
    # 조정·역산 질문을 용어 조회로 바꾸지 않는다.
    if re.search(r'어떻게|바꾸|늘리|줄이|만들|얻으|맞추|계산',question):return None
    match=re.search(r'\[실험 설정 스냅샷\]\n([^\n]+)',query)
    if not match:return None
    try:
        snapshot=json.loads(match[1]);kind=snapshot['kind']
        if snapshot.get('version')!=1 or kind not in PARAMETERS:return None
        q=_normalize(question);keys=[]
        for key,(label,unit,definition,aliases) in PARAMETERS[kind].items():
            if any(_normalize(alias) in q for alias in aliases.split('|')):keys.append(key)
        if not keys:return None
        return {'operation':'parameter_definition','parameters':{'snapshot':snapshot,'keys':keys},'origins':{},'document':DOCS[kind]}
    except (ValueError,TypeError,KeyError):return None

def calculate_parameter_query(parameters):
    try:
        snapshot=parameters['snapshot'];kind=snapshot['kind'];rows=[]
        snapshot={**snapshot,'practical':dict(snapshot.get('practical',{})),'derived':{}}
        practical=snapshot['practical'];values=snapshot.get('values',{})
        l1=practical.get('arm1Distance');l2=practical.get('arm2Distance');dx=values.get('displacement')
        valid=lambda x:type(x) in (int,float) and math.isfinite(x)
        if valid(l1) and valid(l2) and l1>0 and l2>0:
            practical['armDifference']=round((l2-l1)*1000,9)
        if valid(practical.get('armDifference')) and valid(dx):
            snapshot['derived']['opl']=2*(practical['armDifference']+dx)
        for key in parameters['keys']:
            label,unit,definition,_=PARAMETERS[kind][key];group,name=key.split('.')
            value=snapshot.get(group,{}).get(name)
            if type(value) in (int,float) and math.isfinite(value):current=f'현재 전송된 설정은 **{value:g} {unit}**입니다.'
            else:current='현재 스냅샷에 이 값이 없어 숫자는 확인할 수 없습니다.'
            rows.append(f'**{label}**: {definition} {current}')
        # 팔 길이 기준과 추가 이동량의 관계도 두 입력을 따로 읽어 계산한다.
        if 'practical.armDifference' in parameters['keys']:
            a=snapshot.get('practical',{}).get('armDifference');dx=snapshot.get('values',{}).get('displacement')
            if all(type(x) in (int,float) and math.isfinite(x) for x in (a,dx)):
                rows.append(f'두 거울까지 현재 편도 거리 차이는 초기 {a:g} + 추가 이동 {dx:g} = **{a+dx:g} µm**입니다. Δx에 따른 왕복 광경로 변화는 **{2*dx:g} µm**이며 기준 차이 자체가 0이라는 뜻은 아닙니다. 중심 위상은 기준 위치에서 보정한 교육 모델입니다.')
        return {'operation':'parameter_definition','ok':True,'status':'calculated','answer':'\n\n'.join(rows),'formula':'현재 편도 거리 차이 = L₂−L₁+Δx; 왕복 광로차 ≈ 2(L₂−L₁+Δx); 추가 왕복 광로차 변화 ≈ 2Δx' if kind=='michelson' and 'practical.armDifference' in parameters['keys'] else '화면 설정 항목의 정의와 전송 시점 값 조회','assumptions':'전송 당시 가상 모델의 설정이며 실제 장비 측정값이 아닙니다.','source':'optics://documents/'+DOCS[kind]}
    except (KeyError,TypeError,ValueError):
        return {'operation':'parameter_definition','ok':False,'status':'invalid_input','message':'설정 항목과 스냅샷을 확인해 주세요.'}
