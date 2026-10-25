"""GitHub Pages용 가벼운 RSS 수집기. 전문 요약이 아닌 제목·RSS 설명 기반 요약."""
import concurrent.futures, datetime, email.utils, hashlib, html, json, pathlib, re, urllib.parse, urllib.request, xml.etree.ElementTree as ET
ROOT=pathlib.Path(__file__).resolve().parent
QUERIES=[('국내','상업용 부동산 오피스 물류센터 투자 리츠 when:2d','ko','KR'),('해외','commercial real estate investment office logistics refinancing when:2d','en-US','US')]
def clean(s): return re.sub(r'\s+',' ',re.sub('<[^>]+>',' ',html.unescape(s or ''))).strip()
def fetch_feed(spec):
 region,q,lang,country=spec
 url='https://news.google.com/rss/search?'+urllib.parse.urlencode({'q':q,'hl':lang,'gl':country,'ceid':country+':'+('ko' if country=='KR' else 'en')})
 req=urllib.request.Request(url,headers={'User-Agent':'EstateBrief/1.0 RSS Reader'})
 with urllib.request.urlopen(req,timeout=25) as r: root=ET.fromstring(r.read())
 out=[];now=datetime.datetime.now(datetime.timezone.utc)
 for item in root.findall('./channel/item'):
  title=clean(item.findtext('title'));source=clean(item.findtext('source'));link=item.findtext('link','')
  try: published=email.utils.parsedate_to_datetime(item.findtext('pubDate'))
  except Exception: continue
  if published>now or (now-published).total_seconds()>72*3600 or not link.startswith('https://'):continue
  title=title.removesuffix(' - '+source)
  sector=next((label for label,pattern in [('데이터센터',r'data cent|데이터센터'),('물류',r'logistic|industrial|물류'),('리빙',r'multifamily|living|housing|리빙|주거'),('리테일',r'retail|리테일'),('호텔',r'hotel|호텔'),('오피스',r'office|오피스')] if re.search(pattern,title,re.I)),'복합')
  desc=clean(item.findtext('description'))
  summary=(desc[:230] if desc and desc!=title else title)+' (RSS 제목·설명 기반, 세부 내용은 원문 확인)'
  out.append(dict(id=hashlib.sha256(title.casefold().encode()).hexdigest()[:18],title=title,summary=summary,source=source or 'Google News RSS',publishedAt=published.astimezone(datetime.timezone(datetime.timedelta(hours=9))).date().isoformat(),region=region,sector=sector,type='기사',url=link))
 return out
if __name__=='__main__':
 items=[];errors=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  for f in [pool.submit(fetch_feed,q) for q in QUERIES]:
   try:items.extend(f.result())
   except Exception as e:errors.append(type(e).__name__)
 if errors:raise SystemExit('RSS source failed; retaining previous briefing: '+','.join(errors))
 unique={};
 for a in items: unique.setdefault(re.sub(r'\W','',a['title']).casefold(),a)
 items=sorted(unique.values(),key=lambda a:a['publishedAt'],reverse=True)
 fallback=json.loads((ROOT/'briefing.json').read_text())
 if len(items)<5:
  for a in fallback['highlights']:
   if a['id'] not in {x['id'] for x in items}:
    a=dict(a);a['summary']='[이전 참고자료] '+a['summary'];items.append(a)
   if len(items)>=5:break
 if len(items)<5:raise SystemExit('Fewer than 5 verified items; retaining previous briefing')
 # 국내/해외 각각 적어도 1개. 나머지는 최신순으로 채운다.
 main=[]
 for region in ['국내','해외']:
  if first:=next((a for a in items if a['region']==region),None):main.append(first)
 for a in items:
  if len(main)==5:break
  if a not in main:main.append(a)
 now=datetime.datetime.now(datetime.timezone.utc);date=now.astimezone(datetime.timezone(datetime.timedelta(hours=9))).date().isoformat()
 data=dict(date=date,updatedAt=now.isoformat(),edition='RSS 자동 브리핑',intro='국내·해외 공개 RSS에서 선별한 최신 소식입니다. 제목·RSS 설명 기반 자동 요약으로, 주요 수치와 거래 조건은 원문에서 확인해 주세요.',highlights=main,additional=[a for a in items if a not in main][:15])
 (ROOT/'briefing.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
 print('Collected',len(items),'items; selected 5 highlights')
