"""실제 HTTP SSE의 첫 표시 가능 답변·완료 시간과 원답 기록. 서버는 별도 실행한다."""
import argparse,asyncio,json,time
from pathlib import Path
import httpx

async def main(args):
    wanted=set(args.ids.split(','));cases=[c for c in json.loads(Path(args.cases).read_text()) if c['id'] in wanted];rows=[]
    async with httpx.AsyncClient(timeout=180) as client:
        for c in cases:
            started=time.perf_counter();row={'id':c['id'],'first_answer_seconds':None,'event_types':[]}
            async with client.stream('GET',args.url+'/chat/stream',params={'message':c['message'],'thread_id':'audit-'+c['id']+'-'+str(time.time_ns())}) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith('data: '):continue
                    if line=='data: [DONE]':row['done']=True;break
                    event=json.loads(line[6:]);kind=event.get('type');row['event_types'].append(kind)
                    if kind in ('AnswerToken','FinalAnswer') and row['first_answer_seconds'] is None:row['first_answer_seconds']=round(time.perf_counter()-started,3)
                    if kind=='FinalAnswer':row['answer']=event['reply']
                    if kind=='Error':row['error']=event.get('message')
            row['total_seconds']=round(time.perf_counter()-started,3);rows.append(row)
            Path(args.output).write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n');print(row['id'],row['total_seconds'],row.get('done'),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:18100');p.add_argument('--cases',default='eval/fixtures/inquiry_cases.json');p.add_argument('--ids',required=True);p.add_argument('--output',required=True);asyncio.run(main(p.parse_args()))
