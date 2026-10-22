"""광학 계산 계약·단위 검증·제한된 한국어 질의 해석. LLM과 브라우저를 신뢰하지 않는다."""
import math
import json
import re

LENGTH = {'m':1., 'cm':1e-2, 'mm':1e-3, 'um':1e-6, 'µm':1e-6, 'μm':1e-6, 'nm':1e-9, 'å':1e-10, 'Å':1e-10}
SPECS = {
 'photon_energy': ('광자 에너지', 'light-fundamentals', ['wavelength'], 'E = hc/λ₀', '진공 파장, 광자 한 개의 에너지'),
 'bragg_angle': ('브래그 각도', 'xrd-bragg', ['wavelength','spacing','order'], '2d sinθ = nλ', '같은 단위로 변환. θ는 결정면 기준이며 측정 축은 2θ. 결정 소멸 규칙·세기는 계산하지 않음'),
 'michelson_wavelength': ('간섭계 파장', 'michelson-interferometer', ['displacement','fringes'], 'λ ≈ 2Δx/N', '공기 n≈1, 한 팔 거울 이동, 밝음→다음 밝음을 한 주기로 계수'),
 'michelson_displacement': ('간섭계 거울 이동량', 'michelson-interferometer', ['wavelength','fringes'], 'Δx ≈ Nλ/2', '공기 n≈1, 한 팔 거울의 추가 이동 거리, 밝음→다음 밝음 한 주기'),
 'michelson_fringes': ('간섭무늬 주기 수', 'michelson-interferometer', ['displacement','wavelength'], 'N ≈ 2Δx/λ', '공기 n≈1, 왕복 경로. 결과는 연속적인 위상 주기 수'),
 'malus': ('편광판 투과 세기 비', 'polarization-and-reflection', ['angle'], 'I/I₀ = cos²θ', '이상적인 두 선편광 투과축의 상대각, I₀는 두 번째 판 직전 세기'),
 'thin_lens': ('얇은 렌즈 상 위치', 'lenses-and-optical-instruments', ['focal','object_distance'], '1/f = 1/u + 1/v, m = −v/u', '공기 중 얇은 렌즈. 실물체 u>0, 볼록 f>0·오목 f<0. 유한 두께·수차 생략'),
}
NUM = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?'
UNIT = r'(?:nm|mm|cm|[uµμ]m|[Åå]|m)'

