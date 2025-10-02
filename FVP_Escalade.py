# app.py
# Webapp de paris (pari mutuel) pour une course le 6 décembre
# Version avec SQLite (persistance automatique + suppression de paris)

import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime

st.set_page_config(page_title="Paris DPM", page_icon="🏁", layout="wide")

DB_FILE = "data.db"

# ------------------------
# DB Setup
# ------------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS participants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nom TEXT UNIQUE
                )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS bets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    parieur TEXT,
                    selection_id INTEGER,
                    selection_nom TEXT,
                    mise REAL,
                    timestamp TEXT
                )""")
    conn.commit()
    conn.close()

def get_participants():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql("SELECT * FROM participants", conn)
    conn.close()
    return df

def add_participant(nom):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO participants (nom) VALUES (?)", (nom,))
    conn.commit()
    conn.close()

def delete_participant(pid):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("DELETE FROM participants WHERE id=?", (pid,))
    cur.execute("DELETE FROM bets WHERE selection_id=?", (pid,))
    conn.commit()
    conn.close()

def get_bets():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql("SELECT * FROM bets", conn)
    conn.close()
    return df

def add_bet(parieur, sel_id, sel_nom, mise):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("INSERT INTO bets (parieur, selection_id, selection_nom, mise, timestamp) VALUES (?,?,?,?,?)",
                (parieur, sel_id, sel_nom, mise, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def delete_bet(bet_id):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("DELETE FROM bets WHERE id=?", (bet_id,))
    conn.commit()
    conn.close()

# ------------------------
# Cotes pari mutuel
# ------------------------
def compute_pool_metrics(bets_df, rake, participants):
    if bets_df.empty:
        return 0.0, 0.0, pd.Series(dtype=float), {}, {}

    total_pool = bets_df["mise"].sum()
    pool_net = total_pool * (1 - rake)
    mises_par = bets_df.groupby("selection_id")["mise"].sum()

    cotes, probas = {}, {}
    for pid, mise_runner in mises_par.items():
        cote = pool_net / mise_runner if mise_runner > 0 else None
        cotes[int(pid)] = cote
        probas[int(pid)] = (mise_runner / total_pool) * 100 if total_pool > 0 else 0

    for pid in participants["id"].tolist():
        if int(pid) not in cotes:
            cotes[int(pid)], probas[int(pid)] = None, 0.0

    return total_pool, pool_net, mises_par, cotes, probas

def settle_payouts(bets_df, winner_id, rake):
    if bets_df.empty or winner_id is None:
        return pd.DataFrame(), {}

    total_pool, pool_net, mises_par, cotes, _ = compute_pool_metrics(bets_df, rake, get_participants())
    if winner_id not in cotes or cotes[winner_id] is None:
        return pd.DataFrame(), {"total_pool": total_pool, "pool_net": pool_net}

    cote_gagnant = cotes[winner_id]
    winners_bets = bets_df[bets_df["selection_id"] == winner_id].copy()
    winners_bets["cote"] = cote_gagnant
    winners_bets["gain"] = winners_bets["mise"] * winners_bets["cote"]

    return winners_bets, {
        "total_pool": total_pool,
        "pool_net": pool_net,
        "gagnant_mises": mises_par.get(winner_id, 0.0),
        "redistribue": winners_bets["gain"].sum(),
        "commission": total_pool - pool_net,
    }

# ------------------------
# Init
# ------------------------
init_db()
if "winner_id" not in st.session_state:
    st.session_state.winner_id = None
if "race_date" not in st.session_state:
    year = datetime.now().year
    st.session_state.race_date = datetime(year, 12, 6).date()
if "rake" not in st.session_state:
    st.session_state.rake = 0.05

# ------------------------
# Sidebar
# ------------------------
st.sidebar.title("⚙️ Paramètres")
st.session_state.race_date = st.sidebar.date_input("Date de la course", value=st.session_state.race_date)
rake_percent = st.sidebar.slider("Commission (%)", 0, 15, int(st.session_state.rake * 100))
st.session_state.rake = rake_percent / 100
if st.sidebar.button("♻️ Réinitialiser (tout effacer)"):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("DELETE FROM participants")
    cur.execute("DELETE FROM bets")
    conn.commit()
    conn.close()
    st.session_state.winner_id = None
    st.success("Base vidée.")

# ------------------------
# Header
# ------------------------
st.title("🏁 Paris DPM — Course du 6 décembre")
st.caption(f"Date : **{st.session_state.race_date.strftime('%d.%m.%Y')}** | Rake : **{int(st.session_state.rake*100)}%**")

tab1, tab2, tab3, tab4 = st.tabs(["👥 Participants", "💸 Paris", "📊 Cotes", "🏆 Résultats"])

# --- Participants ---
with tab1:
    with st.form("add_participant", clear_on_submit=True):
        nom = st.text_input("Nom du participant")
        if st.form_submit_button("Ajouter") and nom.strip():
            add_participant(nom.strip())
            st.success(f"{nom.strip()} ajouté.")

    participants = get_participants()
    if participants.empty:
        st.info("Aucun participant pour l’instant.")
    else:
        st.markdown("### 👥 Liste des participants")
        for _, row in participants.iterrows():
            st.markdown(f"<h3>• {row['nom']}</h3>", unsafe_allow_html=True)

        to_remove = st.selectbox(
            "Supprimer un participant",
            options=participants["id"],
            format_func=lambda pid: participants.loc[participants["id"] == pid, "nom"].values[0]
        )
        if st.button("Supprimer participant"):
            delete_participant(int(to_remove))
            st.success("Supprimé.")

# --- Paris ---
with tab2:
    participants = get_participants()
    if participants.empty:
        st.info("Ajoute des participants d’abord.")
    else:
        with st.form("place_bet", clear_on_submit=True):
            parieur = st.text_input("Ton nom/pseudo")
            sel_id = st.selectbox(
                "Choix du participant",
                options=participants["id"],
                format_func=lambda pid: f"👉 {participants.loc[participants['id'] == pid, 'nom'].values[0]}"
            )
            mise = st.number_input("Mise (CHF)", min_value=1.0, step=1.0)
            if st.form_submit_button("Parier 💸"):
                sel_nom = participants.loc[participants["id"] == sel_id, "nom"].values[0]
                add_bet(parieur.strip(), int(sel_id), sel_nom, float(mise))
                st.success(f"{parieur.strip()} → {sel_nom} ({mise} CHF)")

        bets = get_bets()
        if not bets.empty:
            bets["selection_nom"] = bets["selection_nom"].apply(lambda x: f"**{x}**")
            st.dataframe(bets, use_container_width=True)

            st.markdown("### ❌ Supprimer un pari")
            bet_to_del = st.selectbox(
                "Choisir un pari à supprimer",
                options=bets["id"],
                format_func=lambda bid: f"{bets.loc[bets['id']==bid, 'parieur'].values[0]} → {bets.loc[bets['id']==bid, 'selection_nom'].values[0]} ({bets.loc[bets['id']==bid, 'mise'].values[0]} CHF)"
            )
            if st.button("Supprimer ce pari"):
                delete_bet(int(bet_to_del))
                st.success("Pari supprimé.")

# --- Cotes ---
with tab3:
    participants = get_participants()
    bets = get_bets()
    total, net, mises, cotes, probas = compute_pool_metrics(bets, st.session_state.rake, participants)
    
    col1, col2 = st.columns(2)
    col1.metric("Total pool", f"{total:.2f} CHF")
    col2.metric("Net (après rake)", f"{net:.2f} CHF")

    rows = []
    for _, r in participants.iterrows():
        pid = int(r["id"])
        cote = cotes.get(pid, None)
        rows.append({
            "Nom": f"**{r['nom']}**",
            "Mises (CHF)": mises.get(pid, 0.0),
            "Cote": "—" if cote is None else f"{cote:.2f}",
            "Proba": f"{probas.get(pid, 0.0):.1f}%"
        })
    
    df_market = pd.DataFrame(rows)
    st.dataframe(df_market, use_container_width=True)

# --- Résultats ---
with tab4:
    participants = get_participants()
    bets = get_bets()
    if participants.empty:
        st.info("Ajoute des participants.")
    else:
        winner = st.selectbox(
            "Vainqueur",
            options=[None] + participants["id"].tolist(),
            format_func=lambda pid: "—" if pid is None else participants.loc[participants["id"] == pid, "nom"].values[0]
        )
        if st.button("Enregistrer vainqueur"):
            st.session_state.winner_id = winner

    if st.session_state.winner_id:
        wdf, resume = settle_payouts(bets, int(st.session_state.winner_id), st.session_state.rake)
        st.write(resume)
        if not wdf.empty:
            wdf["selection_nom"] = wdf["selection_nom"].apply(lambda x: f"**{x}**")
            st.dataframe(wdf, use_container_width=True)
