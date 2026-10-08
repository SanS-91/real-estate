#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re
from datetime import datetime, timezone
from pathlib import Path
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
PROJECTS=ROOT/"data/mock/infrastructure/projects.json"
SCHEDULES=ROOT/"data/mock/infrastructure/schedules.json"
SOURCES=ROOT/"data/mock/core/sources.json"
WATCH=ROOT/"data/candidate/registry/watch-report.json"
CAND=ROOT/"data/candidate/infrastructure/updates.json"
REPORT=ROOT/"data/candidate/infrastructure/infrastructure-candidate-report.json"
HEADERS={"User-Agent":"VietnamRealEstateMarketIntelligence/1.0 (+GitHub Actions infrastructure candidate collector)"}

PROJECT_ALIASES={
  "long-thanh-airport":["sân bay long thành","cảng hkqt long thành","cảng hàng không quốc tế long thành"],
  "hcmc-ring-road-3":["vành đai 3 tphcm","vành đai 3 thành phố hồ chí minh","đường vành đai 3"],
  "ben-luc-long-thanh-expressway":["bến lức - long thành","bến lức – long thành","cao tốc bến lức"],
  "hcmc-metro-line-1":["metro số 1","bến thành - suối tiên","bến thành – suối tiên"],
  "hcmc-moc-bai-expressway":["tphcm - mộc bài","tphcm – mộc bài","cao tốc tp.hcm - mộc bài","cao tốc tphcm – mộc bài"],
  "hcmc-ring-road-4":["vành đai 4 tphcm","vành đai 4 thành phố hồ chí minh","đường vành đai 4"],
  "bien-hoa-vung-tau-expressway":["biên hòa - vũng tàu","biên hòa – vũng tàu","cao tốc biên hòa"],
  "hcmc-long-thanh-expansion":["mở rộng cao tốc tphcm - long thành","mở rộng cao tốc tphcm – long thành","mở rộng cao tốc tp.hcm - long thành","cao tốc tphcm - long thành - dầu giây","cao tốc tphcm – long thành – dầu giây"]
}

def load(p,default=None):
    return json.loads(Path(p).read_text(encoding="utf-8")) if Path(p).exists() else default

def dump(p,obj):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def norm(s):
    return re.sub(r"\s+"," ",str(s or "")).strip()

def slug(s):
    s=s.lower()
    s=re.sub(r"[^a-z0-9]+","-",s).strip("-")
    return s[:100]

def text_of(html):
    soup=BeautifulSoup(html,"lxml")
    for t in soup(["script","style","noscript"]): t.decompose()
    return soup,norm(soup.get_text(" ",strip=True))

def find_project_id(text):
    tl=text.lower()
    matches=[]
    for pid,aliases in PROJECT_ALIASES.items():
        if any(a in tl for a in aliases):
            matches.append(pid)
    # Prefer the longest/most specific alias family when multiple names occur.
    if len(matches)==1: return matches[0]
    if matches:
        scores={}
        for pid in matches:
            scores[pid]=max((len(a) for a in PROJECT_ALIASES[pid] if a in tl),default=0)
        return sorted(matches,key=lambda x:scores[x],reverse=True)[0]
    return None

def announced_date(text):
    patterns=[
      r"\b([0-3]?\d)[/-]([01]?\d)[/-](20\d{2})\b",
      r"ngày\s+([0-3]?\d)\s+tháng\s+([01]?\d)\s+năm\s+(20\d{2})"
    ]
    for p in patterns:
        m=re.search(p,text,re.I)
        if m:
            d,mn,y=m.groups()
            return f"{int(y):04d}-{int(mn):02d}-{int(d):02d}"
    return None

def quarter(year,month):
    return f"{year}-Q{((month-1)//3)+1}"

