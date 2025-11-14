
# sports_app_full.py
# Versão funcional - Analisador e Simulador de Apostas Esportivas (arquivo para upload no Streamlit)
# Coloque sua API keys em Streamlit Secrets:
# - api-football = "SUA_CHAVE_API_FOOTBALL"  (recomendado: fornece H2H, últimos jogos, odds)
# - FOOTBALL_DATA_API = "SUA_CHAVE_FOOTBALL_DATA_ORG" (opcional fallback para fixtures)
#
# Deploy: suba este arquivo no Streamlit Cloud (Upload file) e adicione as chaves em Settings -> Secrets.
# Run locally: streamlit run sports_app_full.py

import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import date, datetime
import time
import random

st.set_page_config(page_title="Analisador de Apostas", page_icon="⚽", layout="wide")
st.title("⚽ Analisador e Simulador de Apostas Esportivas")
st.write("App que busca partidas, mostra últimos jogos/H2H e simula retornos.")

# --- KEYS (via Streamlit Secrets) ---
API_FOOTBALL_KEY = st.secrets.get("api-football", "")
FOOTBALL_DATA_KEY = st.secrets.get("FOOTBALL_DATA_API", "")

# 🗝️ --- KEYS (via Streamlit Secrets) ---
API_FOOTBALL_KEY = st.secrets.get("api-football", "")
FOOTBALL_DATA_KEY = st.secrets.get("football_data_api", "")

API_FOOTBALL_BASE = "https://v3.football.api-sports.io/"
FOOTBALL_DATA_BASE = "https://api.football-data.org/v4/"

# Headers corretos
HEADERS_API_FOOTBALL = {"X-APi-Key": API_FOOTBALL_KEY}
HEADERS_FOOTBALL_DATA = {"X-Auth-Token": FOOTBALL_DATA_KEY}

# Aviso caso nenhuma API tenha sido configurada
if not API_FOOTBALL_KEY and not FOOTBALL_DATA_KEY:
    st.warning("Nenhuma API configurada. O app funcionará em modo simulado (mock).")

# --- Default leagues (IDs for api-football / codes for football-data) ---
LEAGUES = {
    "Brasileirão Série A": 71,
    "Premier League": 39,
    "La Liga": 140,
    "Serie A (Itália)": 135,
    "Bundesliga": 78,
    "Ligue 1": 61
}

# --- Helpers ---
# --- Helpers ---
def safe_get(url, params=None, headers=None, timeout=12):
    try:
        r = requests.get(url, params=params, headers=headers or {}, timeout=timeout)
        time.sleep(0.12)

        if r.status_code == 200:
            return r.json()

        return {
            "__error__": f"CODE {r.status_code}",
            "url": url,
            "params": params,
            "response_text": r.text
        }

    except Exception as e:
        return {"__error__": str(e)}

# --- Fetch fixtures (football-data preferred, else api-football) ---
def fetch_fixtures_by_league_and_date(league_id, date_iso):
    if FOOTBALL_DATA_KEY:
        url = f"{FOOTBALL_DATA_BASE}/competitions/{league_id}/matches"
        params = {"dateFrom": date_iso, "dateTo": date_iso}
        return safe_get(url, params=params, headers=HEADERS_FOOTBALL_DATA)
    elif API_FOOTBALL_KEY:
        url = f"{API_FOOTBALL_BASE}/fixtures"
        params = {"league": league_id, "season": datetime.now().year, "date": date_iso}
        return safe_get(url, params=params, headers=HEADERS_API_FOOTBALL)
    else:
        return {"response": []}

def fetch_last_matches(team_id, n=5):
    if not API_FOOTBALL_KEY:
        return []
    url = f"{API_FOOTBALL_BASE}/fixtures"
    params = {"team": team_id, "last": n}
    resp = safe_get(url, params=params, headers=HEADERS_API_FOOTBALL)
    return resp.get("response", []) if "__error__" not in resp else []

def fetch_h2h(home_id, away_id, n=5):
    if not API_FOOTBALL_KEY:
        return []
    url = f"{API_FOOTBALL_BASE}/fixtures"
    params = {"h2h": f"{home_id}-{away_id}", "last": n}
    resp = safe_get(url, params=params, headers=HEADERS_API_FOOTBALL)
    return resp.get("response", []) if "__error__" not in resp else []

