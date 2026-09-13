import os, re, requests, xml.etree.ElementTree as ET

UA="AutomaticConflictScanner/2.0"

def fetch_bundestag_people():
    # Öffentliche Stammdaten-URL kann sich ändern; deshalb konfigurierbar.
    url=os.getenv("BUNDESTAG_PEOPLE_URL","https://www.bundestag.de/resource/blob/194594/Personenstammdaten.xml")
    try:
        r=requests.get(url,headers={"User-Agent":UA},timeout=25); r.raise_for_status()
        root=ET.fromstring(r.content)
        people=[]
        for person in root.iter():
            txt=" ".join(person.itertext()).strip()
            if not txt: continue
            # Heuristik für Namen; bei abweichendem XML lieber leer zurückgeben als falsche Personen erzeugen.
            m=re.search(r"(?:Nachname|Familienname)\s*[:\-]?\s*([A-Za-zÄÖÜäöüß\- ]+)",txt)
            if m:
                name=m.group(1).strip()
                if 3<len(name)<80:
                    people.append({"name":name,"role_terms":[]})
        # dedupe
        seen=set(); out=[]
        for p in people:
            if p["name"].lower() not in seen:
                seen.add(p["name"].lower()); out.append(p)
        return out[:800]
    except Exception:
        # Sicherer Fallback: keine erfundenen Personen.
        return []

def fetch_lobby():
    key=os.getenv("LOBBYREGISTER_API_KEY","")
    if not key: return []
    url="https://www.lobbyregister.bundestag.de/sucheDetailJson?sort=REGISTRATION_DESC"
    try:
        r=requests.get(url,headers={"User-Agent":UA,"X-API-Key":key},timeout=30)
        r.raise_for_status(); data=r.json()
        raw=data.get("results",data.get("registerEntries",[]))
        out=[]
        for x in raw[:3000]:
            d=x.get("registerEntryDetail",x)
            name=(d.get("lobbyistIdentity") or {}).get("name","") if isinstance(d,dict) else ""
            out.append({"title":name or "Lobbyregister-Eintrag","url":"https://www.lobbyregister.bundestag.de/","text":str(d),"source":"Lobbyregister"})
        return out
    except Exception: return []

def fetch_govdata():
    # Nur Metadaten; daraus werden keine tatsächlichen Zahlungen abgeleitet.
    url="https://www.govdata.de/ckan/api/3/action/package_search?q=förderung"
    try:
        r=requests.get(url,headers={"User-Agent":UA},timeout=20); r.raise_for_status()
        data=r.json(); out=[]
        for x in data.get("result",{}).get("results",[])[:100]:
            out.append({"title":x.get("title",""),"url":"https://www.govdata.de/","snippet":x.get("notes",""),"source":"GovData"})
        return out
    except Exception: return []
