# app.py
# Webapp de paris (pari mutuel) pour une course le 6 décembre
# Usage : streamlit run app.py

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(page_title="Course - Paris entre amis", page_icon="🏁", layout="wide")

# ------------------------
# Init session state
# ------------------------
def init_state():
    if "participants" not in st.session_state:
        st.session_state.participants = pd.DataFrame(columns=["id", "nom"])
    if "bets" not in st.session_state:
        st.session_state.bets = pd.DataFrame(columns=["parieur", "selection_id", "selection_nom", "mise", "timestamp"])
    if "winner_id" not in st.session_state:
        st.session_state.winner_id = None
    if "race_date" not in st.session_state:
        year = datetime.now().year
        st.session_state.race_date = datetime(year, 12, 6).date()
    if "rake" not in st.session_state:
        st.session_state.rake = 0.05  # 5%

init_state()

# ------------------------
# Cotes pari mutuel
# ------------------------
def compute_pool_metrics(bets_df, rake):
    if bets_df.empty:
        return 0.0, 0.0, pd.Series(dtype=float), {}, {}

    total_pool = bets_df["mise"].sum()
    pool_net = total_pool * (1 - rake)
    mises_par = bets_df.groupby("selection_id")["mise"].sum()

    cotes, probas = {}, {}
    for pid, mise_runner in mises_par.items():
        cote = pool_net / mise_runner if mise_runner > 0 else None
        cotes[pid] = cote
        probas[pid] = (mise_runner / total_pool) * 100 if total_pool > 0 else 0

    for pid in st.session_state.participants["id"].tolist():
        if pid not in cotes:
            cotes[pid], probas[pid] = None, 0.0

    return total_pool, pool_net, mises_par, cotes, probas

def settle_payouts(bets_df, winner_id, rake):
    if bets_df.empty or winner_id is None:
        return pd.DataFrame(), {}

    total_pool, pool_net, mises_par, cotes, _ = compute_pool_metrics(bets_df, rake)
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
# Sidebar
# ------------------------
st.sidebar.title("⚙️ Paramètres")
st.session_state.race_date = st.sidebar.date_input("Date de la course", value=st.session_state.race_date)
rake_percent = st.sidebar.slider("Commission (%)", 0, 15, int(st.session_state.rake * 100))
st.session_state.rake = rake_percent / 100

if st.sidebar.button("♻️ Réinitialiser"):
    st.session_state.clear()
    init_state()
    st.success("Réinitialisé.")

# ------------------------
# Header
# ------------------------
st.title("🏁 Paris entre amis — Course du 6 décembre")
st.caption(f"Date : **{st.session_state.race_date.strftime('%d.%m.%Y')}** | Rake : **{int(st.session_state.rake*100)}%**")

tab1, tab2, tab3, tab4 = st.tabs(["👥 Participants", "💸 Paris", "📊 Cotes", "🏆 Résultats"])

# --- Participants ---
with tab1:
    with st.form("add_participant", clear_on_submit=True):
        nom = st.text_input("Nom du participant")
        if st.form_submit_button("Ajouter") and nom.strip():
            new_id = 1 if st.session_state.participants.empty else int(st.session_state.participants["id"].max()) + 1
            st.session_state.participants.loc[len(st.session_state.participants)] = [new_id, nom.strip()]
            st.success(f"{nom.strip()} ajouté.")

    if not st.session_state.participants.empty:
        st.session_state.participants["nom"] = st.session_state.participants["nom"].apply(lambda x: f"**{x}**")
        st.dataframe(st.session_state.participants, use_container_width=True)

        to_remove = st.selectbox(
            "Supprimer participant",
            options=[None] + st.session_state.participants["id"].tolist(),
            format_func=lambda pid: "—" if pid is None else st.session_state.participants.loc[st.session_state.participants["id"] == pid, "nom"].values[0]
        )
        if st.button("Supprimer") and to_remove is not None:
            st.session_state.participants = st.session_state.participants[st.session_state.participants["id"] != to_remove]
            st.session_state.bets = st.session_state.bets[st.session_state.bets["selection_id"] != to_remove]
            st.success("Supprimé.")

# --- Paris ---
with tab2:
    if st.session_state.participants.empty:
        st.info("Ajoute des participants d'abord.")
    else:
        with st.form("place_bet", clear_on_submit=True):
            parieur = st.text_input("Ton nom/pseudo")
            sel_id = st.selectbox(
                "Choix du participant",
                options=st.session_state.participants["id"],
                format_func=lambda pid: f"👉 {st.session_state.participants.loc[st.session_state.participants['id'] == pid, 'nom'].values[0]}"
            )
            mise = st.number_input("Mise (CHF)", min_value=1.0, step=1.0)
            if st.form_submit_button("Parier 💸"):
                sel_nom = st.session_state.participants.loc[st.session_state.participants["id"] == sel_id, "nom"].values[0]
                st.session_state.bets.loc[len(st.session_state.bets)] = [parieur.strip(), sel_id, sel_nom, mise, datetime.now().isoformat()]
                st.success(f"{parieur.strip()} → {sel_nom} ({mise} CHF)")

        if not st.session_state.bets.empty:
            df_bets = st.session_state.bets.copy()
            df_bets["selection_nom"] = df_bets["selection_nom"].apply(lambda x: f"**{x}**")
            st.dataframe(df_bets, use_container_width=True)

# --- Cotes ---
with tab3:
    total, net, mises, cotes, probas = compute_pool_metrics(st.session_state.bets, st.session_state.rake)
    
    col1, col2 = st.columns(2)
    col1.metric("Total pool", f"{total:.2f} CHF")
    col2.metric("Net (après rake)", f"{net:.2f} CHF")

    rows = []
    for _, r in st.session_state.participants.iterrows():
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

    st.caption("Cote = (pool net après commission) ÷ (mises sur le participant).")

# --- Résultats ---
with tab4:
    if st.session_state.participants.empty:
        st.info("Ajoute des participants.")
    else:
        winner = st.selectbox(
            "Vainqueur",
            options=[None] + st.session_state.participants["id"].tolist(),
            format_func=lambda pid: "—" if pid is None else st.session_state.participants.loc[st.session_state.participants["id"] == pid, "nom"].values[0]
        )
        if st.button("Enregistrer vainqueur"):
            st.session_state.winner_id = winner

    if st.session_state.winner_id:
        wdf, resume = settle_payouts(st.session_state.bets, st.session_state.winner_id, st.session_state.rake)
        st.write(resume)
        if not wdf.empty:
            wdf["selection_nom"] = wdf["selection_nom"].apply(lambda x: f"**{x}**")
            st.dataframe(wdf, use_container_width=True)
