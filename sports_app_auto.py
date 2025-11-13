import streamlit as st
import pandas as pd
import requests
import random
from datetime import datetime

# ⚙️ CONFIGURAÇÕES INICIAIS
st.set_page_config(page_title="Analisador de Apostas", page_icon="⚽", layout="centered")

st.title("⚽ Analisador e Simulador de Apostas Esportivas")
st.write("App automatizado para buscar estatísticas e calcular probabilidades das partidas do dia.")

# 🧩 API FOOTBALL CONFIG
API_KEY = st.secrets["API_FOOTBALL_KEY"]
API_URL = "https://v3.football.api-sports.io"
headers = {"x-apisports-key": API_KEY}

# IDs das ligas que você quer (pode adicionar mais)
LIGAS_DISPONIVEIS = {
    "Brasileirão Série A": 71,
    "Premier League": 39,
}

# 🧮 FUNÇÃO PARA BUSCAR PARTIDAS
def buscar_partidas(data_jogo, ligas):
    resultados = []
    for nome, id_liga in LIGAS_DISPONIVEIS.items():
        if nome in ligas:
            url = f"{API_URL}/fixtures?date={data_jogo}&league={id_liga}&season=2025"
            try:
                resp = requests.get(url, headers=headers)
                if resp.status_code == 200:
                    dados = resp.json().get("response", [])
                    for partida in dados:
                        resultados.append({
                            "Competição": nome,
                            "Data": partida["fixture"]["date"][:10],
                            "Hora": partida["fixture"]["date"][11:16],
                            "Mandante": partida["teams"]["home"]["name"],
                            "Visitante": partida["teams"]["away"]["name"],
                            "Status": partida["fixture"]["status"]["short"]
                        })
                else:
                    st.warning(f"Erro {resp.status_code} ao buscar {nome}")
            except Exception as e:
                st.error(f"Erro ao buscar {nome}: {e}")
    return pd.DataFrame(resultados)

# 🎯 FUNÇÃO PARA GERAR PROBABILIDADES MOCKADAS
def calcular_probabilidades(df):
    if df.empty:
        return df
    df["Prob_Mandante"] = [round(random.uniform(0.4, 0.75), 2) for _ in range(len(df))]
    df["Prob_Visitante"] = [round(1 - p, 2) for p in df["Prob_Mandante"]]
    return df

# 🗓️ SEÇÃO DE INPUTS
st.subheader("📅 Partidas do Dia")
data_jogo = st.date_input("Selecione a data:", datetime.today())
ligas = st.multiselect("Selecione as ligas:", options=list(LIGAS_DISPONIVEIS.keys()))

if st.button("Buscar Partidas"):
    with st.spinner("Buscando partidas e estatísticas..."):
        df_partidas = buscar_partidas(data_jogo, ligas)
        df_partidas = calcular_probabilidades(df_partidas)
        if not df_partidas.empty:
            st.success("✅ Partidas e probabilidades obtidas com sucesso!")
            st.dataframe(df_partidas, use_container_width=True)
        else:
            st.warning("Nenhuma partida encontrada para essa data ou liga selecionada.")

# 💰 SEÇÃO DE SIMULAÇÃO
st.subheader("💰 Simulação de Aposta")
banca = st.number_input("Informe sua banca inicial (R$):", value=100.0, step=10.0)
stake = st.number_input("Informe o valor por aposta (stake) (R$):", value=10.0, step=5.0)

if st.button("Simular Retorno"):
    try:
        total_apostas = int(banca // stake)
        lucro_estimado = round(total_apostas * random.uniform(-0.2, 0.5) * stake, 2)
        st.info(f"💸 Retorno estimado: R$ {banca + lucro_estimado}")
    except:
        st.error("Erro ao simular retorno.")
