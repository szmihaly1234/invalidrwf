import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- KONFIGURÁCIÓ ---
st.set_page_config(page_title="Midnight RWF Tracker", layout="wide")

ADMIN_PASSWORD = "rwfpred" # Írd át!
# A Google Sheet URL-je (amit az imént másoltál ki)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1SJpzwiqBkhIbNHqPv_TBBCc50Lnyo7mhF2fuOB9fvqM/edit?usp=sharing"

CLASS_COLORS = {
    "Death Knight": "#C41E3A", "Demon Hunter": "#A330C9", "Druid": "#FF7C0A",
    "Evoker": "#33937F", "Hunter": "#AAD372", "Mage": "#3FC7EB",
    "Monk": "#00FF98", "Paladin": "#F48CBA", "Priest": "#FFFFFF",
    "Rogue": "#FFF468", "Shaman": "#0070DD", "Warlock": "#8788EE",
    "Warrior": "#C69B6D"
}

CLASSES = {
    "Death Knight": ["Blood", "Frost", "Unholy"],
    "Demon Hunter": ["Havoc", "Vengeance", "Devourer"],
    "Druid": ["Balance", "Feral", "Guardian", "Restoration"],
    "Evoker": ["Augmentation", "Devastation", "Preservation"],
    "Hunter": ["Beast Mastery", "Marksmanship", "Survival"],
    "Mage": ["Arcane", "Fire", "Frost"],
    "Monk": ["Brewmaster", "Mistweaver", "Windwalker"],
    "Paladin": ["Holy", "Protection", "Retribution"],
    "Priest": ["Discipline", "Holy", "Shadow"],
    "Rogue": ["Assassination", "Outlaw", "Subtlety"],
    "Shaman": ["Elemental", "Enhancement", "Restoration"],
    "Warlock": ["Affliction", "Demonology", "Destruction"],
    "Warrior": ["Arms", "Fury", "Protection"]
}

# --- CSATLAKOZÁS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# Adatok beolvasása (Cache-elés nélkül, hogy mindig friss legyen)
def get_data():
    return conn.read(spreadsheet=SHEET_URL, worksheet="Sheet1")

def get_settings():
    return conn.read(spreadsheet=SHEET_URL, worksheet="Sheet2")

# --- PONTOZÁS (Rugalmas) ---
def calculate_points(user_data, official_data):
    if not user_data or not official_data or pd.isna(user_data) or pd.isna(official_data): return 0
    u_list, o_list = str(user_data).split(","), str(official_data).split(",")
    rem_off = list(o_list)
    score = 0
    u_rem = []
    for u in u_list:
        if u in rem_off:
            score += 2; rem_off.remove(u)
        else: u_rem.append(u)
    for u in u_rem:
        u_cls = u.split(":")[0]
        for i, o in enumerate(rem_off):
            if u_cls == o.split(":")[0]:
                score += 1; rem_off.pop(i); break
    return score

# --- SESSION ---
if 'user' not in st.session_state: st.session_state.user = None
if 'is_admin' not in st.session_state: st.session_state.is_admin = False

# --- UI / SIDEBAR ---
with st.sidebar:
    st.title("⚔️ Midnight RWF")
    if not st.session_state.user:
        u_name = st.text_input("Név")
        u_pass = st.text_input("Jelszó", type="password")
        if st.button("Belépés / Regisztráció"):
            df = get_data()
            if u_name == "admin" and u_pass == ADMIN_PASSWORD:
                st.session_state.is_admin = True
                st.session_state.user = "Admin"
                st.rerun()
            
            user_row = df[df['user'] == u_name]
            if not user_row.empty:
                if str(user_row.iloc[0]['pw']) == u_pass:
                    st.session_state.user = u_name
                    st.rerun()
                else: st.error("Rossz jelszó!")
            else:
                new_user = pd.DataFrame([{"user": u_name, "pw": u_pass, "data": ""}])
                updated_df = pd.concat([df, new_user], ignore_index=True)
                conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=updated_df)
                st.session_state.user = u_name
                st.success("Regisztrálva!")
                st.rerun()
    else:
        st.write(f"Szia, **{st.session_state.user}**!")
        if st.button("Kijelentkezés"):
            st.session_state.user = None; st.session_state.is_admin = False; st.rerun()

# --- ADMIN & USER LOGIC ---
settings_df = get_settings()
# Biztosítjuk, hogy legyenek alapértékek
if settings_df.empty:
    settings_df = pd.DataFrame([{"id": "status", "value": "open"}, {"id": "wf", "value": ""}])

status = settings_df[settings_df['id'] == 'status']['value'].values[0]
official_wf = settings_df[settings_df['id'] == 'wf']['value'].values[0]

if st.session_state.is_admin:
    st.header("🛡️ Admin Panel")
    col1, col2 = st.columns(2)
    if col1.button("🔓 NYITÁS"):
        settings_df.loc[settings_df['id'] == 'status', 'value'] = 'open'
        conn.update(spreadsheet=SHEET_URL, worksheet="Sheet2", data=settings_df); st.rerun()
    if col2.button("🔒 ZÁRÁS"):
        settings_df.loc[settings_df['id'] == 'status', 'value'] = 'closed'
        conn.update(spreadsheet=SHEET_URL, worksheet="Sheet2", data=settings_df); st.rerun()
    
    with st.expander("🔴 WF COMP BEÁLLÍTÁSA"):
        # (Itt a 20 fős választó kódja jön...)
        # Egyszerűsített mentés példa:
        if st.button("WF MENTÉSE"):
            # Ide tennéd a 20 választó értékét
            # settings_df.loc[settings_df['id'] == 'wf', 'value'] = ",".join(uj_comp)
            # conn.update(...)
            pass

elif st.session_state.user and status == 'open':
    st.header("🎮 Saját Comp")
    df = get_data()
    current_data = df[df['user'] == st.session_state.user]['data'].values[0]
    # (Itt a 4x5-ös választó grid kódja jön, amit korábban írtunk...)
    if st.button("💾 MENTÉS"):
        # Mentés a Google Sheetbe
        # df.loc[df['user'] == st.session_state.user, 'data'] = ",".join(new_comp)
        # conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=df)
        st.success("Mentve a felhőbe!")

# --- LEADERBOARD (Mindig látszik) ---
st.divider()
st.header("🏆 Ranglista")
# (A korábbi Leaderboard kódod, ami a get_data() eredményéből dolgozik)
