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
from datetime import datetime

st.header("📅 Partidas do Dia (Busca Automática)")

# Configuração inicial (troque pela sua API key quando tiver)
API_KEY = st.secrets.get("FOOTBALL_DATA_API_KEY", "COLOQUE_SUA_API_AQUI")
LEAGUES = ["PL", "PD", "SA", "FL1", "BSA"]  # Premier League, LaLiga, Serie A, Ligue 1, Brasileirão

if API_KEY == "COLOQUE_SUA_API_AQUI":
    st.warning("⚠️ Adicione sua API Key em .streamlit/secrets.toml para ativar a busca automática.")
else:
    hoje = datetime.now().strftime("%Y-%m-%d")
    url = f"https://api.football-data.org/v4/matches?dateFrom={hoje}&dateTo={hoje}"
    headers = {"X-Auth-Token": API_KEY}

    try:
        response = requests.get(url, headers=headers)
        data = response.json()

        if "matches" in data:
            jogos_hoje = [
                {
                    "Competição": match["competition"]["name"],
                    "Casa": match["homeTeam"]["name"],
                    "Fora": match["awayTeam"]["name"],
                    "Status": match["status"]
                }
                for match in data["matches"]
                if match["competition"]["code"] in LEAGUES
            ]

            if jogos_hoje:
                st.success(f"{len(jogos_hoje)} partidas encontradas para hoje!")
                st.dataframe(jogos_hoje)
            else:
                st.info("Nenhuma partida encontrada para as ligas selecionadas hoje.")
        else:
            st.warning("Nenhum dado recebido da API.")

    except Exception as e:
        st.error(f"Erro ao buscar dados da API: {e}")
