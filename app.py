import streamlit as st
import sqlite3
import pandas as pd
import json
import base64

# --- 1. ALAPBEÁLLÍTÁSOK ---
st.set_page_config(page_title="Midnight RWF Tracker", layout="wide")

ADMIN_PASSWORD = "rwfpred" 

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
def get_db_connection():
    conn = sqlite3.connect('rwf_data.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

conn = get_db_connection()
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, prediction TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)')
c.execute("INSERT OR IGNORE INTO meta (key, value) VALUES ('status', 'open')")
c.execute("INSERT OR IGNORE INTO meta (key, value) VALUES ('official_wf', '')")
conn.commit()

# --- 3. PONTOZÓ LOGIKA (SLOT-FÜGGETLEN) ---
def calculate_points(user_data, official_data):
    if not user_data or not official_data: return 0
    u_list = [x for x in user_data.split(",") if x]
    o_list = [x for x in official_data.split(",") if x]
    
    rem_off = list(o_list)
    score = 0
    u_rem = []
    
    # 1. Kör: Teljes találat (Spec + Class)
    for u in u_list:
        if u in rem_off:
            score += 2
            rem_off.remove(u)
        else:
            u_rem.append(u)
            
    # 2. Kör: Csak Kaszt találat
    for u in u_rem:
        u_cls = u.split(":")[0]
        for i, o in enumerate(rem_off):
            if u_cls == o.split(":")[0]:
                score += 1
                rem_off.pop(i)
                break
    return score

# --- 4. SESSION STATE ---
if 'user' not in st.session_state: st.session_state.user = None
if 'is_admin' not in st.session_state: st.session_state.is_admin = False

# --- 5. SIDEBAR / LOGIN ---
with st.sidebar:
    st.title("⚔️ Midnight RWF")
    if not st.session_state.user:
        u_name = st.text_input("Név")
        u_pass = st.text_input("Jelszó", type="password")
        if st.button("Belépés / Regisztráció"):
            if u_name == "admin" and u_pass == ADMIN_PASSWORD:
                st.session_state.is_admin = True
                st.session_state.user = "Admin"
                st.rerun()
            else:
                c.execute("SELECT password FROM users WHERE username=?", (u_name,))
                res = c.fetchone()
                if res:
                    if res[0] == u_pass:
                        st.session_state.user = u_name
                        st.rerun()
                    else: st.error("Hibás jelszó!")
                else:
                    c.execute("INSERT INTO users VALUES (?,?,?)", (u_name, u_pass, ""))
                    conn.commit()
                    st.session_state.user = u_name
                    st.rerun()
    else:
        st.success(f"Bejelentkezve: {st.session_state.user}")
        if st.button("Kijelentkezés"):
            st.session_state.user = None
            st.session_state.is_admin = False
            st.rerun()

# --- 6. ADMIN PANEL ---
if st.session_state.is_admin:
    st.header("🛡️ Admin Panel")
    
    # Státusz és WF Comp betöltése
    c.execute("SELECT value FROM meta WHERE key='status'")
    status = c.fetchone()[0]
    c.execute("SELECT value FROM meta WHERE key='official_wf'")
    official_wf = c.fetchone()[0]

    col1, col2 = st.columns(2)
    if col1.button(f"🔓 NYITÁS (Most: {status})"):
        c.execute("UPDATE meta SET value='open' WHERE key='status'")
        conn.commit(); st.rerun()
    if col2.button(f"🔒 ZÁRÁS (Most: {status})"):
        c.execute("UPDATE meta SET value='closed' WHERE key='status'")
        conn.commit(); st.rerun()

    with st.expander("🔴 HIVATALOS WF COMP BEÁLLÍTÁSA"):
        off_curr = official_wf.split(",") if official_wf else ["Warrior:Arms"] * 20
        off_new = []
        grid = st.columns(4)
        for i in range(20):
            with grid[i%4]:
                sc, ss = off_curr[i].split(":")
                c_sel = st.selectbox(f"WF {i+1}", list(CLASSES.keys()), index=list(CLASSES.keys()).index(sc), key=f"wf_c_{i}")
                s_sel = st.selectbox(f"S {i+1}", CLASSES[c_sel], index=CLASSES[c_sel].index(ss) if ss in CLASSES[c_sel] else 0, key=f"wf_s_{i}")
                off_new.append(f"{c_sel}:{s_sel}")
        if st.button("WF COMP MENTÉSE"):
            c.execute("UPDATE meta SET value=? WHERE key='official_wf'", (",".join(off_new),))
            conn.commit(); st.success("Mentve!")

    # --- ADATMENTÉS (BACKUP) RÉSZ ---
    st.divider()
    st.subheader("💾 Adatvédelem (Adatvesztés ellen)")
    
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        if st.button("📥 BACKUP KÓD GENERÁLÁSA"):
            c.execute("SELECT * FROM users")
            u_rows = [dict(r) for r in c.fetchall()]
            backup_data = {"users": u_rows, "wf": off_new if 'off_new' in locals() else official_wf}
            st.code(json.dumps(backup_data), language="json")
            st.info("Másold ki ezt a kódot és mentsd el egy fájlba a gépeden!")

    with col_b2:
        restore_code = st.text_area("Visszaállító kód helye", placeholder="Ide illeszd be a mentett JSON-t...")
        if st.button("📤 VISSZAÁLLÍTÁS"):
            try:
                data = json.loads(restore_code)
                for u in data["users"]:
                    c.execute("INSERT OR REPLACE INTO users VALUES (?,?,?)", (u['username'], u['password'], u['prediction']))
                if "wf" in data:
                    c.execute("UPDATE meta SET value=? WHERE key='official_wf'", (data['wf'] if isinstance(data['wf'], str) else ",".join(data['wf']),))
                conn.commit()
                st.success("Adatok sikeresen visszaállítva!")
                st.rerun()
            except Exception as e: st.error(f"Hiba: {e}")

