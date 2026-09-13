import json, re, urllib.parse, requests
from datetime import datetime, timezone
from storage import normalize_text
from sources import fetch_current_bundestag, fetch_sidejobs, fetch_committee_memberships, fetch_lobby, fetch_govdata

UA="InteressenScannerDeutschland/3.0"

def news(q, days=30, limit=8):
    url="https://news.google.com/rss/search?"+urllib.parse.urlencode({
        "q":q+" when:"+str(days)+"d","hl":"de","gl":"DE","ceid":"DE:de"
    })
    try:
        r=requests.get(url,headers={"User-Agent":UA},timeout=15)
        r.raise_for_status()
        import feedparser
        f=feedparser.parse(r.text)
        return [{
            "title":e.get("title",""),
            "url":e.get("link",""),
            "snippet":re.sub("<.*?>"," ",e.get("summary","")).strip(),
            "source":"Google News"
        } for e in f.entries[:limit]]
    except Exception:
        return []

CATEGORY={
    "29231":("Beteiligung an Kapital-/Personengesellschaften",35),
    "29228":("Funktion in einem Unternehmen",32),
    "29230":("Funktion in Verein/Verband/Stiftung",24),
    "29229":("Funktion in Körperschaft/Anstalt des öffentlichen Rechts",22),
    "29647":("entgeltliche Tätigkeit neben dem Mandat",25),
    "29233":("künftige Tätigkeit/Vermögensvorteil vereinbart",38),
    "29232":("Spende/Zuwendung für politische Tätigkeit",18),
    "29234":("frühere berufliche Tätigkeit",8),
}

def _label(x):
    if isinstance(x,dict): return x.get("label") or x.get("name") or ""
    return str(x or "")

def _ref_id(x):
    if isinstance(x,dict): return x.get("id")
    return x

def prepare_structured(people, sidejobs, committees):
    by_person={p["id"]:dict(p, sidejobs=[], committees=[]) for p in people}
    mandate_to_person={str(p["mandate_id"]):p["id"] for p in people if p.get("mandate_id") is not None}
    for job in sidejobs:
        refs=job.get("mandates") or []
        pid=None
        for ref in refs:
            pid=mandate_to_person.get(str(_ref_id(ref)))
            if pid: break
        if pid and pid in by_person:
            org=job.get("sidejob_organization") or {}
            topics=job.get("field_topics") or []
            by_person[pid]["sidejobs"].append({
                "id":job.get("id"),
                "label":job.get("label",""),
                "extra":job.get("job_title_extra",""),
                "info":job.get("additional_information",""),
                "category":str(job.get("category","")),
                "category_label":CATEGORY.get(str(job.get("category","")),("sonstige Nebentätigkeit",5))[0],
                "points":CATEGORY.get(str(job.get("category","")),("sonstige Nebentätigkeit",5))[1],
                "income_level":job.get("income_level"),
                "income":job.get("income"),
                "organization":_label(org),
                "topics":[_label(t) for t in topics],
                "changed":job.get("data_change_date"),
                "url":job.get("api_url") or "https://www.abgeordnetenwatch.de/api/v2/sidejobs"
            })
    for cm in committees:
        mid=_ref_id(cm.get("candidacy_mandate"))
        # map mandate id to person
        pid=mandate_to_person.get(str(mid))
        if pid and pid in by_person:
            by_person[pid]["committees"].append({
                "name":_label(cm.get("committee")),
                "role":cm.get("committee_role","member")
            })
    return list(by_person.values())