# --- Fetch odds for a match ---
def fetch_odds_for_match(match_id):
    if not API_FOOTBALL_KEY:
        return None

    url = f"{API_FOOTBALL_BASE}/odds"
    params = {"fixture": match_id, "bookmaker": 1}  # Bet365
    resp = safe_get(url, params=params, headers=HEADERS_API_FOOTBALL)

    if "__error__" in resp:
        return None

    try:
        # The response structure: resp["response"][0]["bookmakers"] -> list of bookmakers
        bets = resp.get("response", [])
        if not bets:
            return None

        bookmakers = bets[0].get("bookmakers", []) if isinstance(bets[0], dict) else []
        if not bookmakers:
            return None

        markets = bookmakers[0].get("bets", []) if isinstance(bookmakers[0], dict) else []
        for m in markets:
            name = m.get("name", "") if isinstance(m, dict) else ""
            # try to catch typical "Match Winner" market names (english/pt)
            if name in ("Match Winner", "Vencedor da Partida", "1X2", "Winner"):
                values = m.get("values", []) or []
                # safe extraction of odds (some entries may be missing)
                try:
                    home = float(values[0].get("odd")) if len(values) > 0 and values[0].get("odd") is not None else None
                    draw = float(values[1].get("odd")) if len(values) > 1 and values[1].get("odd") is not None else None
                    away = float(values[2].get("odd")) if len(values) > 2 and values[2].get("odd") is not None else None
                except Exception:
                    home = draw = away = None

                return home, draw, away

    except Exception:
        return None

    return None


def odds_to_probs_decimal(home, draw, away):
    try:
        inv = np.array([1.0 / home, 1.0 / draw, 1.0 / away])
        inv_sum = inv.sum()
        probs = inv / inv_sum
        return float(probs[0]), float(probs[1]), float(probs[2])
    except Exception:
        # fallback probabilities (evenly distributed)
        return 0.33, 0.34, 0.33


def model_probs_from_form(home_matches, away_matches):
    # compute points-per-match metric from a list of matches
    def ppm(matches):
        pts = 0
        games = 0
        for m in matches:
            score = m.get("score", {}) or m.get("goals", {}) or {}
            try:
                # try to read fulltime dict first
                if isinstance(score.get("fulltime", {}), dict):
                    h = score.get("fulltime", {}).get("home")
                    a = score.get("fulltime", {}).get("away")
                else:
                    h = score.get("home")
                    a = score.get("away")
            except Exception:
                h = None
                a = None

            if h is None or a is None:
                continue

            games += 1
            if h > a:
                pts += 3
            elif h == a:
                pts += 1

def model_probs_from_form(home_matches, away_matches):

    def ppm(matches):
        pts = 0
        games = 0

        for m in matches:
            score = m.get("score") or m.get("goals") or {}

            try:
                # tenta forma nova
                if isinstance(score.get("fulltime"), dict):
                    h = score["fulltime"].get("home")
                    a = score["fulltime"].get("away")
                else:
                    # forma antiga
                    h = score.get("home")
                    a = score.get("away")
            except:
                h = None
                a = None

            if h is None or a is None:
                continue

            games += 1
            if h > a:
                pts += 3
            elif h == a:
                pts += 1

        return pts / games if games else 1.0

    # calcula ppm
    ppm_h = ppm(home_matches)
    ppm_a = ppm(away_matches)

    total = ppm_h + ppm_a if (ppm_h + ppm_a) != 0 else 1.0

    ph = ppm_h / total
    pa = ppm_a / total
    pd = max(0.15, 1 - (ph + pa))

    return round(ph, 2), round(pd, 2), round(pa, 2)        return (pts / games) if games else 1.0

    ppm_h = ppm(home_matches)
    ppm_a = ppm(away_matches)

    total = ppm_h + ppm_a if (ppm_h + ppm_a) != 0 else 1.0
    ph = ppm_h / total
    pa = ppm_a / total
    pd = max(0.15, 1 - (ph + pa))

    return round(ph, 2), round(pd, 2), round(pa, 2)

            if h is None or a is None:
                continue

            games += 1
            if h > a:
                pts += 3
            elif h == a:
                pts += 1

        return pts / games if games else 1.0

    ppm_h = ppm(home_matches)
    ppm_a = ppm(away_matches)



