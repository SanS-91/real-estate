#!/usr/bin/env python3
"""Source-gated Market terms and FS readiness; never infer missing net price or PV.

Reported financing and bank-support terms must not be misrepresented as
developer contractual customer receipts. Only a verified net contract price,
complete dated net-price collection schedule, current first-party evidence,
and an explicitly supplied comparison discount rate permit PV calculation.
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlsplit
import hashlib, json, argparse

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/"data/mock/market/sales-policy-evidence.json"
SOURCES=ROOT/"data/mock/core/sources.json"
PROJECTS=ROOT/"data/mock/market/projects.json"
OUT=ROOT/"data/processed/market/sales-policy-readiness.json"
WATCHLIST=["izumi-city","aqua-city","springville","elyse-island","kita-airport-city","nam-long-ii-central-lake"]
OFFICIAL_HOSTS={"nam-long-official":"www.namlongvn.com",
                "novaland-official":"www.novaland.com.vn",
                "gamuda-land-official":"www.gamudaland.com.vn",
                "kita-group-official":"kita-group.com.vn"}
VALID_STATUSES={"official-milestone-only","third-party-claim-unverified-current-applicability",
                "historical-unknown-validity","verified-current-contractual-policy"}
def load(p):return json.loads(p.read_text(encoding="utf-8"))
def positive(x):return type(x) in (int,float) and x>0

def calc_pv_if_complete(policy, annual_rate, valuation_date):
    """One customer contract net-price PV for FULL dated net buyer payments.
    This is NOT developer operating CF (lender draws, fees and subsidy need
    their own legally verified receipt/expense schedule). No partial PV output.
    """
    if not type(annual_rate) in (int,float) or not 0<=annual_rate<=1:
        raise ValueError("Explicit annual opportunity discount rate from 0 to 100% required")
    price=policy.get("verified_net_price_vnd")
    contract=policy.get("verified_contract")
    schedule=policy.get("verified_full_instalments")
    if policy.get("status")!="verified-current-contractual-policy" or not policy.get("official_price_list_verified") or not policy.get("net_price_verified"):
        return None
    if not positive(price) or not isinstance(contract,dict) or not contract.get("is_current"):
        return None
    if not policy.get("discount_stacking_verified") or not policy.get("verified_vat_basis"):
        return None
    if not isinstance(schedule,list) or len(schedule)<2:
        return None
    observed=policy.get("source_publication_date")
    effective=policy.get("valid_from")
    expires=policy.get("valid_until")
    if not (observed and effective and expires) or not (date.fromisoformat(effective)<=valuation_date<=date.fromisoformat(expires)):
        return None
    fractions=[]
    for item in schedule:
        if not isinstance(item,dict) or not item.get("due_date") or item.get("due_basis")!="contractual-exact-date":
            return None
        if not type(item.get("pct_of_net_price")) in (int,float) or not 0<item["pct_of_net_price"]<=100:
            return None
        due=date.fromisoformat(item["due_date"])
        if due < valuation_date:
            return None # no assumption of historic payment recoverability
        fractions.append((due,item["pct_of_net_price"]/100))
    if abs(sum(f for _,f in fractions)-1)>1e-8:return None
    return round(price*sum(f/(1+annual_rate)**((due-valuation_date).days/365.0) for due,f in fractions))

def evaluate(row,source_ids,project_ids,as_of):
    sid=row["source_id"]
    if sid not in source_ids or row["project_id"] not in project_ids:
        raise ValueError(f"Unregistered project/source {row.get('id')}")
    if row["status"] not in VALID_STATUSES:raise ValueError("Unknown source policy status")
    u=urlsplit(row["source_url"])
    if u.scheme!="https" or not u.hostname:
        raise ValueError("Policy must contain a secure source URL")
    if row["source_role"]=="developer-primary":
        if OFFICIAL_HOSTS.get(sid)!=u.hostname:
            raise ValueError("A third-party site cannot impersonate a first-party source")
    elif row["source_role"]=="third-party-commercial-site-not-verified-corporate-domain":
        if sid!="tapdoannamlong-secondary" or u.hostname!="tapdoannamlong.com":
            raise ValueError("Unverified third-party publisher must be explicit")
    else:raise ValueError("Unknown policy publisher role")
    reviewed=date.fromisoformat(row["review_date"])
    if reviewed>as_of:raise ValueError("Future review is not verified")
    if row.get("source_publication_date") and date.fromisoformat(row["source_publication_date"])>reviewed:
        raise ValueError("Future publication date")
    terms=row["published_terms"]
    for field in ("advertised_upfront_pct","guaranteed_post_handover_pct","retention_title_pct"):
        if terms.get(field) is not None and (type(terms[field]) not in (int,float) or not 0<terms[field]<=100):
            raise ValueError("Invalid payment share")
    requested=["official-current-campaign-and-applicable-unit","verified-unit-price-and-VAT-basis",
                "verified-discounts-and-stacking","100pct-net-buyer-payments-with-exact-dates",
                "contractual-HO-and-title-milestones","bank-support-cash-flow-terms-if-applicable"]
    # No current offer can be inferred from the presence of promotional ratios.
    eligible=bool(row.get("status")=="verified-current-contractual-policy" and
                  row.get("source_role")=="developer-primary" and
                  row.get("official_price_list_verified") and row.get("net_price_verified") and
                  row.get("discount_stacking_verified") and
                  row.get("verified_vat_basis") and row.get("verified_net_price_vnd") and
                  row.get("verified_contract",{}).get("is_current") and
                  row.get("verified_full_instalments") and
                  row.get("valid_from") and row.get("valid_until"))
    return {
      "id":row["id"],"project_id":row["project_id"],"phase_name":row.get("phase_name"),
      "product_types":row.get("product_types",[]),"source_id":sid,"source_url":row["source_url"],
      "source_role":row["source_role"],"review_date":row["review_date"],
      "source_publication_date":row.get("source_publication_date"),
      "status":row["status"],"evidence_type":row["evidence_type"],"scope":row["scope"],
      "published_terms":terms,"methodology_note":row["methodology_note"],
      "verified_net_selling_price_vnd":row.get("verified_net_price_vnd") if eligible else None,
      "customer_payment_pv_vnd":None,
      "fs_comparison_ready":False,
      "missing_evidence":requested if not eligible else [],
      "historical_or_unverified":row["status"]!="verified-current-contractual-policy",
      "pv_block_reason":"Incomplete or unverified contractual net price, dates, discounts or receipts" if not eligible else "No explicit annual discount rate supplied"
    }

def build(payload,projects,sources,as_of):
    if payload["record_count"]!=len(payload["data"]):raise ValueError("Count mismatch")
    ids={x["id"] for x in projects["data"]}
    source_ids={x["id"] for x in sources["data"]}
    seen=set()
    rows=[]
    for raw in payload["data"]:
        if raw["id"] in seen:raise ValueError("Duplicate policy ID")
        seen.add(raw["id"])
        rows.append(evaluate(raw,source_ids,ids,as_of))
    coverage=[]
    for project in WATCHLIST:
        if project not in ids:raise ValueError("Missing project from peer watchlist")
        matches=[x for x in rows if x["project_id"]==project]
        coverage.append({"project_id":project,"policy_claims":len(matches),
            "verified_current_schemes":sum(x["fs_comparison_ready"] for x in matches),
            "verified_net_price_count":sum(x["verified_net_selling_price_vnd"] is not None for x in matches),
            "pv_eligible_count":0,
            "missing_approved_terms":not bool(matches)})
    digest=hashlib.sha256(json.dumps(rows,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:16]
    return {"schema_version":1,"build_revision":digest,"evidence_as_of":max(x["review_date"] for x in rows) if rows else None,
            "generated_from":"data/mock/market/sales-policy-evidence.json",
            "source_refresh_is_price_refresh":False,
            "record_count":len(rows),"ready_for_fs_pv":0,"current_approved_official_schemes":0,
            "watchlist":coverage,"data":rows,
            "methodology":"Reported 60/35/5 or 10% +5% every six months does not specify a complete, effective, contractual, unit-specific schedule. Net price and PV stay null. A full verified schedule would require explicit discount rate and cash-recipient mapping; do not substitute buyer loan/grace period for developer revenue."}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",default=str(OUT))
    args=parser.parse_args()
    result=build(load(RAW),load(PROJECTS),load(SOURCES),date.today())
    destination=Path(args.output)
    destination.parent.mkdir(parents=True,exist_ok=True)
    text=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
    if destination.exists() and destination.read_text(encoding="utf-8")==text:
        print("No verified source policy changes. Readiness unchanged.")
        return
    destination.write_text(text,encoding="utf-8")
    print(f"Policy claims {result['record_count']}; verified FS schemes {result['ready_for_fs_pv']}; PV not published.")

if __name__=="__main__": main()
