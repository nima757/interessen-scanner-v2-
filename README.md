# Auffälligkeits-Scanner Deutschland v3

## Was wurde gegenüber v2 geändert?

v2 konnte auf einer veralteten/heuristisch geparsten Bundestag-XML-URL 0 Personen liefern. Dadurch war ein "0 Treffer"-Scan irreführend.

v3 verwendet als Primärquelle die maschinenlesbare API von Abgeordnetenwatch für:
- aktuelle Bundestagsmandate,
- veröffentlichte Nebentätigkeiten,
- Ausschussmitgliedschaften.

Die Bundestagsverwaltung stellt daneben offizielle Stammdaten als XML bereit; die aktuelle Open-Data-Seite verweist auf `MdB-Stammdaten.zip`. Diese ZIP bleibt als dokumentierte Primärquelle erhalten, wird in v3 aber nicht mehr heuristisch geparst.

### Sicherheits-/Qualitätshinweis

Eine veröffentlichte Nebentätigkeit ist **nicht automatisch eine Auffälligkeit**. Der Scanner erzeugt nur Prüfhinweise, wenn strukturierte Merkmale eine nähere Prüfung rechtfertigen. Es werden keine Schuld- oder Korruptionsbehauptungen erzeugt.

Förderprogramme und GovData-Metadaten werden nicht als Beweis für eine konkrete Zahlung an eine Person interpretiert.

## Quellen

- Abgeordnetenwatch API: https://www.abgeordnetenwatch.de/api
- Bundestag Open Data: https://www.bundestag.de/open-data-inhalt-472740
- Lobbyregister API V2: https://www.lobbyregister.bundestag.de/informationen-und-hilfe/open-data-1049716
- GovData: https://www.govdata.de/

## Optional: Lobbyregister

In Streamlit unter App Settings → Secrets:

```toml
LOBBYREGISTER_API_KEY = "DEIN_KEY"
```

Ohne diesen Key funktioniert der Kernscan trotzdem.

## Start

```bash
pip install -r requirements.txt
streamlit run app.py
```