# --- Fetch fixtures ---
    fixtures = resp.get("matches") or resp.get("response") or []

    for f in fixtures:
        fix = f.get("fixture") or f.get("id") or f.get("fixture") or f.get("id") if isinstance(f, dict) else None
        if not fix or fix.get("utcDate") or fix.get("utcDate") or fix.get("utcDate") == "":
            home = f.get("teams", {}).get("homeTeam") or {}
            away = f.get("teams", {}).get("awayTeam") or {}

        home_name = teams.get("home", {}).get("name") if isinstance(teams, dict) and teams.get("home") else f.get("homeTeam", {}).get("name")
        away_name = teams.get("away", {}).get("name") if isinstance(teams, dict) and teams.get("away") else f.get("awayTeam", {}).get("name")

        home_id = teams.get("home", {}).get("id") if isinstance(teams, dict) and teams.get("home") else f.get("homeTeam", {}).get("id")
        away_id = teams.get("away", {}).get("id") if isinstance(teams, dict) and teams.get("away") else f.get("awayTeam", {}).get("id")

        out.append({
            "MatchID": int(match_id) if match_id else None,
            "League": league_name,
            "Date": date_iso,
            "Hour": hour_iso,
            "Home": home_name,
            "Away": away_name,
            "HomeID": home_id,
            "AwayID": away_id
        })

    return pd.DataFrame(out)


# --- UI Inputs ---
st.sidebar.header("Configuração")
data_sel = st.sidebar.date_input("Data das partidas", value=datetime.today())

leagues_sel = st.sidebar.multiselect("Ligas", options=list(LEAGUES.keys()), default=["Brasileirão Série A"])

mode = st.sidebar.radio("Modo de análise", ["Odds quando disponível", "Modelo (sem odds)"])
incl_h2h = st.sidebar.checkbox("Incluir H2H nos ajustes", value=True)
last_n = st.sidebar.number_input("Últimos N jogos (por time)", min_value=1, max_value=12, value=5)

btn_fetch = st.sidebar.button("Buscar partidas")

if "matches_df" not in st.session_state:
    st.session_state["matches_df"] = pd.DataFrame()

if btn_fetch:
    st.spinner("Buscando partidas...")

    df_matches = get_matches_dataframe(leagues_sel, data_sel)

    if df_matches.empty:
        st.warning("Nenhuma partida encontrada para a data/ligas selecionadas.")
        st.session_state["matches_df"] = pd.DataFrame()
    else:
        st.session_state["matches_df"] = df_matches
        st.success("Partidas carregadas e probabilidades calculadas.")
            # --- Display main table ---
df_show = st.session_state.get("matches_df", pd.DataFrame())

