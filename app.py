import streamlit as st
import sqlite3

# --- KONFIG ÉS DB SETUP ---
# (A színeket és classokat hagyd meg a korábbiak szerint)

conn = sqlite3.connect('midnight_wf.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY, status TEXT)')
# Ha még üres a settings, alapértelmezetten legyen "open"
c.execute("INSERT OR IGNORE INTO settings (id, status) VALUES (1, 'open')")
conn.commit()

# Segédfüggvény a státusz lekéréséhez
def get_prediction_status():
    c.execute("SELECT status FROM settings WHERE id=1")
    return c.fetchone()[0]

# --- ADMIN FELÜLET ---
if st.session_state.is_admin:
    st.divider()
    st.subheader("⚙️ Rendszerbeállítások")
    
    current_status = get_prediction_status()
    status_text = "🟢 NYITVA" if current_status == "open" else "🔴 LEZÁRVA"
    st.write(f"Jelenlegi állapot: **{status_text}**")
    
    col_admin1, col_admin2 = st.columns(2)
    with col_admin1:
        if st.button("🔓 Tippek megnyitása", use_container_width=True):
            c.execute("UPDATE settings SET status='open' WHERE id=1")
            conn.commit()
            st.success("A tippleadás mostantól mindenki számára elérhető!")
            st.rerun()
            
    with col_admin2:
        if st.button("🔒 Tippek lezárása", use_container_width=True):
            c.execute("UPDATE settings SET status='closed' WHERE id=1")
            conn.commit()
            st.warning("A tippleadást lezártad!")
            st.rerun()

# --- USER JÁTÉK FELÜLET (Szerkesztés ellenőrzése) ---
if st.session_state.user and not st.session_state.is_admin:
    prediction_status = get_prediction_status()
    
    if prediction_status == "open":
        st.header(f"Raid Leader: {st.session_state.user}")
        # ... Ide jön a 4x5-ös választó grid kódja ...
        
        if st.button("💾 COMP MENTÉSE", use_container_width=True):
            # Mentés folyamata...
            st.success("Sikeresen mentve!")
    else:
        st.error("🛑 A tippleadás jelenleg le van zárva! Már csak a Leaderboardot láthatod.")
        # Itt csak megmutatjuk a korábbi mentését, de nem módosíthatja
        # (Használhatod a Leaderboard kódját a megjelenítéshez)
