import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- KONFIGURÁCIÓ ---
ADMIN_PASSWORD = "invalidpred" # Ezt írd át!
DEADLINE = datetime(2026, 3, 24, 0, 0)
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

# --- DB SETUP ---
conn = sqlite3.connect('midnight_wf.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS predictions (user TEXT PRIMARY KEY, pw TEXT, data TEXT)')
# Tábla a hivatalos győztes compnak
c.execute('CREATE TABLE IF NOT EXISTS official_wf (id INTEGER PRIMARY KEY, data TEXT)')
conn.commit()

st.set_page_config(page_title="Midnight RWF Tracker", layout="wide")

# --- SEGÉDFÜGGVÉNY: PONTSZÁMÍTÁS ---
def calculate_points(user_pred, official_wf_data):
    if not user_pred or not official_wf_data: return 0
    u_list = user_pred.split(",")
    o_list = official_wf_data.split(",")
    
    total = 0
    # Egyszerűsített számítás: slotonként nézzük (vagy ha rugalmasabban akarod, halmazként)
    # Most slot-alapon nézzük (pl. az 1. slotban DK-t vártál, ott az van-e)
    for i in range(20):
        u_cls, u_spc = u_list[i].split(":")
        o_cls, o_spc = o_list[i].split(":")
        
        if u_cls == o_cls:
            if u_spc == o_spc:
                total += 2 # Teljes találat
            else:
                total += 1 # Csak kaszt
    return total

# --- OLDALSÁV (AUTH & ADMIN) ---
if 'user' not in st.session_state: st.session_state.user = None
if 'is_admin' not in st.session_state: st.session_state.is_admin = False

with st.sidebar:
    st.title("⚔️ Midnight RWF")
    u_in = st.text_input("Guild Tag Név")
    p_in = st.text_input("Jelszó", type="password")
    if st.button("Belépés / Regisztráció"):
        if u_in == "admin" and p_in == ADMIN_PASSWORD:
            st.session_state.is_admin = True
            st.session_state.user = "Admin"
        else:
            c.execute("SELECT pw FROM predictions WHERE user=?", (u_in,))
            res = c.fetchone()
            if res:
                if res[0] == p_in: st.session_state.user = u_in
                else: st.error("Rossz jelszó")
            else:
                c.execute("INSERT INTO predictions VALUES (?,?,?)", (u_in, p_in, ""))
                conn.commit()
                st.session_state.user = u_in
        st.rerun()
    
    if st.session_state.user:
        if st.button("Kijelentkezés"):
            st.session_state.user = None
            st.session_state.is_admin = False
            st.rerun()

# --- ADMIN FELÜLET (HIVATALOS COMP FELTÖLTÉSE) ---
if st.session_state.is_admin:
    st.header("🛡️ ADMIN: Világelső Comp Megadása")
    # Itt ugyanaz a 20-as választó van, mint a felhasználónál
    c.execute("SELECT data FROM official_wf WHERE id=1")
    off_res = c.fetchone()
    off_current = off_res[0].split(",") if off_res else ["Death Knight:Blood"] * 20
    
    off_new_comp = []
    cols = st.columns(4)
    for i in range(20):
        with cols[i%4]:
            s_cls, s_spc = off_current[i].split(":")
            c_sel = st.selectbox(f"WF Class {i}", list(CLASSES.keys()), index=list(CLASSES.keys()).index(s_cls), key=f"wf_c_{i}")
            s_sel = st.selectbox(f"WF Spec {i}", CLASSES[c_sel], index=CLASSES[c_sel].index(s_spc) if s_spc in CLASSES[c_sel] else 0, key=f"wf_s_{i}")
            off_new_comp.append(f"{c_sel}:{s_sel}")
            
    if st.button("🔴 HIVATALOS COMP MENTÉSE ÉS PONTSZÁMÍTÁS"):
        final_off = ",".join(off_new_comp)
        c.execute("INSERT OR REPLACE INTO official_wf (id, data) VALUES (1, ?)", (final_off,))
        conn.commit()
        st.success("Hivatalos comp rögzítve!")

# --- USER JÁTÉK FELÜLET ---
elif st.session_state.user and not st.session_state.is_admin:
    # (Ide jön a korábbi kódod a 4x5-ös raid griddel...)
    st.info("Itt tudod összeállítani a saját 20 fős csapatodat.")
    # ... (A korábbi 'new_comp' választó rész változatlanul maradhat itt)

# --- LEADERBOARD (MINDENKINEK LÁTSZIK) ---
st.divider()
st.header("🏆 Guild Rangsor")

c.execute("SELECT data FROM official_wf WHERE id=1")
wf_data_res = c.fetchone()
wf_data = wf_data_res[0] if wf_data_res else None

c.execute("SELECT user, data FROM predictions")
all_preds = c.fetchall()

leaderboard_data = []
for user, data in all_preds:
    score = calculate_points(data, wf_data) if wf_data else 0
    leaderboard_data.append({"Név": user, "Pontszám": score, "Data": data})

# Pontszám szerinti rendezés
df_lb = pd.DataFrame(leaderboard_data).sort_values(by="Pontszám", ascending=False)

for _, row in df_lb.iterrows():
    col_n, col_p = st.columns([3, 1])
    with col_n:
        with st.expander(f"👤 {row['Név']}"):
            if row['Data']:
                d_list = row['Data'].split(",")
                l_cols = st.columns(5)
                for i, item in enumerate(d_list):
                    cn, sn = item.split(":")
                    l_cols[i%5].markdown(f"<span style='color:{CLASS_COLORS[cn]}'>{sn}</span>", unsafe_allow_html=True)
            else: st.write("Nincs tipp.")
    with col_p:
        st.subheader(f"{row['Pontszám']} pont")
