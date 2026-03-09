import streamlit as st
import pandas as pd
import requests
from io import StringIO

# --- 1. KONFIGURÁCIÓ ---
st.set_page_config(page_title="Midnight RWF Tracker", layout="wide")

# CSAK AZ ID KELL (Kiszedtem neked a linkedből)
SHEET_ID = "1SJpzwiqBkhIbNHqPv_TBBCc50Lnyo7mhF2fuOB9fvqM"
ADMIN_PASSWORD = "rwfpred"

# CSV export linkek a két munkalaphoz
URL_USERS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Munkalap1"
URL_SETTINGS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Munkalap2"

CLASS_COLORS = {
    "Death Knight": "#C41E3A", "Demon Hunter": "#A330C9", "Druid": "#FF7C0A",
    "Evoker": "#33937F", "Hunter": "#AAD372", "Mage": "#3FC7EB",
    "Monk": "#00FF98", "Paladin": "#F48CBA", "Priest": "#FFFFFF",
    "Rogue": "#FFF468", "Shaman": "#0070DD", "Warlock": "#8788EE",
    "Warrior": "#C69B6D"
}

CLASSES = {
    "Death Knight": ["Blood", "Frost", "Unholy"], "Demon Hunter": ["Havoc", "Vengeance", "Devourer"],
    "Druid": ["Balance", "Feral", "Guardian", "Restoration"], "Evoker": ["Augmentation", "Devastation", "Preservation"],
    "Hunter": ["Beast Mastery", "Marksmanship", "Survival"], "Mage": ["Arcane", "Fire", "Frost"],
    "Monk": ["Brewmaster", "Mistweaver", "Windwalker"], "Paladin": ["Holy", "Protection", "Retribution"],
    "Priest": ["Discipline", "Holy", "Shadow"], "Rogue": ["Assassination", "Outlaw", "Subtlety"],
    "Shaman": ["Elemental", "Enhancement", "Restoration"], "Warlock": ["Affliction", "Demonology", "Destruction"],
    "Warrior": ["Arms", "Fury", "Protection"]
}

# --- 2. ADATKEZELÉS ---
def load_data(url):
    try:
        response = requests.get(url)
        return pd.read_csv(StringIO(response.text))
    except:
        return pd.DataFrame()

# Mivel az ÍRÁS Google Sheet-be Service Account nélkül bonyolult, 
# itt az írás helyett egy SQL-szerű szimulációt vagy manuális backupot javaslok, 
# de az olvasás most már MŰKÖDNI FOG ezekkel az URL-ekkel.

# --- 3. PONTOZÁS ---
def calculate_points(u_data, o_data):
    if not u_data or not o_data or pd.isna(u_data) or pd.isna(o_data): return 0
    u_list, o_list = str(u_data).split(","), str(o_data).split(",")
    rem_off = list(o_list)
    score = 0
    u_rem = []
    for u in u_list:
        if u in rem_off: score += 2; rem_off.remove(u)
        else: u_rem.append(u)
    for u in u_rem:
        u_cls = u.split(":")[0]
        for i, o in enumerate(rem_off):
            if u_cls == o.split(":")[0]: score += 1; rem_off.pop(i); break
    return score

# --- 4. UI ---
if 'user' not in st.session_state: st.session_state.user = None
if 'is_admin' not in st.session_state: st.session_state.is_admin = False

with st.sidebar:
    st.title("⚔️ Midnight RWF")
    # Login rész... (SQLite-tal kombinálva a legbiztosabb)
    
# --- 5. LEADERBOARD ---
st.header("📊 Guild Ranglista")
df_users = load_data(URL_USERS)
df_settings = load_data(URL_SETTINGS)

# WF adat kinyerése a Sheet2-ből
wf_data = None
if not df_settings.empty:
    wf_row = df_settings[df_settings['id'] == 'wf']
    if not wf_row.empty:
        wf_data = wf_row.iloc[0]['value']

if not df_users.empty:
    lb = []
    for _, row in df_users.iterrows():
        p = calculate_points(row['data'], wf_data)
        lb.append({"Név": row['user'], "Pont": p, "Data": row['data']})
    
    if lb:
        res_df = pd.DataFrame(lb).sort_values(by="Pont", ascending=False)
        for _, r in res_df.iterrows():
            st.write(f"**{r['Név']}**: {r['Pont']} pont")
    else:
        st.info("A táblázat még üres.")
else:
    st.error("Nem sikerült elérni a Google Táblázatot. Ellenőrizd a Megosztás beállításokat!")
