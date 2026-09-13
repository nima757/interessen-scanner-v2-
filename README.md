# Auffälligkeits-Scanner Deutschland v2

Automatischer MVP für die Recherche möglicher Interessenkonflikte und ungewöhnlicher Überschneidungen.

## Datenquellen

- Deutscher Bundestag Open Data: maschinenlesbare Biografien, Drucksachen, Plenarprotokolle und Abstimmungslisten.
- Lobbyregister des Deutschen Bundestages: öffentliche Registerdaten über API.
- GovData: Metadatenkatalog über CKAN API.
- Google News RSS: ergänzende, nicht primäre Recherchequelle.
- Optional OpenSanctions: Personen-/Organisationsabgleich.

## API-Keys

In Streamlit Secrets oder Umgebungsvariablen:
- LOBBYREGISTER_API_KEY
- OPENSANCTIONS_API_KEY (optional)
- BUNDESTAG_PEOPLE_URL (optional)

Keine Schlüssel in Git committen.

## Wichtiger Datenhinweis

Der MVP darf aus GovData-Metadaten nicht schließen, dass eine bestimmte Person oder Organisation eine bestimmte Förderung erhalten hat. Für belastbare Förderfall-Analysen müssen konkrete Förderempfänger-Datensätze angebunden werden.

Ebenso ist eine Namenssuche nicht ausreichend, um Identität festzustellen. Treffer müssen über weitere Merkmale verifiziert werden.

## Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Cloud

Repository auf GitHub hochladen, in Streamlit Community Cloud verbinden und `app.py` als Entrypoint wählen. Secrets im Streamlit-Secrets-Bereich hinterlegen.