def calculate_optics(operation: str, parameters: dict) -> dict:
    """정해진 식만 계산하고 입력 부족·단위 오류·불가능 조건을 구조화해서 반환한다."""
    if operation == 'parameter_definition':
        from .experiment_parameters import calculate_parameter_query
        return calculate_parameter_query(parameters)
    if operation == 'inquiry':
        from .inquiry_calculations import calculate_inquiry
        return calculate_inquiry(parameters)
    if operation not in SPECS:
        return {'ok':False,'status':'unsupported_operation','operation':operation,'message':'지원하지 않는 계산입니다.'}
    title,doc,required,formula,assumption=SPECS[operation]
    def json_safe(value):
        if isinstance(value,float) and not math.isfinite(value):return str(value)
        if isinstance(value,dict):return {k:json_safe(v) for k,v in value.items()}
        if isinstance(value,list):return [json_safe(v) for v in value]
        return value
    base={'operation':operation,'title':title,'formula':formula,'assumptions':assumption,'source':f'optics://documents/{doc}','inputs':json_safe(parameters)}
    if not isinstance(parameters,dict):
        return {**base,'ok':False,'status':'invalid_input','message':'입력은 이름과 값의 사전이어야 합니다.'}
    missing=[k for k in required if k not in parameters]
    if missing:return {**base,'ok':False,'status':'missing_input','missing':missing,'message':'필요한 입력: '+', '.join(missing)}
    try:
        unknown=set(parameters)-set(required)
        if unknown:raise ValueError('정의되지 않은 입력: '+', '.join(sorted(unknown)))
        def val(key):
            entry=parameters[key]
            if not isinstance(entry,dict) or set(entry)!={'value','unit'}:raise ValueError(key+': value와 unit이 필요합니다.')
            raw=entry['value']
            if isinstance(raw,bool) or not isinstance(raw,(int,float)) or not math.isfinite(raw):raise ValueError(key+': 유한 숫자가 필요합니다.')
            return float(raw),entry['unit']
        def length(key,signed=False,zero=False):
            x,unit=val(key)
            if unit not in LENGTH:raise ValueError(key+': 길이 단위 m/cm/mm/µm/nm/Å를 사용하세요.')
            x*=LENGTH[unit]
            if not math.isfinite(x) or (x==0 if signed else x<0 if zero else x<=0):raise ValueError(key+': '+('0이 아닌' if signed else '양수')+' 길이가 필요합니다.')
            return x
        def scalar(key,unit):
            x,u=val(key)
            if u!=unit:raise ValueError(key+': 단위 '+unit+'이 필요합니다.')
            return x
        def result(name,value,unit):
            if not math.isfinite(value):raise ValueError('계산 범위를 초과했습니다.')
            return {'name':name,'value':value,'unit':unit}
        if operation=='photon_energy':
            w=length('wavelength');results=[result('광자 에너지',6.62607015e-34*299792458/w/1.602176634e-19,'eV')]
        elif operation=='bragg_angle':
            w=length('wavelength');d=length('spacing');order=scalar('order','count')
            if order<=0 or not order.is_integer():raise ValueError('회절 차수는 양의 정수여야 합니다.')
            ratio=order*w/(2*d)
            if ratio>1:return {**base,'ok':False,'status':'impossible','message':'nλ > 2d이므로 실수 브래그 각이 없습니다.'}
            theta=math.degrees(math.asin(ratio));results=[result('θ',theta,'deg'),result('2θ',2*theta,'deg')]
        elif operation=='michelson_wavelength':
            d=length('displacement');n=scalar('fringes','count')
            if n<=0:raise ValueError('무늬 주기 수는 0보다 커야 합니다.')
            results=[result('파장',2*d/n*1e9,'nm')]
        elif operation=='michelson_displacement':
            w=length('wavelength');n=scalar('fringes','count')
            if n<0:raise ValueError('무늬 주기 수는 음수가 아니어야 합니다.')
            results=[result('거울 이동량',n*w/2*1e6,'µm')]
        elif operation=='michelson_fringes':
            results=[result('무늬 주기 수',2*length('displacement',zero=True)/length('wavelength'),'cycles')]
        elif operation=='malus':
            angle,u=val('angle')
            if u not in ('deg','rad'):raise ValueError('각도 단위 deg 또는 rad가 필요합니다.')
            ratio=math.cos(math.radians(angle) if u=='deg' else angle)**2
            if ratio<1e-15:ratio=0.
            results=[result('I/I₀',ratio,'ratio'),result('투과율',100*ratio,'%')]
        else:
            f=length('focal',True);u=length('object_distance')
            if math.isclose(u,f,rel_tol=1e-12):return {**base,'ok':False,'status':'singular','message':'물체가 초점에 있어 유한한 상 거리를 구할 수 없습니다.'}
            v=f*u/(u-f);results=[result('상 거리',v*100,'cm'),result('횡배율',-v/u,'ratio')]
        return {**base,'ok':True,'status':'calculated','results':results}
    except (ValueError,TypeError,OverflowError,ZeroDivisionError) as exc:
        return {**base,'ok':False,'status':'invalid_input','message':str(exc)}