# --- 7. USER EDITOR ---
elif st.session_state.user:
    c.execute("SELECT value FROM meta WHERE key='status'")
    if c.fetchone()[0] == 'open':
        st.header("🎮 Állítsd össze a 20 fős csapatod!")
        c.execute("SELECT prediction FROM users WHERE username=?", (st.session_state.user,))
        saved = c.fetchone()[0]
        curr = saved.split(",") if saved else ["Warrior:Arms"] * 20
        
        new_comp = []
        cols = st.columns(4)
        for g in range(4):
            with cols[g]:
                st.subheader(f"{g+1}. Csoport")
                for p in range(5):
                    idx = g*5+p
                    sc, ss = curr[idx].split(":")
                    c_sel = st.selectbox(f"C{idx}", list(CLASSES.keys()), index=list(CLASSES.keys()).index(sc), key=f"u_c_{idx}", label_visibility="collapsed")
                    st.markdown(f'<div style="height:3px; background:{CLASS_COLORS[c_sel]}; margin-bottom:5px;"></div>', unsafe_allow_html=True)
                    s_sel = st.selectbox(f"S{idx}", CLASSES[c_sel], index=CLASSES[c_sel].index(ss) if ss in CLASSES[c_sel] else 0, key=f"u_s_{idx}", label_visibility="collapsed")
                    new_comp.append(f"{c_sel}:{s_sel}")
        
        if st.button("💾 TIPPEK MENTÉSE", use_container_width=True):
            c.execute("UPDATE users SET prediction=? WHERE username=?", (",".join(new_comp), st.session_state.user))
            conn.commit(); st.balloons(); st.success("Mentve!")
    else:
        st.warning("🔒 A fogadás lezárult!")

# --- 8. LEADERBOARD ---
st.divider()
c.execute("SELECT value FROM meta WHERE key='official_wf'")
wf_data = c.fetchone()[0]

if wf_data:
    st.markdown("<h3 style='text-align:center;'>🏆 WORLD FIRST COMP</h3>", unsafe_allow_html=True)
    wf_cols = st.columns(10)
    for i, item in enumerate(wf_data.split(",")):
        cn, sn = item.split(":")
        wf_cols[i%10].markdown(f"<div style='font-size:10px; text-align:center; border-bottom:2px solid {CLASS_COLORS[cn]}'>{sn}</div>", unsafe_allow_html=True)

st.header("📊 Ranglista")
c.execute("SELECT username, prediction FROM users")
all_users = c.fetchall()

lb = []
for u, d in all_users:
    if u == "Admin": continue
    p = calculate_points(d, wf_data)
    lb.append({"Név": u, "Pont": p, "Data": d})

if lb:
    df = pd.DataFrame(lb).sort_values(by="Pont", ascending=False)
    for _, row in df.iterrows():
        with st.expander(f"**{row['Pont']} pont** — {row['Név']}"):
            if row['Data']:
                d_list = row['Data'].split(",")
                o_list = wf_data.split(",") if wf_data else []
                r_cols = st.columns(5)
                for j, item in enumerate(d_list):
                    cn, sn = item.split(":")
                    # Vizualizáció: zöld keret ha benne van a compban
                    is_correct = item in o_list
                    style = f"border: 1px solid {'#28a745' if is_correct else '#444'}; background: {'rgba(40,167,69,0.1)' if is_correct else 'none'}"
                    r_cols[j%5].markdown(f"<div style='{style}; padding:5px; border-radius:3px; font-size:11px; text-align:center;'><b style='color:{CLASS_COLORS[cn]}'>{sn}</b></div>", unsafe_allow_html=True)
