import streamlit as st
import sqlite3
from datetime import datetime

# --- KONFIGURÁCIÓ & WOW SZÍNEK ---
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
conn.commit()

st.set_page_config(page_title="Midnight RWF Builder", layout="wide")

# Egyedi CSS a Raid Frame kinézethez
st.markdown(f"""
    <style>
    .raid-slot {{
        border: 1px solid #444;
        padding: 10px;
        border-radius: 5px;
        background-color: #1a1a1a;
        margin-bottom: 5px;
        text-align: center;
    }}
    </style>
""", unsafe_allow_html=True)

# --- AUTH ---
if 'user' not in st.session_state: st.session_state.user = None

with st.sidebar:
    st.title("⚔️ Midnight RWF")
    u_in = st.text_input("Név")
    p_in = st.text_input("Jelszó", type="password")
    if st.button("Bejelentkezés / Regisztráció"):
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

# --- MAIN UI ---
if st.session_state.user:
    # ELŐZŐ ADATOK BETÖLTÉSE
    c.execute("SELECT data FROM predictions WHERE user=?", (st.session_state.user,))
    saved_data = c.fetchone()[0]
    # Ha van mentett adat, listává alakítjuk, ha nincs, 20 üres slot
    current_preds = saved_data.split(",") if saved_data else ["Death Knight:Blood"] * 20
    
    st.header(f"Raid Leader: {st.session_state.user}")
    
    # 4 oszlop = 4 Group (WoW stílus)
    groups = st.columns(4)
    new_comp = []

    for g_idx in range(4):
        with groups[g_idx]:
            st.subheader(f"Group {g_idx + 1}")
            for p_idx in range(5):
                slot_id = g_idx * 5 + p_idx
                # Meglévő érték kibontása a betöltéshez
                saved_cls, saved_spc = current_preds[slot_id].split(":")
                
                # UI Slot kártya
                with st.container():
                    # Class választó (visszatölti az előzőt az 'index' segítségével)
                    cls_list = list(CLASSES.keys())
                    selected_cls = st.selectbox(f"Class", cls_list, 
                                               index=cls_list.index(saved_cls), 
                                               key=f"c_{slot_id}", label_visibility="collapsed")
                    
                    # Dinamikus Spec szín és választó
                    color = CLASS_COLORS[selected_cls]
                    st.markdown(f'<div style="height:5px; background-color:{color}; border-radius:2px;"></div>', unsafe_allow_html=True)
                    
                    spec_list = CLASSES[selected_cls]
                    # Hibakezelés, ha a spec nem létezik a választott classban (pl. váltásnál)
                    spec_idx = spec_list.index(saved_spc) if saved_spc in spec_list else 0
                    selected_spc = st.selectbox(f"Spec", spec_list, 
                                               index=spec_idx,
                                               key=f"s_{slot_id}", label_visibility="collapsed")
                    
                    new_comp.append(f"{selected_cls}:{selected_spc}")
                st.markdown("---")

    if st.button("💾 COMP MENTÉSE", use_container_width=True):
        if datetime.now() < DEADLINE:
            final_str = ",".join(new_comp)
            c.execute("UPDATE predictions SET data=? WHERE user=?", (final_str, st.session_state.user))
            conn.commit()
            st.success("Sikeresen mentve!")
        else:
            st.error("A határidő lejárt!")

# --- LEADERBOARD ---
st.divider()
st.subheader("📊 Guild Tippek")
c.execute("SELECT user, data FROM predictions")
for u, d in c.fetchall():
    if d:
        with st.expander(f"{u} predikciója"):
            # Itt egy mini gridben mutatjuk meg a többiekét
            l_cols = st.columns(10) # 2 sorban 10-10
            d_list = d.split(",")
            for i, item in enumerate(d_list):
                c_name, s_name = item.split(":")
                l_cols[i%10].markdown(f"**{s_name}** \n<span style='color:{CLASS_COLORS[c_name]}'>{c_name}</span>", unsafe_allow_html=True)
