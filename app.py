import streamlit as st
from engine import run_automatic_scan
from storage import init_db, save_run, load_runs

st.set_page_config(page_title="Auffälligkeits-Scanner Deutschland", page_icon="🔎", layout="wide")
init_db()

st.title("🔎 Auffälligkeits-Scanner Deutschland")
st.caption("Automatische Recherche öffentlicher Verflechtungen. Nur belegte Recherchehinweise werden angezeigt; keine Schuld- oder Korruptionsfeststellungen.")

with st.sidebar:
    st.header("Automatischer Scan")
    lookback = st.slider("Nachrichtenzeitraum (Tage)", 7, 90, 30)
    min_score = st.slider("Nur ab Score", 20, 90, 45)
    scan_btn = st.button("▶ Scan starten", type="primary", use_container_width=True)
    st.divider()
    st.write("Datenquellen im MVP:")
    st.write("• Bundestag Open Data")
    st.write("• Lobbyregister API")
    st.write("• GovData-Metadaten")
    st.write("• öffentliche Nachrichtensuche")
    st.write("• optional OpenSanctions")

if scan_btn:
    with st.spinner("Personen, Organisationen und Quellen werden abgeglichen …"):
        result=run_automatic_scan(lookback_days=lookback, min_score=min_score)
        save_run(result)
    st.session_state["scan"]=result

if "scan" in st.session_state:
    r=st.session_state["scan"]
    st.subheader(f"Scan {r['created_at']}")
    a,b,c,d=st.columns(4)
    a.metric("Auffällig", len(r["alerts"]))
    b.metric("Stark", sum(x["score"]>=75 for x in r["alerts"]))
    c.metric("Mittel", sum(50<=x["score"]<75 for x in r["alerts"]))
    d.metric("Quellen", r["source_count"])

    if not r["alerts"]:
        st.success("Keine Auffälligkeiten oberhalb des gewählten Schwellenwerts.")
    for x in r["alerts"]:
        level="🔴 Stark" if x["score"]>=75 else "🟠 Mittel" if x["score"]>=50 else "🟡 Hinweis"
        with st.expander(f"{level} · {x['score']}/100 · {x['person']} — {x['title']}", expanded=x["score"]>=75):
            st.write(x["summary"])
            st.markdown("**Beziehungs-/Evidenzkette**")
            for e in x["evidence"]:
                st.write("• "+e)
            if x["sources"]:
                st.markdown("**Quellen**")
                for s in x["sources"]:
                    st.markdown(f"- [{s['title']}]({s['url']})")
            st.caption("Prüfhinweis: Die Bewertung ist algorithmisch und kann Fehler enthalten. Vor Veröffentlichung müssen Identität, zeitlicher Zusammenhang und Primärquellen geprüft werden.")

    st.download_button("⬇️ Scan als JSON", r["json"], "scan.json", "application/json", use_container_width=True)

st.divider()
st.subheader("Scan-Verlauf")
h=load_runs()
if h is not None and not h.empty:
    st.dataframe(h, use_container_width=True, hide_index=True)
else:
    st.caption("Noch keine gespeicherten Scans.")