def plan_calculation(query: str) -> dict | None:
    """수치 계산 요청만 해석. 명시 입력을 우선하고 모호한 수치는 추측하지 않는다."""
    from .experiment_parameters import plan_parameter_query
    parameter_query=plan_parameter_query(query)
    if parameter_query:return parameter_query
    from .inquiry_calculations import plan_inquiry
    inquiry=plan_inquiry(query)
    if inquiry:return inquiry
    if query.startswith('[사용자 질문]\n'):
        user,_,context=query[len('[사용자 질문]\n'):].partition('\n\n[현재 가상 실험]')
    else:user,context=query,''
    snapshot={}
    match=re.search(r'\[광학 계산 입력\]\s*([^\n]+)',context)
    if match:
        try:
            candidate=json.loads(match.group(1))
            if isinstance(candidate,dict):snapshot=candidate
        except (ValueError,TypeError):pass
    q=user.lower()
    active_match=re.search(r'\[현재 실험 문서\] ([a-z-]+)',context)
    active_document=active_match.group(1) if active_match else None
    # 목표 설정·역산 문제를 현재 설정의 정방향 계산으로 바꿔 답하지 않는다.
    # 지원하지 않는 역산은 조건을 보존한 채 설명 작성 경로에서 처리한다.
    reverse_request=re.search(r'만들려|얻으려|맞출|정할|옮겨야|설정해야|바꿀|역산|필요한|몇\s*도로',q)
    supported_inverse=('파장' in q or 'wavelength' in q) and bool(re.search(r'마이[켈컬]|michelson|무늬',q)) and not re.search(r'옮겨야|이동해야',q)
    displacement_target=bool(re.search(r'거울.*(?:얼마나|이동량|변위)|(?:이동량|변위).*거울',q)) and bool(re.search(r'옮겨야|이동해야|구해|계산|얼마',q)) and active_document=='michelson-interferometer'
    if reverse_request and not supported_inverse and not displacement_target:return None
    if not re.search(NUM,user) and not re.search(r'계산|구해',q) and not (context and re.search(r'얼마|몇',q)):return None
    if displacement_target:op='michelson_displacement'
    elif re.search(r'광자|에너지|ev',q) and ('파장' in q or '광자' in q or re.search(UNIT,q)):op='photon_energy'
    elif re.search(r'xrd|브래그|브레그|회절각|2θ|2세타',q):op='bragg_angle'
    elif re.search(r'마이[켈컬]|michelson|거울.*이동',q) or ('무늬' in q and active_document in (None,'michelson-interferometer')):op='michelson_fringes' if re.search(r'(?:파장|λ)\s*[=:]?\s*'+NUM+r'\s*'+UNIT,q) else 'michelson_wavelength' if '파장' in q or 'wavelength' in q else 'michelson_fringes'
    elif re.search(r'편광|말뤼스|투과율',q):op='malus'
    elif re.search(r'렌즈|초점거리|상 거리',q) and not re.search(r'망원경|현미경|접안|대물',q):op='thin_lens'
    elif re.search(r'계산|구해|얼마|몇',q) and snapshot.get('default_operation') in SPECS:
        op=snapshot['default_operation']
        if op.startswith('michelson') and '파장' in q:op='michelson_wavelength'
    else:return None
    params={};origins={};ambiguous=set()
    labels={'wavelength':r'파장|λ|lambda','spacing':r'면간격|면 간격|\bd\b','displacement':r'거울 이동|이동량|변위|Δx|Δd|거울(?:을)?','focal':r'초점거리|초점 거리|\bf\b','object_distance':r'물체 거리|물체거리|\bu\b|\bs\b'}
    for key in SPECS[op][2]:
        for text,origin in [(user,'question'),(context,'experiment_snapshot')]:
            # 브라우저가 전송한 구조화 값은 설명문 속 숫자보다 우선한다.
            if origin=='experiment_snapshot' and key in snapshot.get('parameters',{}):
                continue
            if key in labels:
                matches=re.findall(r'(?:'+labels[key]+r')\s*(?:\([^)]*\))?\s*[=:은는을를]?\s*('+NUM+r')\s*('+UNIT+r')(?![a-z])',text,re.I)
                if op=='photon_energy' and origin=='question':
                    all_lengths=re.findall(r'('+NUM+r')\s*('+UNIT+r')(?![a-z])',text,re.I)
                    if len({(float(x),u) for x,u in all_lengths})>1:matches=all_lengths
                # 광자 단일 파장 및 거울 단일 이동량에만 문맥이 명확한 무명 길이를 허용한다.
                if not matches and origin=='question' and (op=='photon_energy' or (key=='displacement' and op.startswith('michelson'))):
                    matches=re.findall(r'('+NUM+r')\s*('+UNIT+r')(?![a-z])',text,re.I)
            elif key=='angle':
                matches=re.findall(r'('+NUM+r')\s*(deg|rad|°|도)',text,re.I)
            else:
                pattern=(r'(?:무늬|주기)\s*(?:수)?\s*[=:은는]?\s*('+NUM+r')\s*(개|회|주기)?' if key=='fringes' else r'('+NUM+r')\s*(차)')
                matches=re.findall(pattern,text,re.I)
                if key=='fringes' and not matches:matches=re.findall(r'('+NUM+r')\s*(개|주기)',text,re.I)
            unique={(float(x),u) for x,u in matches}
            if len(unique)==1:
                x,u=next(iter(unique));params[key]={'value':x,'unit':'count' if key in ('fringes','order') else 'deg' if u in ('°','도') else u.lower()};origins[key]=origin;break
            if len(unique)>1:
                ambiguous.add(key);break
    # 브라우저 입력도 단위·범위 검증을 통과해야 한다. 질문에서 명시한 값이 우선이다.
    if isinstance(snapshot.get('parameters'),dict):
        for key in SPECS[op][2]:
            if key not in params and key not in ambiguous and key in snapshot['parameters']:
                params[key]=snapshot['parameters'][key];origins[key]='experiment_snapshot'
    if op=='thin_lens' and '오목' in q and isinstance(params.get('focal'),dict) and isinstance(params['focal'].get('value'),(int,float)):
        params['focal']={**params['focal'],'value':-abs(params['focal']['value'])}
    if op=='bragg_angle' and 'order' not in params:
        params['order']={'value':1,'unit':'count'};origins['order']='assumed_first_order'
    return {'operation':op,'parameters':params,'origins':origins,'document':SPECS[op][1]}

