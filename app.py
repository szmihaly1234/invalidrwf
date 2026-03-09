import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- BEÁLLÍTÁSOK ---
DEADLINE = datetime(2026, 3, 24, 0, 0)
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

# --- ADATBÁZIS INICIALIZÁLÁS ---
conn = sqlite3.connect('predictions.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users 
             (username TEXT PRIMARY KEY, password TEXT, prediction TEXT)''')
conn.commit()

st.set_page_config(page_title="Midnight RWF Prediction", layout="wide")
st.title("⚔️ Midnight: Race to World First Prediction")

# --- AUTH LOGIKA ---
if 'user' not in st.session_state:
    st.session_state.user = None

col1, col2 = st.columns([2, 1])

with col2:
    st.subheader("Bejelentkezés / Regisztráció")
    user_input = st.text_input("Guild Tag Név")
    pass_input = st.text_input("Jelszó", type="password")
    
    if st.button("Belépés"):
        c.execute("SELECT password FROM users WHERE username=?", (user_input,))
        res = c.fetchone()
        if res:
            if res[0] == pass_input:
                st.session_state.user = user_input
                st.success(f"Üdv újra, {user_input}!")
            else:
                st.error("Hibás jelszó!")
        else:
            c.execute("INSERT INTO users VALUES (?, ?, ?)", (user_input, pass_input, ""))
            conn.commit()
            st.session_state.user = user_input
            st.success("Profil létrehozva!")

# --- PREDIKCIÓ SZERKESZTŐ ---
with col1:
    if st.session_state.user:
        st.header(f"Saját Raid Comp: {st.session_state.user}")
        
        if datetime.now() < DEADLINE:
            # Itt egy 20 elemű listát építünk
            my_comp = []
            cols = st.columns(4) # 5 sor x 4 oszlop a 20 fős raidhez
            
            for i in range(20):
                with cols[i % 4]:
                    st.write(f"Slot {i+1}")
                    cls = st.selectbox(f"Class {i}", list(CLASSES.keys()), key=f"cls_{i}")
                    spc = st.selectbox(f"Spec {i}", CLASSES[cls], key=f"spc_{i}")
                    my_comp.append(f"{cls}:{spc}")
            
            if st.button("Mentés"):
                comp_str = ",".join(my_comp)
                c.execute("UPDATE users SET prediction=? WHERE username=?", (comp_str, st.session_state.user))
                conn.commit()
                st.balloons()
                st.success("Tippek elmentve!")
        else:
            st.warning("A beküldési határidő lejárt!")

# --- LEADERBOARD & MEGTEKINTÉS ---
st.divider()
st.header("🏆 Leaderboard & Tippek")
c.execute("SELECT username, prediction FROM users")
all_users = c.fetchall()

if all_users:
    for u_name, u_pred in all_users:
        with st.expander(f"👤 {u_name} tippjei"):
            if u_pred:
                items = u_pred.split(",")
                df = pd.DataFrame([i.split(":") for i in items], columns=["Class", "Spec"])
                st.table(df)
            else:
                st.write("Még nem töltötte ki.")
