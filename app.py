import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- 1. ALAPBEÁLLÍTÁSOK ÉS ADATOK ---
st.set_page_config(page_title="Midnight RWF Tracker", layout="wide", initial_sidebar_state="expanded")

ADMIN_PASSWORD = "rwfpred"  # Ezt írd át a sajátodra!

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

# --- 2. ADATBÁZIS KEZELÉS ---
def init_db():
    conn = sqlite3.connect('midnight_wf.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS predictions (user TEXT PRIMARY KEY, pw TEXT, data TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS official_wf (id INTEGER PRIMARY KEY, data TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY, status TEXT)')
    c.execute("INSERT OR IGNORE INTO settings (id, status) VALUES (1, 'open')")
    conn.commit()
    return conn

conn = init_db()
c = conn.cursor()

# --- 3. SESSION STATE INICIALIZÁLÁS ---
if 'user' not in st.session_state:
    st.session_state.user = None
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False

# --- 4. SEGÉDFÜGGVÉNYEK ---
def get_status():
    c.execute("SELECT status FROM settings WHERE id=1")
    return c.fetchone()[0]

def calculate_points(user_data, official_data):
    if not user_data or not official_data: return 0
    u_list, o_list = user_data.split(","), official_data.split(",")
    score = 0
    for i in range(20):
        u_cls, u_spc = u_list[i].split(":")
        o_cls, o_spc = o_list[i].split(":")
        if u_cls == o_cls:
            score += 2 if u_spc == o_spc else 1
    return score

# --- 5. OLDALSÁV (LOGIN & ADMIN LOGIKA) ---
with st.sidebar:
    st.title("⚔️ Midnight RWF")
    if st.session_state.user is None:
        u_in = st.text_input("Név")
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
                    else: st.error("Hibás jelszó!")
                else:
                    c.execute("INSERT INTO predictions VALUES (?,?,?)", (u_in, p_in, ""))
                    conn.commit()
                    st.session_state.user = u_in
            st.rerun()
    else:
        st.write(f"Bejelentkezve: **{st.session_state.user}**")
        if st.button("Kijelentkezés"):
            st.session_state.user = None
            st.session_state.is_admin = False
            st.rerun()

# --- 6. ADMIN FELÜLET ---
if st.session_state.is_admin:
    st.header("🛡️ Adminisztráció")
    
    # Tippek nyitása/zárása
    curr_status = get_status()
    st.subheader(f"Állapot: {'🟢 NYITVA' if curr_status == 'open' else '🔴 LEZÁRVA'}")
    col1, col2 = st.columns(2)
    if col1.button("🔓 Tippek Megnyitása"):
        c.execute("UPDATE settings SET status='open' WHERE id=1"); conn.commit(); st.rerun()
    if col2.button("🔒 Tippek Lezárása"):
        c.execute("UPDATE settings SET status='closed' WHERE id=1"); conn.commit(); st.rerun()

    # Hivatalos Comp beállítása
    with st.expander("🔴 HIVATALOS WORLD FIRST COMP BEÁLLÍTÁSA"):
        c.execute("SELECT data FROM official_wf WHERE id=1")
        off_res = c.fetchone()
        off_current = off_res[0].split(",") if off_res else ["Warrior:Arms"] * 20
        off_new = []
        grid = st.columns(4)
        for i in range(20):
            with grid[i%4]:
                sc, ss = off_current[i].split(":")
                c_sel = st.selectbox(f"WF C{i}", list(CLASSES.keys()), index=list(CLASSES.keys()).index(sc), key=f"wf_c_{i}")
                s_sel = st.selectbox(f"WF S{i}", CLASSES[c_sel], index=CLASSES[c_sel].index(ss) if ss in CLASSES[c_sel] else 0, key=f"wf_s_{i}")
                off_new.append(f"{c_sel}:{s_sel}")
        if st.button("HIVATALOS COMP MENTÉSE"):
            c.execute("INSERT OR REPLACE INTO official_wf (id, data) VALUES (1, ?)", (",".join(off_new),))
            conn.commit(); st.success("Mentve!")

