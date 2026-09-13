import os, re, json, urllib.parse, requests, feedparser
from datetime import datetime, timezone
from sources import fetch_bundestag_people, fetch_lobby, fetch_govdata
from storage import normalize_text

UA="AutomaticConflictScanner/2.0"

def news(q, days=30, limit=15):
    url="https://news.google.com/rss/search?"+urllib.parse.urlencode({"q":q+" when:"+str(days)+"d","hl":"de","gl":"DE","ceid":"DE:de"})
    try:
        r=requests.get(url,headers={"User-Agent":UA},timeout=15); r.raise_for_status()
        f=feedparser.parse(r.text)
        out=[]
        for e in f.entries[:limit]:
            out.append({"title":e.get("title",""),"url":e.get("link",""),"snippet":re.sub("<.*?>"," ",e.get("summary","")).strip(),"source":"Google News"})
        return out
    except Exception: return []

def score_case(person, source_items, role_terms):
    text=" ".join(normalize_text(s["title"]+" "+s.get("snippet","")) for s in source_items)
    score=0; reasons=[]
    keywords=[
      (["beteiligung","anteilseigner","gesellschafter"],25,"mögliche Beteiligungs-/Eigentumsverbindung"),
      (["aufsichtsrat","beirat"],18,"mögliche Aufsichts-/Beiratsfunktion"),
      (["vorstand","geschäftsführer"],18,"mögliche Leitungsfunktion"),
      (["beratung","berater","beraterin"],15,"mögliche Beratungsverbindung"),
      (["förderung","zuschuss","fördermittel"],15,"Fördermittelbezug"),
      (["auftrag","vergabe","millionenauftrag"],12,"öffentlicher Auftrags-/Vergabebezug"),
      (["lobby","interessenvertretung"],12,"Lobby-/Interessenvertretungsbezug"),
      (["spende","spender"],8,"Spendenbezug"),
    ]
    for words,pts,label in keywords:
        if any(w in text for w in words):
            score+=pts; reasons.append(label)
    if role_terms:
        hits=sum(1 for t in role_terms if normalize_text(t) in text)
        if hits:
            score+=min(30,hits*10); reasons.append("thematische Überschneidung mit politischer Funktion")
    unique_sources=len({s["url"] for s in source_items if s.get("url")})
    if unique_sources>=3:
        score+=10; reasons.append("mehrere unabhängige Fundstellen")
    return min(score,100), reasons

def run_automatic_scan(lookback_days=30,min_score=45):
    people=fetch_bundestag_people()
    lobby=fetch_lobby()
    gov=fetch_govdata()
    alerts=[]; source_count=0
    for p in people:
        name=p["name"]
        queries=[
          f'"{name}" Beteiligung Unternehmen',
          f'"{name}" Aufsichtsrat Beirat Vorstand',
          f'"{name}" Förderung Zuschuss',
          f'"{name}" Lobby Interessenvertretung',
          f'"{name}" Vergabe Auftrag',
          f'"{name}" Nebentätigkeit',
        ]
        items=[]
        for q in queries: items.extend(news(q,lookback_days,8))
        # Lobbyregister text relevance
        related=[x for x in lobby if normalize_text(name) in normalize_text(x.get("text",""))]
        items.extend(related[:8])
        # GovData is a metadata signal only, never a payment claim
        gov_related=[x for x in gov if any(k in normalize_text(x.get("title","")) for k in ["förder","zuschuss","vergab","subvention"])]
        items.extend(gov_related[:5])
        # de-duplicate
        uniq={x.get("url"):x for x in items if x.get("url")}
        items=list(uniq.values())
        source_count+=len(items)
        score,reasons=score_case(name,items,p.get("role_terms",[]))
        if score>=min_score:
            alerts.append({
              "person":name,"score":score,
              "title":"Mehrere öffentliche Hinweise mit möglicher Überschneidung",
              "summary":"; ".join(reasons)+". Dies ist ein automatischer Prüfhinweis, keine Tatsachenfeststellung.",
              "evidence":reasons,
              "sources":items[:10]
            })
    alerts.sort(key=lambda x:x["score"],reverse=True)
    result={"created_at":datetime.now(timezone.utc).isoformat(),"alerts":alerts,"source_count":source_count}
    result["json"]=json.dumps(result,ensure_ascii=False,indent=2)
    return result