if not df_show.empty:
    st.dataframe(
        df_show[["MatchID", "League", "Date", "Hour", "Home", "Away", "home_odd", "draw_odd", "away_odd", "Prob_H", "Prob_D", "Prob_A"]],
        use_container_width=True
    )

    st.subheader("Últimos 5 jogos e H2H detalhado (por partida)")

    for _, row in df_show.iterrows():
        mid = row.get("MatchID")
        home_name = row.get("Home")
        away_name = row.get("Away")
        home_id = row.get("HomeID")
        away_id = row.get("AwayID")

        st.markdown(f"### {home_name} vs {away_name}")

        with st.expander(f"Últimos {last_n} jogos - {home_name} (casa)"):
            if API_FOOTBALL_KEY:
                last_home = fetch_last_matches(home_id, n=last_n)
                if last_home:
                    out = []
                    for m in last_home[:last_n]:
                        fix = m.get("fixture", {})
                        teams = m.get("teams", {})
                        home_n = teams.get("home", {}).get("name") if teams else None
                        away_n = teams.get("away", {}).get("name") if teams else None
                        score = m.get("score") or {}

                        h = score.get("fulltime", {}).get("home") if isinstance(score.get("fulltime", {}), dict) else score.get("home")
                        a = score.get("fulltime", {}).get("away") if isinstance(score.get("fulltime", {}), dict) else score.get("away")

                        out.append({
                            "Date": fix.get("date"),
                            "Opponent": away_n if home_n == home_name else home_n,
                            "Score": f"{h} - {a}"
                        })

                    st.dataframe(pd.DataFrame(out))
                else:
                    st.info("Últimos jogos não disponíveis via API para este time.")
            else:
                st.info("ID do time ou API não disponível para buscar últimos jogos.")

        with st.expander(f"Últimos {last_n} jogos - {away_name} (fora)"):
            if away_id and API_FOOTBALL_KEY:
                last_away = fetch_last_matches(away_id, n=last_n)
                if last_away:
                    out = []
                    for m in last_away[:last_n]:
                        fix = m.get("fixture", {})
                        teams = m.get("teams", {})
                        home_n = teams.get("home", {}).get("name") if teams else None
                        away_n = teams.get("away", {}).get("name") if teams else None
                        score = m.get("score") or {}

                        h = score.get("fulltime", {}).get("home") if isinstance(score.get("fulltime", {}), dict) else score.get("home")
                        a = score.get("fulltime", {}).get("away") if isinstance(score.get("fulltime", {}), dict) else score.get("away")

                        out.append({
                            "Date": fix.get("date"),
                            "Opponent": home_n if home_n != away_name else away_n,
                            "Score": f"{h} - {a}"
                        })

                    st.dataframe(pd.DataFrame(out))
                else:
                    st.info("Últimos jogos não disponíveis via API para este time.")
            else:
                st.info("ID do time ou API não disponível para buscar últimos jogos.")

        with st.expander("Confrontos Diretos (H2H)"):
            if mid and API_FOOTBALL_KEY:
                h2h = fetch_h2h(mid)
                if h2h:
                    st.dataframe(h2h)
                else:
                    st.info("Nenhum confronto direto encontrado.")
            else:
                st.info("API ou MatchID não disponível para buscar H2H.")
                if h2h:
                    out = []
                    for g in h2h[:last_n]:
                        fix = g.get("fixture") or {}
                        teams = g.get("teams") or {}
                        score = g.get("score") or {}
                        ft = score.get("fulltime", {}) if isinstance(score.get("fulltime", {}), dict) else {}
                        out.append({"Date": fix.get("date"), "Home": teams.get("home", {}).get("name"), "Away": teams.get("away", {}).get("name"), "Score": f"{ft.get('home','-')} - {ft.get('away','-')}"})
                    st.dataframe(pd.DataFrame(out))
                else:
                    st.info("H2H não disponível para este confronto.")
            else:
                st.info("IDs de clubes ou API não configurada para H2H.")

# --- Simulador ---
st.header("💸 Simulação de Aposta")
banca = st.number_input("Banca inicial (R$):", value=100.0, min_value=1.0, step=1.0, format="%.2f")
stake = st.number_input("Stake por aposta (R$):", value=10.0, min_value=0.1, step=0.5, format="%.2f")
if st.button("Simular Retorno"):
    df_sim = st.session_state.get("matches_df", pd.DataFrame())
    if df_sim.empty:
        st.warning("Busque partidas primeiro.")
    else:
        total_profit = 0.0; bets = []
        for _, r in df_sim.iterrows():
            ph = float(r.get("Prob_Final_H", r.get("Prob_H",0.33)))
            pd_ = float(r.get("Prob_Final_D", r.get("Prob_D",0.34)))
            pa = float(r.get("Prob_Final_A", r.get("Prob_A",0.33)))
            # pick highest
            pick = "H" if ph>=pd_ and ph>=pa else ("D" if pd_>=pa else "A")
            prob_model = ph if pick=="H" else (pd_ if pick=="D" else pa)
            # implied odd
            odd = round(max(1.01, 1.0/max(1e-6, prob_model)), 2)
            win = random.random() < prob_model
            profit = (odd-1.0)*stake if win else -stake
            total_profit += profit
            bets.append({"Match": f"{r.get('Home')} x {r.get('Away')}", "Pick": pick, "Odd": odd, "Prob": round(prob_model,2), "Profit": round(profit,2)})
        st.success(f"Lucro estimado total: R$ {round(total_profit,2)}") 
        st.dataframe(pd.DataFrame(bets), use_container_width=True)

st.markdown("---")
st.caption("Observação: este é um protótipo com modelo simples. Ajuste pesos e parsing de odds para produção.")