# --- 7. FELHASZNÁLÓI SZERKESZTŐ ---
elif st.session_state.user:
    status = get_status()
    st.header(f"Raid Leader: {st.session_state.user}")
    
    if status == "open":
        c.execute("SELECT data FROM predictions WHERE user=?", (st.session_state.user,))
        saved = c.fetchone()[0]
        curr_preds = saved.split(",") if saved else ["Warrior:Arms"] * 20
        
        new_comp = []
        cols = st.columns(4)
        for g in range(4):
            with cols[g]:
                st.subheader(f"Group {g+1}")
                for p in range(5):
                    idx = g * 5 + p
                    sc, ss = curr_preds[idx].split(":")
                    c_sel = st.selectbox(f"Class", list(CLASSES.keys()), index=list(CLASSES.keys()).index(sc), key=f"u_c_{idx}", label_visibility="collapsed")
                    st.markdown(f'<div style="height:4px; background:{CLASS_COLORS[c_sel]};"></div>', unsafe_allow_html=True)
                    s_sel = st.selectbox(f"Spec", CLASSES[c_sel], index=CLASSES[c_sel].index(ss) if ss in CLASSES[c_sel] else 0, key=f"u_s_{idx}", label_visibility="collapsed")
                    new_comp.append(f"{c_sel}:{s_sel}")
                    st.write("") # Spacer
        
        if st.button("💾 COMP MENTÉSE", use_container_width=True):
            c.execute("UPDATE predictions SET data=? WHERE user=?", (",".join(new_comp), st.session_state.user))
            conn.commit(); st.success("Sikeres mentés!")
    else:
        st.warning("🔒 A tippleadás lezárult. Nézd meg a rangsort alul!")

# --- 8. LEADERBOARD & RANGSOR ---
# --- 8. LEADERBOARD & RANGSOR ---
st.divider()

# --- HIVATALOS COMP MEGJELENÍTÉSE (Ha már létezik) ---
c.execute("SELECT data FROM official_wf WHERE id=1")
wf_res = c.fetchone()
wf_data = wf_res[0] if wf_res else None

if wf_data:
    with st.container():
        st.markdown("""
            <div style="background: rgba(255, 215, 0, 0.1); border: 2px solid #FFD700; padding: 20px; border-radius: 10px; margin-bottom: 25px;">
                <h2 style="color: #FFD700; margin-top: 0; text-align: center;">🏆 HIVATALOS MIDNIGHT RWF COMP</h2>
            </div>
        """, unsafe_allow_html=True)
        
        wf_list = wf_data.split(",")
        wf_cols = st.columns(5) # 4 sorban 5 ikon
        for i, item in enumerate(wf_list):
            cn, sn = item.split(":")
            wf_cols[i%5].markdown(f"""
                <div style="text-align: center; border-bottom: 2px solid {CLASS_COLORS.get(cn, '#FFF')}; margin-bottom: 15px; padding: 5px;">
                    <small style="color: #ccc;">Slot {i+1}</small><br>
                    <b style="color: {CLASS_COLORS.get(cn, '#FFF')}">{sn}</b><br>
                    <span style="font-size: 0.8em;">{cn}</span>
                </div>
            """, unsafe_allow_html=True)
    st.divider()

st.header("📊 Guild Leaderboard")

c.execute("SELECT user, data FROM predictions")
users = c.fetchall()

lb_list = []
for u, d in users:
    # Az admin (te) ne szerepeljen a ranglistán, hacsak nem akarod
    if u == "Admin": continue
    
    pts = calculate_points(d, wf_data)
    accuracy = (pts / 40) * 100 if wf_data else 0
    lb_list.append({"Név": u, "Pont": pts, "Data": d, "Accuracy": accuracy})

if lb_list:
    df = pd.DataFrame(lb_list).sort_values(by="Pont", ascending=False)

    for _, row in df.iterrows():
        acc_text = f"({row['Accuracy']:.1f}%)" if wf_data else ""
        # Arany/Ezüst/Bronz kiemelés az első három helyezettnek
        rank_icon = "👤"
        if wf_data:
            idx = df.index.get_loc(_)
            if idx == 0: rank_icon = "🥇"
            elif idx == 1: rank_icon = "🥈"
            elif idx == 2: rank_icon = "🥉"

        with st.expander(f"{rank_icon} **{row['Pont']} pont** {acc_text} — {row['Név']}"):
            if row['Data']:
                d_list = row['Data'].split(",")
                r_cols = st.columns(5)
                for i, item in enumerate(d_list):
                    cn, sn = item.split(":")
                    
                    # Találat ellenőrzése a vizuális visszajelzéshez
                    is_correct = False
                    if wf_data:
                        o_list = wf_data.split(",")
                        o_cn, o_sn = o_list[i].split(":")
                        if cn == o_cn and sn == o_sn:
                            is_correct = True
                    
                    # Stílus: ha eltalálta, zölden világít a keret
                    bg_style = "border: 1px solid #444;"
                    if wf_data and is_correct:
                        bg_style = "border: 2px solid #28a745; background: rgba(40, 167, 69, 0.2);"
                    
                    r_cols[i%5].markdown(f"""
                        <div style="{bg_style} padding: 8px; border-radius: 6px; margin-bottom: 8px; text-align: center;">
                            <b style='color:{CLASS_COLORS.get(cn, "#FFF")}; font-size: 0.9em;'>{sn}</b><br>
                            <small style='color:#bbb;'>{cn}</small>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Még nincs beküldött tipp.")
else:
    st.info("Még nincsenek beküldött tippek.")