def format_calculation(data:dict) -> str:
    """검증된 수치·단위만 표시하는 결정론적 작성. 오류 상태에서는 계산값을 만들지 않는다."""
    if data.get('operation') in ('inquiry','parameter_definition'):
        from .inquiry_calculations import format_inquiry
        return format_inquiry(data)
    if not data.get('ok'):
        names={'wavelength':'진공 파장(예: 532 nm)','spacing':'면간격(예: 0.3 nm)','order':'회절 차수','displacement':'거울 이동량(예: 0.1 mm)','fringes':'무늬 주기 수','angle':'상대각(예: 45도)','focal':'초점거리(예: 10 cm)','object_distance':'물체 거리(예: 30 cm)'}
        reason='다음 값이 필요합니다: '+', '.join(names[x] for x in data['missing']) if data.get('missing') else data['message']
        return f"**계산을 완료하지 못했습니다.** {reason}\n\n공식: {data['formula']}\n조건을 확인해 다시 입력해 주세요."
    rows='\n'.join(f"- **{r['name']}: {r['value']:.6g} {r['unit']}**" for r in data['results'])
    inputs=', '.join(f"{k}={v['value']:g} {v['unit']}" for k,v in data['inputs'].items())
    source=data['source'].rsplit('/',1)[-1]
    provenance = '\n\n입력 출처: '+', '.join(f"{k}: { {'question':'질문','experiment_snapshot':'현재 가상실험','assumed_first_order':'1차 가정'}[v]}" for k,v in data.get('input_origins',{}).items()) if data.get('input_origins') else ''
    return f"{rows}\n\n입력: {inputs}{provenance}\n\n공식: {data['formula']}\n\n적용 조건: {data['assumptions']}\n\n출처: [{source}](/documents/{source}) · MCP `calculate_optics` 계산. 실험값이 아닌 입력 기반 이론값입니다."
