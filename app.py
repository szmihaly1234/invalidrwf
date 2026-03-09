import streamlit as st
import sqlite3
import pandas as pd
import json

# --- 1. KONFIGURÁCIÓ ---
st.set_page_config(page_title="Midnight RWF Tracker", layout="wide")

ADMIN_PASSWORD = "guild_mester_jelszo" # Ezt írd át a sajátodra!

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
def get_db():
    conn = sqlite3.connect('rwf_final.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, prediction TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)')
    c.execute("INSERT OR IGNORE INTO meta (key, value) VALUES ('status', 'open')")
    c.execute("INSERT OR IGNORE INTO meta (key, value) VALUES ('official_wf', '')")
    conn.commit()
    return conn

conn = get_db()
cursor = conn.cursor()

# --- 3. PONTOZÓ LOGIKA ---
def calculate_points(user_data, official_data):
    if not user_data or not official_data: return 0
    u_list = [x for x in user_data.split(",") if x]
    o_list = [x for x in official_data.split(",") if x]
    rem_off = list(o_list)
    score = 0
    u_rem = []
    # 2 pont: Spec + Class
    for u in u_list:
        if u in rem_off:
            score += 2; rem_off.remove(u)
        else: u_rem.append(u)
    # 1 pont: Csak Class
    for u in u_rem:
        u_cls = u.split(":")[0]
        for i, o in enumerate(rem_off):
            if u_cls == o.split(":")[0]:
                score += 1; rem_off.pop(i); break
    return score

# --- 4. SESSION STATE ---
if 'user' not in st.session_state: st.session_state.user = None
if 'is_admin' not in st.session_state: st.session_state.is_admin = False

# --- 5. SIDEBAR / LOGIN ---
with st.sidebar:
    st.title("⚔️ Midnight RWF")
    if not st.session_state.user:
        u_in = st.text_input("Név")
        p_in = st.text_input("Jelszó", type="password")
        if st.button("Belépés / Regisztráció"):
            if u_in == "admin" and p_in == ADMIN_PASSWORD:
                st.session_state.is_admin = True; st.session_state.user = "Admin"
                st.rerun()
            else:
                cursor.execute("SELECT password FROM users WHERE username=?", (u_in,))
                res = cursor.fetchone()
                if res:
                    if res[0] == p_in: st.session_state.user = u_in; st.rerun()
                    else: st.error("Rossz jelszó!")
                else:
                    cursor.execute("INSERT INTO users VALUES (?,?,?)", (u_in, p_in, ""))
                    conn.commit(); st.session_state.user = u_in; st.rerun()
    else:
        st.write(f"Üdv, **{st.session_state.user}**!")
        if st.button("Kijelentkezés"):
            st.session_state.user = None; st.session_state.is_admin = False; st.rerun()

# --- 6. ADMIN PANEL ---
if st.session_state.is_admin:
    st.header("🛡️ Adminisztráció")
    cursor.execute("SELECT value FROM meta WHERE key='status'")
    status = cursor.fetchone()[0]
    cursor.execute("SELECT value FROM meta WHERE key='official_wf'")
    official_wf = cursor.fetchone()[0]

    c1, c2 = st.columns(2)
    if c1.button(f"🔓 NYITÁS (Most: {status})"):
        cursor.execute("UPDATE meta SET value='open' WHERE key='status'"); conn.commit(); st.rerun()
    if c2.button(f"🔒 ZÁRÁS (Most: {status})"):
        cursor.execute("UPDATE meta SET value='closed' WHERE key='status'"); conn.commit(); st.rerun()

    with st.expander("🔴 HIVATALOS COMP BEÁLLÍTÁSA"):
        off_curr = official_wf.split(",") if official_wf else ["Warrior:Arms"] * 20
        off_new = []
        grid = st.columns(4)
        for i in range(20):
            with grid[i%4]:
                sc, ss = off_curr[i].split(":")
                c_sel = st.selectbox(f"C {i+1}", list(CLASSES.keys()), index=list(CLASSES.keys()).index(sc), key=f"wf_c_{i}")
                s_sel = st.selectbox(f"S {i+1}", CLASSES[c_sel], index=0 if ss not in CLASSES[c_sel] else CLASSES[c_sel].index(ss), key=f"wf_s_{i}")
                off_new.append(f"{c_sel}:{s_sel}")
        if st.button("WF MENTÉSE"):
            cursor.execute("UPDATE meta SET value=? WHERE key='official_wf'", (",".join(off_new),))
            conn.commit(); st.success("Mentve!")

    with st.expander("💾 ADATMENTÉS ÉS BACKUP"):
        if st.button("BACKUP KÓD GENERÁLÁSA"):
            cursor.execute("SELECT * FROM users")
            u_data = [dict(r) for r in cursor.fetchall()]
            st.code(json.dumps({"users": u_data, "wf": official_wf}))
        
        restore = st.text_area("Restore kód beillesztése")
        if st.button("ADATOK VISSZAÁLLÍTÁSA"):
            try:
                d = json.loads(restore)
                for u in d["users"]:
                    cursor.execute("INSERT OR REPLACE INTO users VALUES (?,?,?)", (u['username'], u['password'], u['prediction']))
                cursor.execute("UPDATE meta SET value=? WHERE key='official_wf'", (d['wf'],))
                conn.commit(); st.success("Sikeres visszaállítás!"); st.rerun()
            except: st.error("Érvénytelen kód!")

