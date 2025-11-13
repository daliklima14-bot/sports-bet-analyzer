import streamlit as st
import pandas as pd
import numpy as np

# ==============================
# CONFIGURAÇÕES DO APP
# ==============================
st.set_page_config(
    page_title="Analisador de Apostas Esportivas",
    page_icon="⚽",
    layout="wide"
)

st.title("⚽ Analisador e Simulador de Apostas Esportivas")
st.markdown("App automatizado para análise de probabilidades e simulação de resultados.")

# ==============================
# UPLOAD DO ARQUIVO
# ==============================
uploaded_file = st.file_uploader("Envie o arquivo Excel com previsões (ex: resultados_previsões.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)

        st.success("✅ Arquivo carregado com sucesso!")
        st.write("Prévia dos dados:")
        st.dataframe(df.head())

        # ==============================
        # ANÁLISE ESTATÍSTICA
        # ==============================
        st.subheader("📊 Estatísticas Gerais")

        stats = {
            "Total de Jogos": len(df),
            "Média de Probabilidade de Vitória Casa": round(df['prob_casa'].mean(), 2) if 'prob_casa' in df else 'N/A',
            "Média de Probabilidade de Vitória Fora": round(df['prob_fora'].mean(), 2) if 'prob_fora' in df else 'N/A',
            "Média de Empate": round(df['prob_empate'].mean(), 2) if 'prob_empate' in df else 'N/A',
        }

        st.json(stats)

        # ==============================
        # FILTROS DE ANÁLISE
        # ==============================
        st.subheader("🎯 Filtros de Probabilidade")
        min_prob = st.slider("Probabilidade mínima para mostrar (Casa)", 0.0, 1.0, 0.5)
        df_filtrado = df[df['prob_casa'] >= min_prob] if 'prob_casa' in df else df

        st.write("Resultados filtrados:")
        st.dataframe(df_filtrado)

        # ==============================
        # SIMULAÇÃO DE APOSTA
        # ==============================
        st.subheader("💰 Simulação de Aposta")
        valor_aposta = st.number_input("Valor da aposta (R$)", min_value=1.0, value=10.0, step=1.0)

        if st.button("Simular ganhos"):
            if 'odd_casa' in df_filtrado:
                df_filtrado['retorno'] = np.where(df_filtrado['resultado'] == 'Casa',
                                                  valor_aposta * df_filtrado['odd_casa'],
                                                  0)
                ganho_total = df_filtrado['retorno'].sum()
                st.success(f"💵 Ganho total simulado: R$ {ganho_total:,.2f}")
            else:
                st.warning("O arquivo precisa conter uma coluna chamada 'odd_casa' e 'resultado'.")

    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")

else:
    st.info("📁 Faça upload do seu arquivo Excel para começar a análise.")
# ============================================
# BUSCA AUTOMÁTICA DE PARTIDAS DO DIA (API)
# ============================================

import requests
from datetime import date, timedelta

# =============================
# BUSCA AUTOMÁTICA DE PARTIDAS
# =============================

st.subheader("📅 Partidas do Dia (Busca Automática)")

# Seleção de data e ligas
col1, col2 = st.columns(2)
data_escolhida = col1.date_input("Escolha uma data:", date.today())

ligas_disponiveis = {
    "Premier League": "PL",
    "La Liga": "PD",
    "Serie A (Itália)": "SA",
    "Bundesliga": "BL1",
    "Ligue 1": "FL1",
    "Brasileirão Série A": "BSA",
    "Champions League": "CL"
}

ligas_escolhidas = col2.multiselect("Selecione as ligas:", list(ligas_disponiveis.keys()), default=["Premier League"])

# Chave da API
import os
api_key = os.getenv("FOOTBALL_DATA_API_KEY")

if not api_key:
    st.warning("⚠️ Adicione sua API Key em .streamlit/secrets.toml para ativar a busca automática.")
else:
    url_base = "https://api.football-data.org/v4/competitions/{liga}/matches"
    headers = {"X-Auth-Token": api_key}

    partidas_encontradas = False

    for nome_liga, codigo_liga in ligas_disponiveis.items():
        if nome_liga not in ligas_escolhidas:
            continue

        url = url_base.format(liga=codigo_liga)
        params = {"dateFrom": data_escolhida.isoformat(), "dateTo": data_escolhida.isoformat()}
        resp = requests.get(url, headers=headers, params=params)

        if resp.status_code == 200:
            dados = resp.json()
            partidas = dados.get("matches", [])

            if len(partidas) > 0:
                partidas_encontradas = True
                st.markdown(f"### 🏆 {nome_liga}")
                for p in partidas:
                    casa = p['homeTeam']['name']
                    fora = p['awayTeam']['name']
                    hora = p['utcDate'][11:16]
                    st.write(f"**{hora}** — {casa} 🆚 {fora}")
        else:
            st.error(f"Erro ao buscar {nome_liga}: {resp.status_code}")

    if not partidas_encontradas:
        st.info("Nenhuma partida encontrada para as ligas selecionadas nesta data.")