def score_structured(p):
    jobs=p["sidejobs"]
    if not jobs: return 0,[]
    score=0; reasons=[]
    # Multiple distinct organisations/categories increase evidence strength, but not linearly.
    cats=[]
    orgs=[]
    topics=[]
    for j in jobs:
        cats.append(j["category"])
        if j["organization"]: orgs.append(j["organization"])
        topics += j["topics"]
    distinct_orgs=len(set(orgs))
    distinct_cats=len(set(cats))
    max_job=max((j["points"] for j in jobs),default=0)
    score=min(60,max_job + min(20,(len(jobs)-1)*5) + min(10,max(0,distinct_orgs-1)*5))
    if any(c in {"29231","29228","29233"} for c in cats):
        score+=10
        reasons.append("offengelegte Unternehmens-/Beteiligungs- oder Zukunftsverbindung")
    if any(c=="29647" for c in cats):
        score+=5; reasons.append("offengelegte entgeltliche Nebentätigkeit")
    if any(c=="29229" for c in cats):
        reasons.append("offengelegte Funktion in einer öffentlich-rechtlichen Organisation")
    if any(c=="29230" for c in cats):
        reasons.append("offengelegte Funktion in Verein/Verband/Stiftung")
    if topics:
        reasons.append("Themenschlagworte zur Nebentätigkeit sind dokumentiert")
    if distinct_cats>=2:
        score+=5; reasons.append("mehrere unterschiedliche Kategorien")
    return min(score,90),reasons

def run_automatic_scan(lookback_days=30,min_score=45):
    started=datetime.now(timezone.utc).isoformat()
    people, d_people=fetch_current_bundestag()
    sidejobs, d_jobs=fetch_sidejobs([p.get("mandate_id") for p in people])
    committees, d_cm=fetch_committee_memberships([p.get("mandate_id") for p in people])
    lobby, d_lobby=fetch_lobby()
    gov, d_gov=fetch_govdata()

    diagnostics=[d_people,d_jobs,d_cm,d_lobby,d_gov]
    structured=prepare_structured(people,sidejobs,committees)
    alerts=[]
    candidates=[]

    for p in structured:
        score,reasons=score_structured(p)
        if score>=min_score:
            candidates.append((score,p,reasons))

    # News is deliberately secondary and only queried for candidates.
    # This avoids thousands of fragile RSS requests in one scan.
    for score,p,reasons in sorted(candidates,key=lambda x:x[0],reverse=True)[:40]:
        q=f'"{p["name"]}" (' + " OR ".join(["Beteiligung","Aufsichtsrat","Beirat","Vorstand","Beratung","Lobby","Vergabe","Förderung"]) + ")"
        news_items=news(q,lookback_days,8)
        if news_items:
            score=min(100,score+10)
            reasons=reasons+["aktuelle öffentliche Berichterstattung mit relevantem Bezug gefunden"]
        evidence=[]
        sources=[]
        for j in p["sidejobs"][:8]:
            desc=f'{j["category_label"]}'
            if j["organization"]: desc += f' – {j["organization"]}'
            if j["label"]: desc += f' ({j["label"]})'
            evidence.append(desc)
            sources.append({"title":"Abgeordnetenwatch: Nebentätigkeit","url":j["url"],"source":"Abgeordnetenwatch"})
        for c in p["committees"][:6]:
            evidence.append(f'Ausschuss: {c["name"]} ({c["role"]})')
        sources.extend(news_items[:6])
        if score>=min_score:
            alerts.append({
                "person":p["name"],"party":p.get("party",""),"score":score,
                "title":"Mögliche relevante Verflechtung – Prüfung erforderlich",
                "summary":"; ".join(reasons)+". Die zugrunde liegenden Nebentätigkeiten sind öffentlich dokumentiert; daraus folgt allein kein Fehlverhalten.",
                "evidence":evidence,
                "sources":sources,
                "profile_url":p.get("profile_url",""),
                "time_axis":[j.get("changed") for j in p["sidejobs"] if j.get("changed")],
            })

    alerts.sort(key=lambda x:x["score"],reverse=True)
    ok_sources=sum(1 for d in diagnostics if d.get("ok"))
    total_records=sum(int(d.get("records") or 0) for d in diagnostics)
    result={
        "created_at":started,
        "alerts":alerts,
        "source_count":total_records,
        "source_health":diagnostics,
        "people_count":len(people),
        "candidate_count":len(candidates),
        "scan_complete":bool(d_people.get("ok") and d_jobs.get("ok")),
        "json":""
    }
    result["json"]=json.dumps(result,ensure_ascii=False,indent=2)
    return result