# --- 7. USER EDITOR ---
elif st.session_state.user:
    cursor.execute("SELECT value FROM meta WHERE key='status'")
    if cursor.fetchone()[0] == 'open':
        st.header("🎮 Tippjeid szerkesztése")
        cursor.execute("SELECT prediction FROM users WHERE username=?", (st.session_state.user,))
        saved = cursor.fetchone()[0]
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
                    s_sel = st.selectbox(f"S{idx}", CLASSES[c_sel], index=0 if ss not in CLASSES[c_sel] else CLASSES[c_sel].index(ss), key=f"u_s_{idx}", label_visibility="collapsed")
                    new_comp.append(f"{c_sel}:{s_sel}")
        if st.button("💾 MENTÉS", use_container_width=True):
            cursor.execute("UPDATE users SET prediction=? WHERE username=?", (",".join(new_comp), st.session_state.user))
            conn.commit(); st.balloons()
    else: st.warning("🔒 A fogadás lezárult!")

# --- 8. LEADERBOARD ÉS RWF KIJELZŐ ---
st.divider()
cursor.execute("SELECT value FROM meta WHERE key='official_wf'")
wf_data = cursor.fetchone()[0]

if wf_data:
    st.markdown("""
        <div style="background: rgba(255, 215, 0, 0.05); border: 1px solid #FFD700; border-radius: 15px; padding: 20px; margin-bottom: 20px;">
            <h2 style='text-align:center; color:#FFD700; margin:0; font-family: sans-serif;'>🏆 HIVATALOS RWF COMP</h2>
        </div>
    """, unsafe_allow_html=True)
    
    wf_items = wf_data.split(",")
    for r in range(4): # 4 sor
        wf_cols = st.columns(5)
        for c in range(5):
            idx = r*5+c
            cn, sn = wf_items[idx].split(":")
            wf_cols[c].markdown(f"""
                <div style="text-align:center; padding:12px 5px; border-radius:8px; background:rgba(0,0,0,0.2); border-left:5px solid {CLASS_COLORS.get(cn, '#FFF')}; margin-bottom:10px;">
                    <b style="color:{CLASS_COLORS.get(cn, '#FFF')}; font-size:18px; display:block;">{sn}</b>
                    <span style="color:#aaa; font-size:13px;">{cn}</span>
                </div>
            """, unsafe_allow_html=True)

st.header("📊 Guild Leaderboard")
cursor.execute("SELECT username, prediction FROM users")
all_u = cursor.fetchall()
lb = []
for u, d in all_u:
    if u == "Admin" or d == "": continue
    p = calculate_points(d, wf_data)
    lb.append({"Név": u, "Pont": p, "Data": d})

if lb:
    df = pd.DataFrame(lb).sort_values(by="Pont", ascending=False)
    for _, row in df.iterrows():
        with st.expander(f"**{row['Pont']} pont** — {row['Név']}"):
            u_list = row['Data'].split(",")
            o_list = wf_data.split(",") if wf_data else []
            
            # Vizuális logika: pontszámítás szimulálása a színezéshez
            rem_off_visual = list(o_list)
            perfect_hits = []
            for i, u_item in enumerate(u_list):
                if u_item in rem_off_visual:
                    perfect_hits.append(i); rem_off_visual.remove(u_item)
            
            r_cols = st.columns(5)
            for j, item in enumerate(u_list):
                cn, sn = item.split(":")
                style = "border: 1px solid #444;"
                icon = ""
                
                if wf_data:
                    if j in perfect_hits:
                        style = "border: 2px solid #28a745; background: rgba(40, 167, 69, 0.2);"
                        icon = "✅"
                    else:
                        found_cls = False
                        for idx, o in enumerate(rem_off_visual):
                            if cn == o.split(":")[0]:
                                style = "border: 2px solid #ffcc00; background: rgba(255, 204, 0, 0.15);"
                                icon = "🔸"; rem_off_visual.pop(idx); found_cls = True; break
                
                r_cols[j%5].markdown(f"""
                    <div style="{style} padding:8px; border-radius:5px; font-size:11px; text-align:center; margin-bottom:5px;">
                        <b style='color:{CLASS_COLORS.get(cn, "#FFF")}'>{sn}</b><br>{cn} {icon}
                    </div>
                """, unsafe_allow_html=True)
else: st.info("Még nincs adat.")
