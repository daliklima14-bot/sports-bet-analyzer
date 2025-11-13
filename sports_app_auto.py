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
    
# ==============================
# BUSCA AUTOMÁTICA DE PARTIDAS DO DIA (API + ANÁLISE)
# ==============================
import requests
from datetime import datetime, date
import streamlit as st

st.header("📅 Partidas do Dia (Busca Automática e Análise de Probabilidades)")

# === Configuração inicial ===
API_KEY = st.secrets.get("FOOTBALL_DATA_API_KEY", "COLOQUE_SUA_API_AQUI")

ligas_dict = {
    "Premier League": "PL",
    "La Liga": "PD",
    "Série A (Itália)": "SA",
    "Bundesliga": "BL1",
    "Ligue 1": "FL1",
    "Brasileirão Série A": "BSA",
}

# Selecionar data e ligas
data_escolhida = st.date_input("Selecione a data para buscar jogos:", date.today(), key="data_busca")
data_formatada = data_escolhida.strftime("%Y-%m-%d")

ligas_escolhidas = st.multiselect(
    "Selecione as ligas:",
    options=list(ligas_dict.keys()),
    default=["Brasileirão Série A"]
)

if not API_KEY or API_KEY.startswith("COLOQUE"):
    st.warning("⚠️ Configure sua chave API no .streamlit/secrets.toml")
else:
    try:
        headers = {"X-Auth-Token": API_KEY}
        st.info(f"🔄 Buscando partidas de {data_formatada}...")
        jogos_analise = []

        for nome_liga in ligas_escolhidas:
            liga_id = ligas_dict[nome_liga]
            url = f"https://api.football-data.org/v4/competitions/{liga_id}/matches?dateFrom={data_formatada}&dateTo={data_formatada}"
            resp = requests.get(url, headers=headers)

            if resp.status_code == 200:
                data = resp.json()
                partidas = data.get("matches", [])
                if partidas:
                    st.subheader(f"🏆 {nome_liga}")
                    for p in partidas:
                        casa = p["homeTeam"]["name"]
                        fora = p["awayTeam"]["name"]
                        hora = p["utcDate"][11:16]
                        status = p["status"]

                        # === Buscar odds ===
                        odds_url = f"https://api.football-data.org/v4/matches/{p['id']}/odds"
                        odds_resp = requests.get(odds_url, headers=headers)

                        if odds_resp.status_code == 200:
                            odds_data = odds_resp.json()
                            mercados = odds_data.get("bookmakers", [])
                            if mercados:
                                try:
                                    mercado_principal = mercados[0]["bets"][0]["values"]
                                    odd_casa = float(mercado_principal[0]["odd"])
                                    odd_empate = float(mercado_principal[1]["odd"])
                                    odd_fora = float(mercado_principal[2]["odd"])

                                    # === Calcular probabilidades implícitas ===
                                    total = (1/odd_casa + 1/odd_empate + 1/odd_fora)
                                    prob_casa = (1/odd_casa)/total*100
                                    prob_empate = (1/odd_empate)/total*100
                                    prob_fora = (1/odd_fora)/total*100

                                    # === Análise simples de valor esperado ===
                                    maior_prob = max(prob_casa, prob_empate, prob_fora)
                                    if maior_prob == prob_casa:
                                        sugestao = f"🏠 Vitória do {casa}"
                                    elif maior_prob == prob_empate:
                                        sugestao = "🤝 Empate"
                                    else:
                                        sugestao = f"🛫 Vitória do {fora}"

                                    # Valor esperado aproximado (EV = probabilidade * odd - 1)
                                    EV_casa = (prob_casa/100)*odd_casa - 1
                                    EV_empate = (prob_empate/100)*odd_empate - 1
                                    EV_fora = (prob_fora/100)*odd_fora - 1

                                    melhor_EV = max(EV_casa, EV_empate, EV_fora)
                                    if melhor_EV > 0:
                                        valor = "💰 **Aposta de Valor Encontrada!**"
                                    else:
                                        valor = "⚖️ Aposta equilibrada (sem valor claro)"

                                    st.markdown(f"### 🕒 {hora} — {casa} 🆚 {fora}")
                                    st.write(f"Status: `{status}`")
                                    st.write(
                                        f"**Odds:** 🏠 {odd_casa} | 🤝 {odd_empate} | 🛫 {odd_fora}"
                                    )
                                    st.write(
                                        f"**Probabilidades:** 🏠 {prob_casa:.1f}% | 🤝 {prob_empate:.1f}% | 🛫 {prob_fora:.1f}%"
                                    )
                                    st.info(f"🔍 Sugestão: {sugestao}")
                                    st.success(valor)
                                    st.divider()

                                except Exception:
                                    st.write(f"**{hora} — {casa} 🆚 {fora}** _(odds não disponíveis)_")
                        else:
                            st.write(f"**{hora} — {casa} 🆚 {fora}** _(sem odds disponíveis)_")
                else:
                    st.info(f"Nenhuma partida encontrada para {nome_liga}.")
            else:
                st.error(f"Erro ao acessar dados de {nome_liga}: {resp.status_code}")
    except Exception as e:
        st.error(f"Erro ao buscar partidas: {e}")

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
