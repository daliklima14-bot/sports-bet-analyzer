import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# ==============================
# CONFIGURAÇÕES BÁSICAS DO APP
# ==============================
st.set_page_config(page_title="Analisador de Partidas", layout="wide")
st.title("⚽ Analisador de Partidas - Futebol Inteligente")
st.write("Este app analisa automaticamente partidas e estatísticas reais das principais ligas.")

# ==============================
# CONFIGURAÇÕES DA API
# ==============================
API_KEY = "5ea0b77896d871932e2847dd2a4bd4b0"
API_URL = "https://v3.football.api-sports.io"
headers = {"x-apisports-key": API_KEY}

# ==============================
# LIGAS SUPORTADAS
# ==============================
LIGAS_DISPONIVEIS = {
    "Brasileirão Série A": 71,
    "Premier League": 39,
    "La Liga": 140,
    "Serie A (Itália)": 135,
    "Bundesliga": 78,
    "Ligue 1": 61
}

# ==============================
# FUNÇÃO PARA BUSCAR PARTIDAS
# ==============================
def buscar_partidas(league_id, data):
    url = f"{API_URL}/fixtures?league={league_id}&season=2025&date={data}"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        st.error("Erro ao buscar partidas. Verifique a chave da API.")
        return pd.DataFrame()

    data = response.json().get("response", [])
    partidas = []

    for jogo in data:
        partidas.append({
            "Competição": jogo["league"]["name"],
            "Data": jogo["fixture"]["date"][:10],
            "Mandante": jogo["teams"]["home"]["name"],
            "Visitante": jogo["teams"]["away"]["name"],
            "Odds (Mandante)": "-",
            "Odds (Empate)": "-",
            "Odds (Visitante)": "-"
        })

    return pd.DataFrame(partidas)

# ==============================
# FUNÇÃO PARA BUSCAR ESTATÍSTICAS REAIS
# ==============================
def buscar_estatisticas(df):
    if df.empty:
        return df

    estatisticas = []
    for _, row in df.iterrows():
        mandante = row["Mandante"]
        visitante = row["Visitante"]

        try:
            # Buscar classificação da liga
            url_class = f"{API_URL}/standings?league={LIGAS_DISPONIVEIS[row['Competição']]}&season=2025"
            resp_class = requests.get(url_class, headers=headers)
            tabela = resp_class.json().get("response", [])[0]["league"]["standings"][0]

            pos_mandante = next((t["rank"] for t in tabela if t["team"]["name"] == mandante), "-")
            pos_visitante = next((t["rank"] for t in tabela if t["team"]["name"] == visitante), "-")

            # Buscar estatísticas de gols
            url_mand = f"{API_URL}/teams/statistics?league={LIGAS_DISPONIVEIS[row['Competição']]}&season=2025&team={tabela[pos_mandante-1]['team']['id']}"
            url_vis = f"{API_URL}/teams/statistics?league={LIGAS_DISPONIVEIS[row['Competição']]}&season=2025&team={tabela[pos_visitante-1]['team']['id']}"
            stats_mand = requests.get(url_mand, headers=headers).json().get("response", {})
            stats_vis = requests.get(url_vis, headers=headers).json().get("response", {})

            mandante_gols = stats_mand.get("goals", {}).get("for", {}).get("average", {}).get("home", 0)
            visitante_gols = stats_vis.get("goals", {}).get("for", {}).get("average", {}).get("away", 0)

            # Histórico de confrontos (H2H)
            url_h2h = f"{API_URL}/fixtures/headtohead?h2h={tabela[pos_mandante-1]['team']['id']}-{tabela[pos_visitante-1]['team']['id']}"
            h2h = requests.get(url_h2h, headers=headers).json().get("response", [])
            ultimos_h2h = len(h2h)
            vitorias_mand = sum(1 for j in h2h if j["teams"]["home"]["name"] == mandante and j["teams"]["home"]["winner"])
            vitorias_vis = sum(1 for j in h2h if j["teams"]["away"]["name"] == visitante and j["teams"]["away"]["winner"])

            estatisticas.append({
                "Mandante": mandante,
                "Visitante": visitante,
                "Posição Mandante": pos_mandante,
                "Posição Visitante": pos_visitante,
                "Gols Médios Mandante": mandante_gols,
                "Gols Médios Visitante": visitante_gols,
                "Confrontos Diretos": ultimos_h2h,
                "Vitórias Mandante": vitorias_mand,
                "Vitórias Visitante": vitorias_vis
            })
        except Exception as e:
            print(f"Erro ao buscar estatísticas: {e}")
            estatisticas.append({
                "Mandante": mandante,
                "Visitante": visitante,
                "Posição Mandante": "-",
                "Posição Visitante": "-",
                "Gols Médios Mandante": "-",
                "Gols Médios Visitante": "-",
                "Confrontos Diretos": "-",
                "Vitórias Mandante": "-",
                "Vitórias Visitante": "-"
            })

    estats_df = pd.DataFrame(estatisticas)
    return df.merge(estats_df, on=["Mandante", "Visitante"], how="left")

# ==============================
# INTERFACE DO APP
# ==============================
col1, col2 = st.columns(2)
with col1:
    liga = st.selectbox("Escolha a Liga:", list(LIGAS_DISPONIVEIS.keys()))
with col2:
    data_jogos = st.date_input("Escolha a Data:", datetime.today())

if st.button("🔍 Buscar Jogos"):
    df_partidas = buscar_partidas(LIGAS_DISPONIVEIS[liga], data_jogos)
    df_partidas = buscar_estatisticas(df_partidas)

    if df_partidas.empty:
        st.warning("⚠️ Nenhum jogo encontrado para essa data.")
    else:
        st.dataframe(df_partidas, use_container_width=True)

        st.markdown("---")
        st.subheader("🎯 Simulação de Aposta (Retorno Esperado)")
        for _, row in df_partidas.iterrows():
            st.write(
                f"**{row['Mandante']} x {row['Visitante']}**  \n"
                f"🏅 Posições: {row['Posição Mandante']}º x {row['Posição Visitante']}º  \n"
                f"⚽ Gols Médios: {row['Gols Médios Mandante']} x {row['Gols Médios Visitante']}  \n"
                f"🏠 Mandante venceu {row['Vitórias Mandante']} dos últimos {row['Confrontos Diretos']} confrontos"
            )

# Rodapé
st.markdown("---")
st.caption("📈 Desenvolvido em parceria com IA para análise de apostas esportivas - versão beta")
