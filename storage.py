import sqlite3, re
from pathlib import Path
import pandas as pd
DB=Path("data/scanner.db")

def normalize_text(s):
    return re.sub(r"\s+"," ",(s or "").lower()).strip()

def init_db():
    DB.parent.mkdir(exist_ok=True)
    c=sqlite3.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS scans(
      id INTEGER PRIMARY KEY, created_at TEXT, alerts INTEGER, strong INTEGER, medium INTEGER, sources INTEGER, payload TEXT)""")
    c.commit(); c.close()

def save_run(r):
    c=sqlite3.connect(DB)
    c.execute("INSERT INTO scans(created_at,alerts,strong,medium,sources,payload) VALUES(?,?,?,?,?,?)",
      (r["created_at"],len(r["alerts"]),sum(x["score"]>=75 for x in r["alerts"]),
       sum(50<=x["score"]<75 for x in r["alerts"]),r["source_count"],r["json"]))
    c.commit(); c.close()

def load_runs():
    c=sqlite3.connect(DB)
    df=pd.read_sql_query("SELECT created_at AS Zeitpunkt,alerts AS Prüfhinweise,strong AS Stark,medium AS Auffällig,sources AS Quellen FROM scans ORDER BY id DESC LIMIT 30",c)
    c.close(); return df
