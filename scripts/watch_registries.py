#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def dump(p,obj):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def now_iso(): return datetime.now(timezone.utc).isoformat()
def text_hash(html):
    soup=BeautifulSoup(html,"lxml")
    for tag in soup(["script","style","noscript"]): tag.decompose()
    txt=re.sub(r"\s+"," ",soup.get_text(" ",strip=True)).strip()
    return hashlib.sha256(txt.encode("utf-8","ignore")).hexdigest() if txt else None
def valid_url(u):
    p=urlparse(u); return p.scheme in {"http","https"} and bool(p.netloc)

def targets(cfg):
    out=[]
    for module,m in cfg["modules"].items():
        payload=load(ROOT/m["canonical_path"])
        seen=set()
        for row in payload.get("data",[]):
            url=row.get(m["url_field"])
            if url and url not in seen:
                seen.add(url); out.append({"module":module,"entity_id":row.get(m["entity_id_field"]) or row.get("id"),"url":url,"discovery":False})
        for url in m.get("discovery_pages",[]):
            out.append({"module":module,"entity_id":"__discovery__","url":url,"discovery":True})
    return out

def fetch_one(t,cfg):
    try:
        r=requests.get(t["url"],headers={"User-Agent":cfg["user_agent"]},timeout=cfg["timeout_seconds"],allow_redirects=True)
        return {**t,"ok":bool(r.ok),"status_code":r.status_code,"final_url":r.url,"content_sha256":text_hash(r.text) if r.ok else None,"fetched_at":now_iso(),"error":None,"html":r.text if r.ok and t["discovery"] else None}
    except Exception as exc:
        return {**t,"ok":False,"status_code":None,"final_url":t["url"],"content_sha256":None,"fetched_at":now_iso(),"error":str(exc),"html":None}

def discover(result,cfg):
    html=result.get("html")
    if not html: return []
    kws=[x.lower() for x in cfg["modules"][result["module"]].get("discovery_keywords",[])]
    soup=BeautifulSoup(html,"lxml"); found=[]; seen=set()
    for a in soup.find_all("a",href=True):
        title=re.sub(r"\s+"," ",a.get_text(" ",strip=True)).strip()
        if not title or not any(k in title.lower() for k in kws): continue
        url=urljoin(result["final_url"],a["href"])
        if valid_url(url) and url not in seen:
            seen.add(url); found.append({"module":result["module"],"title":title[:300],"url":url})
    return found[:100]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--config",default="config/registry_watch.json")
    ap.add_argument("--cache",default="data/state/registry-watch-cache.json")
    ap.add_argument("--output",default="data/candidate/registry/watch-report.json")
    args=ap.parse_args()
    cfg=load(ROOT/args.config); cache_path=ROOT/args.cache
    prev=load(cache_path) if cache_path.exists() else {"targets":{},"discovery_links":[]}
    results=[]
    with ThreadPoolExecutor(max_workers=int(cfg.get("max_workers",6))) as ex:
        futs=[ex.submit(fetch_one,t,cfg) for t in targets(cfg)]
        for f in as_completed(futs): results.append(f.result())
    prev_t=prev.get("targets",{}); links=[]
    for r in results:
        old=prev_t.get(r["url"],{})
        r["changed_since_previous_check"]=bool(old.get("content_sha256") and r.get("content_sha256") and old["content_sha256"]!=r["content_sha256"])
        links.extend(discover(r,cfg))
        r.pop("html",None)
    has_previous_baseline=bool(prev.get("generated_at"))
    prev_links={x.get("url") for x in prev.get("discovery_links",[])}
    # First successful capture establishes a comparison baseline; do not
    # describe every existing discovery link as a newly published event.
    for x in links: x["new_since_previous_check"]=has_previous_baseline and x["url"] not in prev_links
    results.sort(key=lambda x:(x["module"],x["url"]))
    report={
      "schema_version":1,"generated_at":now_iso(),"mode":cfg["mode"],"auto_publish":False,
      "previous_baseline_available":has_previous_baseline,
      "target_count":len(results),"healthy_count":sum(1 for x in results if x["ok"]),
      "failed_count":sum(1 for x in results if not x["ok"]),
      "changed_target_count":sum(1 for x in results if x["changed_since_previous_check"]),
      "new_discovery_link_count":sum(1 for x in links if x["new_since_previous_check"]),
      "status":"healthy" if all(x["ok"] for x in results) else "degraded",
      "targets":results,"discovery_links":links
    }
    dump(ROOT/args.output,report)
    dump(cache_path,{"schema_version":1,"generated_at":report["generated_at"],"targets":{x["url"]:{"content_sha256":x["content_sha256"],"status_code":x["status_code"]} for x in results},"discovery_links":[{"module":x["module"],"title":x["title"],"url":x["url"]} for x in links]})
    print(f"Registry watch: {report['status']} · targets={report['target_count']} · changed={report['changed_target_count']} · new-links={report['new_discovery_link_count']}")
if __name__=="__main__": main()
