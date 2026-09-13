import streamlit as st
from engine import run_automatic_scan
from storage import init_db, save_run, load_runs

st.set_page_config(page_title="Auffälligkeits-Scanner Deutschland", page_icon="🔎", layout="wide")
init_db()

st.title("🔎 Auffälligkeits-Scanner Deutschland")
st.caption("Automatische Recherche öffentlicher Verflechtungen. Prüfhinweise statt Schuld- oder Korruptionsfeststellungen.")

with st.sidebar:
    st.header("Automatischer Scan")
    lookback=st.slider("Nachrichtenzeitraum (Tage)",7,90,30)
    min_score=st.slider("Nur ab Score",20,90,45)
    scan_btn=st.button("▶ Scan starten",type="primary",use_container_width=True)
    st.divider()
    st.markdown("**Primäre Quellen**")
    st.write("• Abgeordnetenwatch: aktuelle Bundestagsmandate")
    st.write("• Abgeordnetenwatch: veröffentlichte Nebentätigkeiten")
    st.write("• Abgeordnetenwatch: Ausschussmitgliedschaften")
    st.markdown("**Ergänzende Quellen**")
    st.write("• Lobbyregister API (optional)")
    st.write("• GovData")
    st.write("• Google News – nur für Kandidaten")

if scan_btn:
    with st.spinner("Strukturierte Daten werden geladen und Kandidaten geprüft …"):
        result=run_automatic_scan(lookback_days=lookback,min_score=min_score)
        save_run(result)
    st.session_state["scan"]=result

if "scan" in st.session_state:
    r=st.session_state["scan"]
    st.subheader("Scan-Ergebnis")
    st.caption(f"Start: {r['created_at']} · Bundestags-Personen: {r['people_count']} · Kandidaten: {r['candidate_count']}")
    a,b,c,d=st.columns(4)
    a.metric("Prüfhinweise",len(r["alerts"]))
    b.metric("Stark",sum(x["score"]>=75 for x in r["alerts"]))
    c.metric("Auffällig",sum(50<=x["score"]<75 for x in r["alerts"]))
    d.metric("Quell-Datensätze",r["source_count"])

    if not r["scan_complete"]:
        st.error("⚠️ Scan unvollständig: Eine Primärquelle für Personen/Mandate oder Nebentätigkeiten konnte nicht geladen werden. 'Keine Treffer' darf deshalb nicht als Entwarnung interpretiert werden.")
    elif not r["alerts"]:
        st.success("Keine Prüfhinweise oberhalb des gewählten Schwellenwerts. Das ist keine Aussage über das Fehlen von Interessenkonflikten.")

    st.subheader("Quellengesundheit")
    for d in r["source_health"]:
        icon="✅" if d.get("ok") else "⚠️"
        extra=f" · {d.get('records',0)} Datensätze"
        if d.get("error"): extra+=f" · {d['error']}"
        st.write(f"{icon} **{d['name']}**{extra}")

    for x in r["alerts"]:
        level="🔴 Stark auffällig" if x["score"]>=75 else "🟠 Auffällig" if x["score"]>=50 else "🟡 Prüfhweis"
        with st.expander(f"{level} · {x['score']}/100 · {x['person']}",expanded=x["score"]>=75):
            if x.get("party"): st.write(f"Partei: {x['party']}")
            st.write(x["summary"])
            st.markdown("**Evidenzkette**")
            for e in x["evidence"]: st.write("• "+e)
            if x["time_axis"]: st.caption("Zeitachse: "+", ".join(sorted(set(x["time_axis"]))[:8]))
            if x["sources"]:
                st.markdown("**Quellen**")
                for s in x["sources"]:
                    title=s.get("title") or s.get("source") or "Quelle"
                    url=s.get("url")
                    if url: st.markdown(f"- [{title}]({url})")
            st.caption("Automatischer Prüfhinweis. Identität, zeitlicher Zusammenhang und Primärquellen müssen vor einer Veröffentlichung manuell geprüft werden.")

    st.download_button("⬇️ Scan als JSON",r["json"],"scan.json","application/json",use_container_width=True)

st.divider()
st.subheader("Scan-Verlauf")
h=load_runs()
if h is not None and not h.empty: st.dataframe(h,use_container_width=True,hide_index=True)
else: st.caption("Noch keine gespeicherten Scans.")
