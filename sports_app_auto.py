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
        st.write("📄 Prévia dos dados:")
        st.dataframe(df.head())

    except Exception as e:
        st.error(f"❌ Erro ao carregar o arquivo: {e}")

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

        # ============================================
# 📊 ANÁLISE ESTATÍSTICA E DE ODDS
# ============================================
st.subheader("📊 Análise Estatística e de Odds (Probabilidades e Value Bets)")

if 'df' in locals() or 'df' in globals():
    try:
        # Verifica se o arquivo tem as colunas necessárias
        colunas_necessarias = ['HomeTeam', 'AwayTeam', 'Pred_H', 'Pred_D', 'Pred_A']
        if all(col in df.columns for col in colunas_necessarias):

            # Mostra tabela básica de probabilidades
            st.markdown("### ⚽ Probabilidades Previstas")
            st.dataframe(
                df[['HomeTeam', 'AwayTeam', 'Pred_H', 'Pred_D', 'Pred_A']].rename(
                    columns={
                        'HomeTeam': 'Mandante',
                        'AwayTeam': 'Visitante',
                        'Pred_H': 'Vitória Casa (%)',
                        'Pred_D': 'Empate (%)',
                        'Pred_A': 'Vitória Fora (%)'
                    }
                )
            )

            # Se houver odds, faz análise de valor esperado
            if all(col in df.columns for col in ['Home_Odd', 'Draw_Odd', 'Away_Odd']):
                st.markdown("### 💰 Análise de Odds e Valor Esperado")

                # Calcula odds justas
                df['Fair_H'] = 1 / df['Pred_H']
                df['Fair_D'] = 1 / df['Pred_D']
                df['Fair_A'] = 1 / df['Pred_A']

                # Calcula valor esperado
                df['Value_H'] = (df['Home_Odd'] * df['Pred_H']) - 1
                df['Value_D'] = (df['Draw_Odd'] * df['Pred_D']) - 1
                df['Value_A'] = (df['Away_Odd'] * df['Pred_A']) - 1

                # Monta tabela final
                tabela_odds = df[[
                    'HomeTeam', 'AwayTeam',
                    'Home_Odd', 'Draw_Odd', 'Away_Odd',
                    'Fair_H', 'Fair_D', 'Fair_A',
                    'Value_H', 'Value_D', 'Value_A'
                ]]

                st.dataframe(tabela_odds.rename(columns={
                    'HomeTeam': 'Mandante',
                    'AwayTeam': 'Visitante',
                    'Home_Odd': 'Odd Casa',
                    'Draw_Odd': 'Odd Empate',
                    'Away_Odd': 'Odd Fora',
                    'Fair_H': 'Odd Justa Casa',
                    'Fair_D': 'Odd Justa Empate',
                    'Fair_A': 'Odd Justa Fora',
                    'Value_H': 'Value Casa',
                    'Value_D': 'Value Empate',
                    'Value_A': 'Value Fora'
                }))

                # Destaque apostas de valor
                melhores_apostas = df[
                    (df['Value_H'] > 0) | (df['Value_D'] > 0) | (df['Value_A'] > 0)
                ]
                if not melhores_apostas.empty:
                    st.success("🎯 Apostas de Valor Encontradas:")
                    for _, row in melhores_apostas.iterrows():
                        if row['Value_H'] > 0:
                            st.write(f"🏠 {row['HomeTeam']} — Value: **{row['Value_H']:.2f}**")
                        if row['Value_D'] > 0:
                            st.write(f"🤝 Empate — Value: **{row['Value_D']:.2f}**")
                        if row['Value_A'] > 0:
                            st.write(f"🚀 {row['AwayTeam']} — Value: **{row['Value_A']:.2f}**")
                else:
                    st.warning("⚠️ Nenhuma aposta de valor encontrada com as probabilidades atuais.")

            else:
                st.info("Adicione colunas de odds (Home_Odd, Draw_Odd, Away_Odd) no seu Excel para ver análise de valor esperado.")

        else:
            st.error("O arquivo Excel precisa conter as colunas: HomeTeam, AwayTeam, Pred_H, Pred_D, Pred_A.")

    except Exception as e:
        st.error(f"Erro ao processar análises: {e}")

else:
    st.info("Envie o arquivo Excel para começar a análise.")

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
        
        # =========================================
# 💰 SIMULAÇÃO DE APOSTA
# =========================================
st.subheader("💰 Simulação de Aposta")

try:
    # Verifica se já há dados carregados
    if 'df' in locals() or 'df' in globals():
        # Permite ao usuário configurar os parâmetros da aposta
        st.markdown("### ⚙️ Configurações da Simulação")
        banca_inicial = st.number_input("💵 Banca inicial (R$)", min_value=10.0, value=100.0, step=10.0)
        stake = st.number_input("🎯 Valor da aposta por jogo (R$)", min_value=1.0, value=10.0, step=1.0)
        odd_minima = st.number_input("📉 Odd mínima", min_value=1.01, value=1.5, step=0.01)
        odd_maxima = st.number_input("📈 Odd máxima", min_value=1.01, value=3.5, step=0.01)

        # Filtro de odds válidas
        if all(col in df.columns for col in ['Home_Odd', 'Draw_Odd', 'Away_Odd']):
            df_filtrado = df[
                (df['Home_Odd'] >= odd_minima) & (df['Home_Odd'] <= odd_maxima) |
                (df['Draw_Odd'] >= odd_minima) & (df['Draw_Odd'] <= odd_maxima) |
                (df['Away_Odd'] >= odd_minima) & (df['Away_Odd'] <= odd_maxima)
            ]

            # Cálculo do retorno esperado
            df_filtrado["Retorno_Esperado"] = (
                df_filtrado["Pred_H"] * df_filtrado["Home_Odd"] +
                df_filtrado["Pred_D"] * df_filtrado["Draw_Odd"] +
                df_filtrado["Pred_A"] * df_filtrado["Away_Odd"]
            ) - 1

            # Mostra jogos com melhor valor esperado
            melhores_jogos = df_filtrado.sort_values("Retorno_Esperado", ascending=False).head(10)

            st.markdown("### 🏆 Melhores Oportunidades de Aposta (Value Bets)")
            st.dataframe(
                melhores_jogos[["HomeTeam", "AwayTeam", "Home_Odd", "Draw_Odd", "Away_Odd", "Retorno_Esperado"]]
                .rename(columns={
                    "HomeTeam": "Mandante",
                    "AwayTeam": "Visitante",
                    "Home_Odd": "Odd Casa",
                    "Draw_Odd": "Odd Empate",
                    "Away_Odd": "Odd Fora",
                    "Retorno_Esperado": "Valor Esperado"
                })
            )

            # Simulação da banca
            lucro_total = (melhores_jogos["Retorno_Esperado"].mean() or 0) * stake * len(melhores_jogos)
            banca_final = banca_inicial + lucro_total

            st.success(f"💰 Banca final estimada: R$ {banca_final:.2f}")
            st.info(f"📊 Lucro estimado: R$ {lucro_total:.2f}")
        else:
            st.warning("⚠️ Seu arquivo Excel precisa conter as colunas: Home_Odd, Draw_Odd e Away_Odd para simular apostas.")
    else:
        st.warning("📁 Faça upload do arquivo Excel antes de usar a simulação.")
except Exception as e:
    st.error(f"❌ Erro na simulação: {e}")


