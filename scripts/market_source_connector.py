from __future__ import annotations

from pathlib import Path
import json, re, argparse
from datetime import datetime, timezone
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
TARGETS=ROOT/"config/market-automation-targets.json"
REPORT=ROOT/"data/candidate/market/market-source-connector-report.json"
HEADERS={"User-Agent":"Mozilla/5.0 (compatible; RealEstateMarketIntelligence/1.0; +https://github.com/SanS-91/real-estate)"}

def read_json(p, default=None):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default

def write_json(p, payload):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def page_meta(html):
    soup=BeautifulSoup(html,"lxml")
    title=(soup.title.get_text(" ",strip=True) if soup.title else None)
    desc=None
    tag=soup.find("meta",attrs={"name":re.compile("^description$",re.I)})
    if tag and tag.get("content"): desc=tag["content"].strip()
    text=soup.get_text(" ",strip=True)
    dates=re.findall(r"\b(?:20\d{2})[-/.](?:0?[1-9]|1[0-2])[-/.](?:0?[1-9]|[12]\d|3[01])\b",text)
    return {"title":title,"description":desc,"date_mentions":dates[:10],"text_length":len(text)}

def probe(target):
    url=target["url"]
    try:
        r=requests.get(url,headers=HEADERS,timeout=20,allow_redirects=True)
        out={"target_id":target["target_id"],"source_id":target["source_id"],"url":url,
             "final_url":r.url,"http_status":r.status_code}
        if r.status_code==200:
            out.update(page_meta(r.text))
            out["status"]="reachable"
        elif r.status_code in (401,403,429):
            out["status"]="blocked"
        else:
            out["status"]="http-error"
        return out
    except Exception as e:
        return {"target_id":target["target_id"],"source_id":target["source_id"],"url":url,
                "status":"fetch-error","error":str(e)[:300]}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--target",action="append",default=[])
    args=ap.parse_args()
    cfg=read_json(TARGETS,{"targets":[]})
    selected=[x for x in cfg.get("targets",[]) if x.get("enabled") and (not args.target or x["target_id"] in set(args.target))]
    rows=[probe(x) for x in selected]
    counts={s:sum(1 for x in rows if x["status"]==s) for s in sorted({x["status"] for x in rows})}
    payload={
      "schema_version":1,
      "generated_at":datetime.now(timezone.utc).isoformat(),
      "targets_checked":len(rows),
      "counts":counts,
      "sources":rows,
      "production_written":False,
      "note":"Phase 5.5F access/discovery probe only. No market observation is promoted automatically."
    }
    write_json(REPORT,payload)
    print(json.dumps(payload,ensure_ascii=False,indent=2))
if __name__=="__main__":
    main()