def target_period(text):
    tl=text.lower()
    patterns=[
      (r"(?:hoàn thành|thông xe|khai thác|đưa vào khai thác)[^\.]{0,100}?quý\s*([1-4])[/\s-]*(20\d{2})",lambda m:f"{m.group(2)}-Q{m.group(1)}","quarter"),
      (r"(?:hoàn thành|thông xe|khai thác|đưa vào khai thác)[^\.]{0,100}?q([1-4])[/\s-]*(20\d{2})",lambda m:f"{m.group(2)}-Q{m.group(1)}","quarter"),
      (r"(?:cuối|trong)\s+năm\s+(20\d{2})",lambda m:m.group(1),"year"),
      (r"(?:hoàn thành|thông xe|khai thác|đưa vào khai thác)[^\.]{0,100}?(20\d{2})",lambda m:m.group(1),"year"),
    ]
    for p,fn,precision in patterns:
        m=re.search(p,tl,re.I)
        if m: return fn(m),precision
    return None,None

def operation_date(text):
    tl=text.lower()
    m=re.search(r"(?:chính thức\s+)?(?:thông xe|đưa vào khai thác|vận hành)[^\.]{0,100}?([0-3]?\d)[/-]([01]?\d)[/-](20\d{2})",tl,re.I)
    if not m: return None
    d,mn,y=map(int,m.groups())
    return f"{y:04d}-{mn:02d}-{d:02d}"

def progress_percent(text):
    tl=text.lower()
    patterns=[
      r"(?:tiến độ|khối lượng|sản lượng)[^%]{0,80}?(?:đạt|khoảng|trên|hơn)?\s*(\d{1,3}(?:[.,]\d+)?)\s*%",
      r"(?:đạt|hoàn thành)\s*(\d{1,3}(?:[.,]\d+)?)\s*%[^\.]{0,60}?(?:khối lượng|tiến độ|sản lượng)"
    ]
    for p in patterns:
        m=re.search(p,tl,re.I)
        if m:
            val=float(m.group(1).replace(",","."))
            if 0<=val<=100: return val
    return None

def investment_bn(text):
    tl=text.lower()
    m=re.search(r"(?:tổng mức đầu tư|tổng vốn đầu tư)[^\d]{0,40}([\d.,]+)\s*(?:tỷ đồng|tỷ)",tl,re.I)
    if not m: return None
    raw=m.group(1)
    # Vietnamese thousands separators are commonly dots.
    digits=re.sub(r"\D","",raw)
    return int(digits) if digits else None

def source_id(url):
    u=url.lower()
    if "dongnai.gov.vn" in u: return "dongnai-public-infrastructure"
    if "hochiminhcity.gov.vn" in u or "hdnd.hochiminhcity.gov.vn" in u: return "hcmc-public-infrastructure"
    return "gov-vietnam-infrastructure"

def parse(html,url,fetched_at):
    soup,text=text_of(html)
    pid=find_project_id(text)
    announced=announced_date(text)
    op_date=operation_date(text)
    target,precision=target_period(text)
    progress=progress_percent(text)
    investment=investment_bn(text)

    schedule=None
    if op_date:
        y,m,_=map(int,op_date.split("-"))
        schedule={
          "infrastructure_project_id":pid,
          "schedule_type":"operation-start",
          "target_period":quarter(y,m),
          "date_precision":"quarter",
          "announced_date":announced or op_date,
          "source_id":source_id(url),
          "source_url":url
        }
    elif target:
        schedule={
          "infrastructure_project_id":pid,
          "schedule_type":"expected-completion",
          "target_period":target,
          "date_precision":precision,
          "announced_date":announced,
          "source_id":source_id(url),
          "source_url":url
        }

    patch={}
    if progress is not None:
        patch["current_progress_percent"]=progress
        patch["current_progress_note"]=norm(text[:1200])
    if investment is not None:
        patch["current_total_investment"]=investment
        patch["investment_currency"]="VND"
        patch["investment_unit"]="bn"
    tl=text.lower()
    if any(k in tl for k in ["chính thức thông xe","đưa vào khai thác","vận hành chính thức"]):
        patch["status"]="operational"
    elif "khởi công" in tl:
        patch["status"]="under-construction"

    return {
      "project_id":pid,
      "title":norm((soup.find("h1").get_text(" ",strip=True) if soup.find("h1") else (soup.title.get_text(" ",strip=True) if soup.title else "Infrastructure update"))),
      "announced_date":announced,
      "schedule_candidate":schedule,
      "project_patch":patch,
      "source_id":source_id(url),
      "source_url":url,
      "collector_provenance":{"capture_mode":"official-update-parser","fetched_at":fetched_at,"review_required":True}
    }

