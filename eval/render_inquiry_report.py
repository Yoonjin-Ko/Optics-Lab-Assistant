"""실모델 원답·시간과 수동 내용 검토를 합친다. 미검토/원답 변경은 통과로 세지 않는다."""
import argparse,hashlib,json,math,statistics
from pathlib import Path


def main(args):
    rows=json.loads(Path(args.results).read_text());reviews=json.loads(Path(args.reviews).read_text())
    counts={s:0 for s in ['pass','partial','fail','unreviewed']}
    for row in rows:
        review=reviews.get(row['id'],{})
        digest=hashlib.sha256(row.get('answer','').encode()).hexdigest()
        if review.get('answer_sha256')!=digest:review={'status':'unreviewed','review':'원답과 일치하는 내용 검토 기록 없음'}
        row['content_review']=review;counts[review['status']]+=1
    output=Path(args.output);output.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    times=sorted(r['total_seconds'] for r in rows)
    first=[r['first_token_seconds'] for r in rows if r.get('first_token_seconds') is not None]
    lines=['# 탐구 질문 실모델 검증','', '확인일: 2026-10-21 · 로컬 Ollama qwen3:8b · 실제 MCP 문서/계산 호출.','',f"실행 {len(rows)}건 · 내용 통과 {counts['pass']} · 부분 충족 {counts['partial']} · 실패 {counts['fail']} · 미검토 {counts['unreviewed']}",'',f"완료 시간 중앙값 {statistics.median(times):.2f}초 · P95 {times[math.ceil(len(times)*.95)-1]:.2f}초 · 최대 {max(times):.2f}초."]
    if first:lines.append(f'모델 답변 첫 조각까지 중앙값 {statistics.median(first):.2f}초. 계산 도구만 사용한 답변은 모델 토큰 시간이 없습니다.')
    lines+=['','위 시간은 그래프 입력부터 첫 토큰/최종 답변까지입니다. 브라우저 렌더링 시간은 포함하지 않습니다. 성공 응답이나 형식 검사 통과를 내용 정답으로 간주하지 않았습니다.','', '이 결과는 저장된 질문·설정과 이번 실행에 한정됩니다. 모든 광학 질문이나 모든 조절값에 대한 정확도 보장이 아닙니다.','', '[원답·입력·시간 기록](../eval/inquiry_live_results.json) · [재실행 입력](../eval/fixtures/inquiry_cases.json) · [판정 기준](../eval/fixtures/inquiry_criteria.json)','', '| 질문 ID | 질문 | 첫 조각(초) | 완료(초) | 내용 판정 | 검토 |','| --- | --- | ---: | ---: | --- | --- |']
    labels={'pass':'통과','partial':'부분 충족','fail':'실패','unreviewed':'미검토'}
    for r in rows:
        review=r['content_review'];first=r.get('first_token_seconds');note=review.get('review','').replace('|','/')
        lines.append(f"| {r['id']} | {r['question']} | {first if first is not None else '계산 경로'} | {r['total_seconds']} | {labels[review['status']]} | {note} |")
    Path(args.report).write_text('\n'.join(lines)+'\n')
    print(counts)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--results',required=True);p.add_argument('--reviews',required=True);p.add_argument('--output',required=True);p.add_argument('--report',required=True);main(p.parse_args())
