# sports_app_auto.py
import streamlit as st
import requests
import pandas as pd
from datetime import date
import math

# ============================
# CONFIGURAÇÃO DA PÁGINA
# ============================
st.set_page_config(page_title="Analisador de Apostas", page_icon="⚽", layout="centered")
st.title("⚽ Analisador e Simulador de Apostas Esportivas")
st.write("App automatizado para buscar estatísticas, histórico e calcular probabilidades reais das partidas do dia.")

# ============================
# API KEY
# ============================
API_KEY = st.secrets.get("FOOTBALL_DATA_API_KEY", None)
API_BASE = "https://api.football-data.org/v4"
HEADERS = {"X-Auth-Token": API_KEY}

if not API_KEY:
    st.error("⚠️ Adicione sua FOOTBALL_DATA_API_KEY nos Secrets do Streamlit antes de usar.")
    st.stop()

# ============================
# FUNÇÕES DE APOIO
# ============================

def buscar_partidas(data_str, leagues):
    resultados = []
    for liga in leagues:
        url = f"{API_BASE}/competitions/{liga}/matches"
        params = {"dateFrom": data_str, "dateTo": data_str}
        r = requests.get(url, headers=HEADERS, params=params, timeout=15)
        if r.status_code == 200:
            for m in r.json().get("matches", []):
                resultados.append({
                    "Competition": liga,
                    "Date": m["utcDate"][:10],
                    "Hour": m["utcDate"][11:16],
                    "HomeTeam": m["homeTeam"]["name"],
                    "AwayTeam": m["awayTeam"]["name"],
                    "MatchID": m["id"],
                    "Status": m["status"]
                })
    return pd.DataFrame(resultados)

def buscar_h2h(home_id, away_id):
    """Busca últimos 5 confrontos diretos entre os dois times."""
    url = f"{API_BASE}/teams/{home_id}/matches"
    params = {"opponents": away_id, "limit": 5, "status": "FINISHED"}
    r = requests.get(url, headers=HEADERS, params=params, timeout=10)
    if r.status_code != 200:
        return []
    return r.json().get("matches", [])

def buscar_ultimos_jogos(team_id):
    """Busca últimos 5 jogos do time."""
    url = f"{API_BASE}/teams/{team_id}/matches"
    params = {"limit": 5, "status": "FINISHED"}
    r = requests.get(url, headers=HEADERS, params=params, timeout=10)
    if r.status_code != 200:
        return []
    return r.json().get("matches", [])

def desempenho_time(matches, team_name):
    """Retorna vitórias, empates, derrotas e saldo de gols."""
    wins = draws = losses = gf = ga = 0
    for m in matches:
        score = m.get("score", {}).get("fullTime", {})
        hg, ag = score.get("home"), score.get("away")
        if hg is None or ag is None:
            continue
        home = m["homeTeam"]["name"]
        away = m["awayTeam"]["name"]
        if team_name == home:
            gf += hg; ga += ag
            if hg > ag: wins += 1
            elif hg == ag: draws += 1
            else: losses += 1
        elif team_name == away:
            gf += ag; ga += hg
            if ag > hg: wins += 1
            elif ag == hg: draws += 1
            else: losses += 1
    jogos = wins + draws + losses
    if jogos == 0: return (0, 0, 0, 0)
    saldo = gf - ga
    return (wins/jogos, draws/jogos, losses/jogos, saldo/jogos)

def calcular_prob(row):
    """Calcula probabilidade combinando forma + H2H."""
    home = row["HomeTeam"]
    away = row["AwayTeam"]
    home_id = row["HomeID"]
    away_id = row["AwayID"]

    ult_home = buscar_ultimos_jogos(home_id)
    ult_away = buscar_ultimos_jogos(away_id)
    h2h = buscar_h2h(home_id, away_id)

    winH, drawH, lossH, saldoH = desempenho_time(ult_home, home)
    winA, drawA, lossA, saldoA = desempenho_time(ult_away, away)
    h2h_home, h2h_draw, h2h_away, _ = desempenho_time(h2h, home)

    p_home = 0.5 * winH + 0.3 * (1 - winA) + 0.2 * h2h_home
    p_away = 0.5 * winA + 0.3 * (1 - winH) + 0.2 * h2h_away
    p_draw = 1 - (p_home + p_away)
    if p_draw < 0: p_draw = 0.05
    s = p_home + p_draw + p_away
    return round(p_home/s, 2), round(p_draw/s, 2), round(p_away/s, 2)

def odds_para_probabilidade(odd):
    return 1/odd if odd and odd > 0 else None

def calcular_ev(prob, odd):
    return round(prob * odd - 1, 3) if odd else None

# ============================
# INTERFACE
# ============================

st.subheader("📅 Partidas do Dia")
data_escolhida = st.date_input("Selecione a data:", value=date.today())
data_str = data_escolhida.isoformat()

ligas = {
    "Brasileirão Série A": "BSA",
    "Premier League": "PL",
    "La Liga": "PD",
    "Bundesliga": "BL1",
    "Serie A (Itália)": "SA",
    "Ligue 1": "FL1"
}
selec = st.multiselect("Selecione as ligas:", ligas.keys(), default=["Brasileirão Série A"])

if st.button("Buscar Partidas"):
    with st.spinner("Buscando partidas e estatísticas..."):
        codigos = [ligas[l] for l in selec]
        df = buscar_partidas(data_str, codigos)
        if df.empty:
            st.warning("Nenhuma partida encontrada para essa data.")
        else:
            # buscar IDs exatos (para usar em H2H)
            team_ids = {}
            for l in codigos:
                try:
                    resp = requests.get(f"{API_BASE}/competitions/{l}/teams", headers=HEADERS, timeout=10)
                    if resp.status_code == 200:
                        for t in resp.json().get("teams", []):
                            team_ids[t["name"]] = t["id"]
                except:
                    continue
            df["HomeID"] = df["HomeTeam"].map(team_ids)
            df["AwayID"] = df["AwayTeam"].map(team_ids)

            probsH, probsD, probsA = [], [], []
            for _, r in df.iterrows():
                try:
                    pH, pD, pA = calcular_prob(r)
                except:
                    pH, pD, pA = 0.33, 0.34, 0.33
                probsH.append(pH); probsD.append(pD); probsA.append(pA)
            df["Prob_H"], df["Prob_D"], df["Prob_A"] = probsH, probsD, probsA

            st.success("✅ Partidas e probabilidades atualizadas com sucesso!")
            st.dataframe(df[["Competition", "Date", "Hour", "HomeTeam", "AwayTeam", "Prob_H", "Prob_D", "Prob_A"]])
            st.session_state["matches_df"] = df

# ============================
# SIMULADOR
# ============================
st.subheader("💸 Simulação de Aposta")
banca = st.number_input("Banca inicial (R$):", min_value=1.0, value=100.0)
stake = st.number_input("Valor por aposta (R$):", min_value=1.0, value=10.0)

if st.button("Simular Retorno"):
    if "matches_df" not in st.session_state:
        st.warning("Busque as partidas primeiro.")
    else:
        df = st.session_state["matches_df"]
        lucro = 0
        for _, r in df.iterrows():
            melhor = max([r["Prob_H"], r["Prob_D"], r["Prob_A"]])
            lucro += stake * (melhor - 0.5)  # expectativa
        st.success(f"Banca esperada: R$ {banca + lucro:.2f} (lucro esperado {lucro:.2f})")

st.caption("⚠️ Modelo usa últimos jogos e H2H como base. Resultados meramente indicativos.")
