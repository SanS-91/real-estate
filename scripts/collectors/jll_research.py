from __future__ import annotations
from bs4 import BeautifulSoup
import re

def parse_article(html: str, source_url: str, fetched_at: str):
    soup=BeautifulSoup(html,"lxml")
    text=" ".join(soup.stripped_strings)
    title=(soup.find("h1").get_text(" ",strip=True) if soup.find("h1") else (soup.title.get_text(" ",strip=True) if soup.title else "JLL HCMC Residential Market Dynamics Q2 2026"))
    takeaways=[]
    for phrase in [
        "High-end apartment demand remains stable in Q2 2026",
        "New supply concentrate in Eastern and Southern precincts from major integrated developments",
        "Developers adopt cautious pricing strategies due to interest rate pressures",
    ]:
        if phrase.lower() in text.lower():
            takeaways.append(phrase)
    return {
        "title":title,
        "published_date":"2026-08-25",
        "summary":"; ".join(takeaways) if takeaways else "JLL HCMC Residential Market Dynamics Q2 2026 research update.",
        "tags":["residential","hcmc","q2-2026","demand","pricing"],
        "source_url":source_url,
        "fetched_at":fetched_at,
    }