def schedule_key(row):
    return (row.get("infrastructure_project_id"),row.get("schedule_type"),row.get("target_period"),row.get("source_url"))

def validate(update):
    issues=[]
    if not update.get("project_id"): issues.append("project match requires review")
    if not update.get("announced_date"): issues.append("announced date requires review")
    if not update.get("schedule_candidate") and not update.get("project_patch"):
        issues.append("no structured change extracted")
    return issues

def collect_urls(args):
    urls=list(args.url or [])
    if args.from_watch and WATCH.exists():
        w=load(WATCH,{"discovery_links":[]})
        urls += [x["url"] for x in w.get("discovery_links",[]) if x.get("module")=="infrastructure" and x.get("new_since_previous_check")]
    out=[]; seen=set()
    for u in urls:
        if u and u not in seen: seen.add(u); out.append(u)
    return out

def fetch(url):
    r=requests.get(url,headers=HEADERS,timeout=20,allow_redirects=True)
    r.raise_for_status()
    return r.url,r.text,datetime.now(timezone.utc).isoformat()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--url",action="append",default=[])
    ap.add_argument("--from-watch",action="store_true")
    ap.add_argument("--fixture")
    ap.add_argument("--fixture-url",default="https://baochinhphu.vn/fixture-infrastructure-update.htm")
    args=ap.parse_args()

    projects=load(PROJECTS,{"data":[]}).get("data",[])
    project_ids={x["id"] for x in projects}
    schedules=load(SCHEDULES,{"data":[]}).get("data",[])
    schedule_keys={schedule_key(x) for x in schedules}
    rows=[]; reports=[]

    inputs=[]
    if args.fixture:
        inputs=[(args.fixture_url,Path(args.fixture).read_text(encoding="utf-8"),datetime.now(timezone.utc).isoformat())]
    else:
        for url in collect_urls(args):
            try: inputs.append(fetch(url))
            except Exception as e: reports.append({"url":url,"status":"fetch-error","error":str(e)[:300]})

    for final_url,html,fetched_at in inputs:
        update=parse(html,final_url,fetched_at)
        issues=validate(update)
        pid=update.get("project_id")
        if pid and pid not in project_ids:
            issues.append("unknown project_id")
        schedule=update.get("schedule_candidate")
        sched_state=None
        if schedule:
            sched_state="unchanged" if schedule_key(schedule) in schedule_keys else "new"
        patch=update.get("project_patch") or {}
        project=next((x for x in projects if x["id"]==pid),None)
        patch_changes={k:{"from":project.get(k),"to":v} for k,v in patch.items() if project and project.get(k)!=v}
        patch_state="changed" if patch_changes else ("unchanged" if patch else None)

        if (sched_state=="new" or patch_state=="changed") and pid:
            row={
              "id":"candidate-infra-"+slug(pid+"-"+(update.get("announced_date") or "undated")+"-"+str(len(rows)+1)),
              **update,
              "schedule_decision":sched_state,
              "project_patch_decision":patch_state,
              "project_patch_changes":patch_changes,
              "review_issues":issues
            }
            rows.append(row)

        reports.append({
          "url":final_url,"status":"parsed","project_id":pid,
          "schedule_decision":sched_state,"project_patch_decision":patch_state,
          "review_issues":issues
        })

    payload={"schema_version":1,"generated_at":datetime.now(timezone.utc).isoformat(),"candidate_only":True,"record_count":len(rows),"data":rows}
    report={"schema_version":1,"generated_at":payload["generated_at"],"production_written":False,"candidate_count":len(rows),"results":reports}
    dump(CAND,payload); dump(REPORT,report)
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
