import os
import time
import requests
from datetime import datetime, timezone

AW_BASE = "https://www.abgeordnetenwatch.de/api/v2"
BT_OPEN_DATA = "https://www.bundestag.de/resource/blob/472878/MdB-Stammdaten.zip"
LOBBY_API = "https://api.lobbyregister.bundestag.de/rest/v2/registerentries"
UA = "InteressenScannerDeutschland/3.0"

session = requests.Session()
session.headers.update({"User-Agent": UA, "Accept": "application/json"})

def _get(url, params=None, timeout=30, retries=2):
    last=None
    for attempt in range(retries+1):
        try:
            r=session.get(url, params=params, timeout=timeout)
            if r.status_code == 429 and attempt < retries:
                time.sleep(60)
                continue
            r.raise_for_status()
            return r.json(), None
        except Exception as e:
            last=str(e)
            if attempt < retries:
                time.sleep(2*(attempt+1))
    return None, last

def _data(payload):
    if not isinstance(payload, dict):
        return []
    d=payload.get("data", [])
    return d if isinstance(d, list) else [d]

def _ref_label(ref):
    if isinstance(ref, dict):
        return ref.get("label") or ref.get("name") or ""
    return str(ref or "")

def _ref_id(ref):
    if isinstance(ref, dict):
        return ref.get("id")
    return ref

def fetch_current_bundestag():
    """Primary universe: current Bundestag mandates via Abgeordnetenwatch.
    This avoids the brittle heuristic XML parser used in v2."""
    diagnostics={"name":"Abgeordnetenwatch","ok":False,"records":0,"error":None,"url":AW_BASE}
    parliaments, err = _get(f"{AW_BASE}/parliaments", {"range_end":200})
    if err:
        diagnostics["error"]=err; return [], diagnostics
    ps=_data(parliaments)
    bt=next((p for p in ps if "bundestag" in (_ref_label(p.get("label"))+" "+_ref_label(p.get("label_external_long"))).lower()), None)
    if not bt:
        diagnostics["error"]="Bundestag in API-Parlamenten nicht gefunden"; return [], diagnostics

    current=bt.get("current_project") or {}
    period_id=_ref_id(current)
    if not period_id:
        periods, err = _get(f"{AW_BASE}/parliament-periods", {"parliament":bt.get("id"),"type":"legislature","range_end":100})
        if err:
            diagnostics["error"]=err; return [], diagnostics
        candidates=_data(periods)
        if not candidates:
            diagnostics["error"]="Keine Bundestags-Legislatur gefunden"; return [], diagnostics
        period_id=candidates[0].get("id")

    mandates, err = _get(f"{AW_BASE}/candidacies-mandates",
                          {"parliament_period":period_id,"type":"mandate","range_end":1000})
    if err:
        diagnostics["error"]=err; return [], diagnostics

    out=[]
    for m in _data(mandates):
        if m.get("type") != "mandate": continue
        pol=m.get("politician") or {}
        pid=_ref_id(pol)
        name=_ref_label(pol)
        if not pid or not name: continue
        if m.get("end_date"): continue
        party=_ref_label(m.get("party"))
        out.append({
            "id": int(pid) if str(pid).isdigit() else pid,
            "mandate_id": m.get("id"),
            "name": name,
            "party": party,
            "profile_url": pol.get("abgeordnetenwatch_url") or "",
            "role_terms": [],
        })
    # Deduplicate by politician
    seen=set(); people=[]
    for p in out:
        if p["id"] in seen: continue
        seen.add(p["id"]); people.append(p)
    diagnostics["ok"]=bool(people)
    diagnostics["records"]=len(people)
    diagnostics["period_id"]=period_id
    return people, diagnostics

def fetch_sidejobs(mandate_ids):
    diagnostics={"name":"Abgeordnetenwatch Nebentätigkeiten","ok":False,"records":0,"error":None,"url":f"{AW_BASE}/sidejobs"}
    if not mandate_ids:
        diagnostics["error"]="Keine aktuellen Mandate"; return [], diagnostics
    wanted={str(x) for x in mandate_ids if x is not None}
    all_jobs=[]
    # Fair-use: max 10 pages, 1000 each. Usually one page is enough for current Bundestag side jobs.
    for page in range(1,11):
        payload, err = _get(f"{AW_BASE}/sidejobs", {"page":page,"pager_limit":1000})
        if err:
            diagnostics["error"]=err; break
        rows=_data(payload)
        if not rows: break
        for job in rows:
            refs=job.get("mandates") or []
            ids={str(_ref_id(x)) for x in refs}
            if ids & wanted:
                all_jobs.append(job)
        total=(payload.get("meta") or {}).get("result",{}).get("total")
        if total is not None and page*1000 >= int(total): break
        if len(rows)<1000: break
        time.sleep(2.1)
    diagnostics["records"]=len(all_jobs)
    diagnostics["ok"]=True
    return all_jobs, diagnostics

def fetch_committee_memberships(mandate_ids):
    diagnostics={"name":"Abgeordnetenwatch Ausschüsse","ok":False,"records":0,"error":None,"url":f"{AW_BASE}/committee-memberships"}
    wanted={str(x) for x in mandate_ids if x is not None}
    payload, err = _get(f"{AW_BASE}/committee-memberships", {"range_end":1000})
    if err:
        diagnostics["error"]=err; return [], diagnostics
    rows=[]
    for x in _data(payload):
        if str(_ref_id(x.get("candidacy_mandate"))) in wanted:
            rows.append(x)
    diagnostics["records"]=len(rows); diagnostics["ok"]=True
    return rows, diagnostics

def fetch_lobby():
    key=os.getenv("LOBBYREGISTER_API_KEY","").strip()
    diagnostics={"name":"Lobbyregister","ok":False,"records":0,"error":None,"configured":bool(key),"url":LOBBY_API}
    if not key:
        diagnostics["error"]="Kein LOBBYREGISTER_API_KEY in Streamlit Secrets gesetzt."
        return [], diagnostics
    payload, err=_get(LOBBY_API, {"page":0,"size":100}, timeout=40)
    if err:
        diagnostics["error"]=err; return [], diagnostics
    rows=_data(payload)
    out=[]
    for x in rows:
        text=str(x)
        out.append({
            "title":x.get("name") or x.get("organisationName") or "Lobbyregister-Eintrag",
            "url":"https://www.lobbyregister.bundestag.de/",
            "text":text,
            "source":"Lobbyregister"
        })
    diagnostics["ok"]=True; diagnostics["records"]=len(out)
    return out, diagnostics

def fetch_govdata():
    diagnostics={"name":"GovData","ok":False,"records":0,"error":None,"url":"https://www.govdata.de/ckan/api/3/action/package_search"}
    try:
        r=session.get(diagnostics["url"],params={"q":"förderung OR vergabe","rows":100},timeout=25)
        r.raise_for_status()
        data=r.json()
        rows=(data.get("result") or {}).get("results",[])
        out=[]
        for x in rows:
            out.append({"title":x.get("title",""),"url":"https://www.govdata.de/","snippet":x.get("notes",""),"source":"GovData"})
        diagnostics["ok"]=True; diagnostics["records"]=len(out)
        return out, diagnostics
    except Exception as e:
        diagnostics["error"]=str(e); return [], diagnostics

def source_timestamp():
    return datetime.now(timezone.utc).isoformat()
