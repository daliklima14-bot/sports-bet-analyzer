import streamlit as st
import pandas as pd
import requests
import random
from datetime import datetime

# ============================
# ⚙️ CONFIGURAÇÕES INICIAIS
# ============================

st.set_page_config(page_title="Analisador de Apostas", page_icon="⚽", layout="centered")

st.title("⚽ Analisador e Simulador de Apostas Esportivas")
st.write("App automatizado para buscar estatísticas e calcular probabilidades reais das partidas do dia.")

# Pega a API key configurada no Streamlit
API_KEY = st.secrets["FOOTBALL_DATA_API_KEY"]

# URL base da API
BASE_URL = "https://api.football-data.org/v4"
headers = {"X-Auth-Token": API_KEY}


# ============================
# 🔍 FUNÇÃO PARA BUSCAR PARTIDAS
# ============================

def buscar_partidas(data_jogos, ligas):
    resultados = []

    for liga in ligas:
        url = f"{BASE_URL}/competitions/{liga}/matches?dateFrom={data_jogos}&dateTo={data_jogos}"
        try:
            resp = requests.get(url, headers=headers)
            if resp.status_code == 200:
                dados = resp.json().get("matches", [])
                if not dados:
                    st.warning(f"Nenhuma partida encontrada para a liga {liga} nessa data.")
                    continue

                for match in dados:
                    resultados.append({
                        "Competição": liga,
                        "Data": match["utcDate"][:10],
                        "Hora": match["utcDate"][11:16],
                        "Mandante": match["homeTeam"]["name"],
                        "Visitante": match["awayTeam"]["name"],
                        "Status": match["status"],
                        "ID": match["id"]
                    })
            else:
                st.warning(f"Erro ao buscar {liga}: ({resp.status_code}) - {resp.text}")

        except Exception as e:
            st.error(f"Erro: {e}")

    return pd.DataFrame(resultados)


# ============================
# 💰 FUNÇÃO PARA BUSCAR ODDS REAIS
# ============================

def buscar_odds_reais(match_id):
    try:
        url = f"{BASE_URL}/matches/{match_id}"
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            odds = data.get("odds", {})
            if odds:
                home = odds.get("homeWin", None)
                draw = odds.get("draw", None)
                away = odds.get("awayWin", None)
                return home, draw, away
    except:
        pass
    return None, None, None


# ============================
# 📊 CALCULAR PROBABILIDADES
# ============================

def calcular_probabilidades(df, modo):
    probs_mandante = []
    probs_visitante = []

    for _, row in df.iterrows():
        if modo == "Odds Reais (API)":
            odd_home, odd_draw, odd_away = buscar_odds_reais(row["ID"])
            if odd_home and odd_away:
                p_home = round((1 / odd_home) / ((1 / odd_home) + (1 / odd_away)), 2)
                p_away = round(1 - p_home, 2)
            else:
                p_home = round(random.uniform(0.4, 0.7), 2)
                p_away = round(1 - p_home, 2)
        else:
            # Simulação aleatória
            p_home = round(random.uniform(0.4, 0.7), 2)
            p_away = round(1 - p_home, 2)

        probs_mandante.append(p_home)
        probs_visitante.append(p_away)

    df["Prob_Mandante"] = probs_mandante
    df["Prob_Visitante"] = probs_visitante
    return df


# ============================
# 🎲 SIMULAÇÃO DE APOSTA
# ============================

def simular_apostas(banca, stake, df):
    resultados = []
    for _, row in df.iterrows():
        ganho = round(stake * (1 / row["Prob_Mandante"]), 2)
        perda = stake
        resultados.append(ganho - perda)
    total = round(sum(resultados), 2)
    banca_final = round(banca + total, 2)
    return banca_final, total


# ============================
# 🧩 INTERFACE
# ============================

st.subheader("📅 Partidas do Dia")

data_jogos = st.date_input("Selecione a data:", datetime.now())
ligas_disp = {
    "Brasileirão Série A": "BSA",
    "Premier League": "PL",
    "La Liga": "PD",
    "Serie A (Itália)": "SA",
    "Bundesliga": "BL1"
}
ligas = st.multiselect("Selecione as ligas:", list(ligas_disp.keys()), default=["Brasileirão Série A"])

# Novo seletor de modo de análise
modo = st.radio("Modo de análise:", ["Odds Reais (API)", "Simulação Aleatória"], horizontal=True)

if st.button("Buscar Partidas"):
    ligas_cod = [ligas_disp[l] for l in ligas]
    df_partidas = buscar_partidas(data_jogos, ligas_cod)
    if not df_partidas.empty:
        df_prob = calcular_probabilidades(df_partidas, modo)
        st.success("✅ Partidas e probabilidades obtidas com sucesso!")
        st.dataframe(df_prob)
        st.session_state["df_partidas"] = df_prob
    else:
        st.warning("Nenhuma partida encontrada para essa data.")

st.subheader("💸 Simulação de Aposta")

banca = st.number_input("Informe sua banca inicial (R$):", min_value=10.0, value=100.0, step=10.0)
stake = st.number_input("Informe o valor por aposta (stake) (R$):", min_value=1.0, value=10.0, step=1.0)

if st.button("Simular Retorno"):
    if "df_partidas" not in st.session_state or st.session_state["df_partidas"].empty:
        st.warning("⚠️ Nenhuma partida disponível para simulação.")
    else:
        df = st.session_state["df_partidas"]
        banca_final, lucro_total = simular_apostas(banca, stake, df)
        st.info(f"💰 Lucro total estimado: R$ {lucro_total:.2f}")
        st.success(f"🏦 Banca final projetada: R$ {banca_final:.2f}")
