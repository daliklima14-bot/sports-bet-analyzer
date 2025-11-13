import streamlit as st
import requests
import pandas as pd
from datetime import date
import time

# -----------------------------------
# ⚙️ CONFIGURAÇÕES INICIAIS
# -----------------------------------

st.set_page_config(page_title="Analisador de Apostas", page_icon="⚽", layout="centered")

st.title("⚽ Analisador e Simulador de Apostas Esportivas")
st.write("App automatizado para buscar estatísticas e calcular probabilidades das partidas do dia.")

# 🔑 Pega a API Key direto do secret configurado no Streamlit
API_KEY = st.secrets["FOOTBALL_DATA_API_KEY"]

# 🌍 URL base da API
API_URL = "https://api.football-data.org/v4/matches"

# 🧾 Cabeçalho da requisição
headers = {"X-Auth-Token": API_KEY}


# -----------------------------------
# 🔍 FUNÇÃO PARA BUSCAR PARTIDAS
# -----------------------------------
def buscar_partidas(data_jogos, ligas):
    """Busca partidas das ligas selecionadas para uma data específica."""
    resultados = []

    for liga in ligas:
        # Monta URL correta no formato esperado pela API football-data.org
        url = f"https://api.football-data.org/v4/competitions/{liga}/matches?dateFrom={data_jogos}&dateTo={data_jogos}"

        try:
            resp = requests.get(url, headers=headers)
            if resp.status_code == 200:
                dados = resp.json().get("matches", [])
                if not dados:
                    st.warning(f"Nenhuma partida encontrada para a liga {liga} nessa data.")
                for match in dados:
                    resultados.append({
                        "Competição": liga,
                        "Data": match["utcDate"][:10],
                        "Hora": match["utcDate"][11:16],
                        "Mandante": match["homeTeam"]["name"],
                        "Visitante": match["awayTeam"]["name"],
                        "Status": match["status"]
                    })
            else:
                st.warning(f"Erro ao buscar {liga}: {resp.status_code} - {resp.text}")
        except Exception as e:
            st.error(f"Erro: {e}")

    return pd.DataFrame(resultados)


def calcular_probabilidades(df):
    """Cria probabilidades simuladas (mock) para teste."""
    import random
    df["Prob_Mandante"] = [round(random.uniform(0.4, 0.7), 2) for _ in range(len(df))]
    df["Prob_Visitante"] = [round(1 - p, 2) for p in df["Prob_Mandante"]]
    df["Odds_Mandante"] = [round(1 / p, 2) for p in df["Prob_Mandante"]]
    df["Odds_Visitante"] = [round(1 / p, 2) for p in df["Prob_Visitante"]]
    return df


def simular_aposta(df, banca, stake):
    """Simula retorno de apostas baseadas nas probabilidades."""
    df["Lucro_Esperado"] = round((df["Prob_Mandante"] * (df["Odds_Mandante"] - 1) - (1 - df["Prob_Mandante"])) * stake, 2)
    ganho_total = df["Lucro_Esperado"].sum()
    nova_banca = banca + ganho_total
    return df, ganho_total, nova_banca

# -------------------------------
# 📅 BUSCA DE PARTIDAS
# -------------------------------
st.subheader("📅 Partidas do Dia")

data_jogos = st.date_input("Selecione a data:", value=date.today())
ligas_disponiveis = {
    "Brasileirão Série A": "BSA",
    "Premier League": "PL",
    "La Liga": "PD",
    "Champions League": "CL"
}
ligas_selecionadas = st.multiselect("Selecione as ligas:", list(ligas_disponiveis.keys()), default=["Brasileirão Série A"])

if st.button("Buscar Partidas"):
    ligas_api = [ligas_disponiveis[l] for l in ligas_selecionadas]
    with st.spinner("Buscando partidas e calculando probabilidades..."):
        time.sleep(1)
        df_jogos = buscar_partidas(str(data_jogos), ligas_api)
        if not df_jogos.empty:
            df_prob = calcular_probabilidades(df_jogos)
            st.success("✅ Partidas e probabilidades obtidas com sucesso!")
            st.dataframe(df_prob)
        else:
            st.warning("Nenhuma partida encontrada para essa data.")

# -------------------------------
# 💰 SIMULAÇÃO DE APOSTA
# -------------------------------
st.subheader("💰 Simulação de Aposta")

banca_inicial = st.number_input("Informe sua banca inicial (R$):", min_value=10.0, value=100.0, step=10.0)
stake = st.number_input("Informe o valor por aposta (stake) (R$):", min_value=1.0, value=10.0, step=1.0)

if st.button("Simular Retorno"):
    try:
        df_sim, ganho, nova_banca = simular_aposta(df_prob, banca_inicial, stake)
        st.dataframe(df_sim[["Mandante", "Visitante", "Odds_Mandante", "Odds_Visitante", "Lucro_Esperado"]])
        st.success(f"💵 Lucro total estimado: R$ {ganho:.2f}")
        st.info(f"Nova banca estimada: R$ {nova_banca:.2f}")
    except Exception:
        st.warning("⚠️ Busque as partidas antes de simular.")
