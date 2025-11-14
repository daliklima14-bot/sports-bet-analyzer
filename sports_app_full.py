
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

API_FOOTBALL_BASE = "https://v3.football.api-sports.io"
FOOTBALL_DATA_BASE = "https://api.football-data.org/v4"

HEADERS_API_FOOTBALL = {"x-apisports-key": API_FOOTBALL_KEY} if API_FOOTBALL_KEY else {}
HEADERS_FOOTBALL_DATA = {"X-Auth-Token": FOOTBALL_DATA_KEY} if FOOTBALL_DATA_KEY else {}

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

def fetch_odds_for_match(match_id):
    if not API_FOOTBALL_KEY:
        return None
    url = f"{API_FOOTBALL_BASE}/odds"
    params = {"fixture": match_id}
    resp = safe_get(url, params=params, headers=HEADERS_API_FOOTBALL)
    if "__error__" in resp:
        return None
    return resp.get("response", [])

def odds_to_probs_decimal(home, draw, away):
    try:
        inv = np.array([1.0/home, 1.0/draw, 1.0/away])
        probs = inv / inv.sum()
        return float(probs[0]), float(probs[1]), float(probs[2])
    except Exception:
        return 0.33, 0.34, 0.33

def model_probs_from_form(home_matches, away_matches):
    def ppm(matches):
        pts = 0; games = 0
        for m in matches:
            score = m.get("score", {}) or m.get("goals", {}) or {}
            # defensive extraction
            try:
                h = None; a = None
                if isinstance(score.get("fulltime", {}), dict):
                    h = score.get("fulltime", {}).get("home"); a = score.get("fulltime", {}).get("away")
                else:
                    h = score.get("home"); a = score.get("away")
            except Exception:
                h = a = None
            if h is None or a is None: continue
            games += 1
            if h > a: pts += 3
            elif h == a: pts += 1
        return (pts/games) if games else 1.0
    ppm_h = ppm(home_matches); ppm_a = ppm(away_matches)
    total = max(0.0001, ppm_h + ppm_a)
    ph = ppm_h/total; pa = ppm_a/total
    pd = max(0.05, 1 - (ph + pa))
    s = ph + pd + pa
    return round(ph/s,2), round(pd/s,2), round(pa/s,2)

# --- Build dataframe of matches ---
def get_matches_dataframe(selected_leagues, date_obj):
    results = []
    date_iso = date_obj.isoformat()
    for league_name in selected_leagues:
        league_id = LEAGUES.get(league_name)
        if not league_id:
            continue
        resp = fetch_fixtures_by_league_and_date(league_id, date_iso)
        if "__error__" in resp:
            st.warning(f"Erro ao buscar fixtures {league_name}: {resp['__error__']}")
            continue
        fixtures = resp.get("matches") or resp.get("response") or []
        for f in fixtures:
            fix = f.get("fixture") or f
            match_id = fix.get("id") or f.get("id") or (f.get("fixture") or {}).get("id") if isinstance(f, dict) else None
            utc = fix.get("utcDate") or fix.get("date") or f.get("utcDate") or ""
            hour = utc[11:16] if utc else ""
            # teams parsing defensive
            teams = f.get("teams") or f.get("homeTeam") or {}
            home = teams.get("home", {}).get("name") if isinstance(teams, dict) and teams.get("home") else (f.get("homeTeam") or {}).get("name") if f.get("homeTeam") else ""
            away = teams.get("away", {}).get("name") if isinstance(teams, dict) and teams.get("away") else (f.get("awayTeam") or {}).get("name") if f.get("awayTeam") else ""
            home_id = (teams.get("home", {}).get("id") if isinstance(teams, dict) and teams.get("home") else (f.get("homeTeam") or {}).get("id")) if isinstance(f, dict) else None
            away_id = (teams.get("away", {}).get("id") if isinstance(teams, dict) and teams.get("away") else (f.get("awayTeam") or {}).get("id")) if isinstance(f, dict) else None
            results.append({"MatchID": int(match_id) if match_id else None, "League": league_name, "Date": date_iso, "Hour": hour, "Home": home, "Away": away, "HomeID": home_id, "AwayID": away_id})
    return pd.DataFrame(results)

# --- UI Inputs ---
st.sidebar.header("Configuração")
data_sel = st.sidebar.date_input("Data das partidas", value=date.today())
leagues_sel = st.sidebar.multiselect("Ligas", options=list(LEAGUES.keys()), default=["Brasileirão Série A"])
mode = st.sidebar.radio("Modo de análise", ["Odds quando disponível", "Modelo (sem odds)"])
include_h2h = st.sidebar.checkbox("Incluir H2H nos ajustes", value=True)
last_n = st.sidebar.number_input("Últimos N jogos (por time)", min_value=1, max_value=10, value=5)
btn_fetch = st.sidebar.button("Buscar partidas")

if "matches_df" not in st.session_state:
    st.session_state["matches_df"] = pd.DataFrame()

if btn_fetch:
    with st.spinner("Buscando partidas..."):
        df_matches = get_matches_dataframe(leagues_sel, data_sel)
        if df_matches.empty:
            st.warning("Nenhuma partida encontrada para a data/ligas selecionadas.")
            st.session_state["matches_df"] = pd.DataFrame()
        else:
            df_matches["home_odd"] = np.nan; df_matches["draw_odd"] = np.nan; df_matches["away_odd"] = np.nan
            # fetch odds when available and mode requires
            for i, row in df_matches.iterrows():
                mid = row.get("MatchID")
                if mode == "Odds quando disponível" and mid and API_FOOTBALL_KEY:
                    odds = fetch_odds_for_match(int(mid))
                    if odds:
                        # provider parsing varies; keep raw
                        df_matches.at[i, "home_odd"] = np.nan
                        df_matches.at[i, "draw_odd"] = np.nan
                        df_matches.at[i, "away_odd"] = np.nan
            # compute base probs (model/fallback)
            if mode == "Odds quando disponível" and df_matches[ ["home_odd","draw_odd","away_odd"] ].notna().any(axis=None):
                probs = []
                for _, r in df_matches.iterrows():
                    h,d,a = r.get("home_odd"), r.get("draw_odd"), r.get("away_odd")
                    if pd.notna(h) and pd.notna(d) and pd.notna(a) and h>0 and d>0 and a>0:
                        probs.append(odds_to_probs_decimal(h,d,a))
                    else:
                        probs.append(model_probs_from_form([], []))
                df_matches["Prob_H"], df_matches["Prob_D"], df_matches["Prob_A"] = zip(*probs)
            else:
                gens = [model_probs_from_form([], []) for _ in range(len(df_matches))]
                df_matches["Prob_H"], df_matches["Prob_D"], df_matches["Prob_A"] = zip(*gens)
            # combine with H2H/form
            df_matches = combine_probabilities(df_matches, use_h2h=include_h2h, last_n=int(last_n))
            st.session_state["matches_df"] = df_matches
            st.success("Partidas carregadas e probabilidades calculadas.")

# Display main table
df_show = st.session_state.get("matches_df", pd.DataFrame())
if not df_show.empty:
    display_df = df_show[["MatchID","League","Date","Hour","Home","Away","home_odd","draw_odd","away_odd","Prob_H","Prob_D","Prob_A","Prob_Final_H","Prob_Final_D","Prob_Final_A"]].rename(columns={"home_odd":"Odd_H","draw_odd":"Odd_D","away_odd":"Odd_A","Prob_H":"Base_H","Prob_D":"Base_D","Prob_A":"Base_A","Prob_Final_H":"Final_H","Prob_Final_D":"Final_D","Prob_Final_A":"Final_A"})
    st.dataframe(display_df, use_container_width=True)
    st.subheader("📊 Últimos 5 jogos e H2H (detalhado por partida)")
    for _, row in df_show.iterrows():
        home = row.get("Home"); away = row.get("Away"); hid = row.get("HomeID"); aid = row.get("AwayID")
        st.markdown(f"### ⚔️ {home} x {away}")
        with st.expander(f"Últimos {last_n} jogos - {home}"):
            if hid and API_FOOTBALL_KEY:
                last_home = fetch_last_matches(hid, n=last_n)
                if last_home:
                    out = []
                    for g in last_home[:last_n]:
                        fix = g.get("fixture") or {}
                        date_s = fix.get("date") or fix.get("utcDate") or None
                        teams = g.get("teams") or {}
                        home_name = teams.get("home", {}).get("name") if teams else None
                        away_name = teams.get("away", {}).get("name") if teams else None
                        score = g.get("score") or {}
                        ft = score.get("fulltime", {}) if isinstance(score.get("fulltime", {}), dict) else {}
                        out.append({"Date": date_s, "Opponent": away_name if home_name==home else home_name, "Score": f"{ft.get('home','-')} - {ft.get('away','-')}"})
                    st.dataframe(pd.DataFrame(out))
                else:
                    st.info("Últimos jogos não disponíveis via API para este time.")
            else:
                st.info("ID do time ou API não disponível para buscar últimos jogos.")
        with st.expander(f"Últimos {last_n} jogos - {away}"):
            if aid and API_FOOTBALL_KEY:
                last_away = fetch_last_matches(aid, n=last_n)
                if last_away:
                    out = []
                    for g in last_away[:last_n]:
                        fix = g.get("fixture") or {}
                        date_s = fix.get("date") or fix.get("utcDate") or None
                        teams = g.get("teams") or {}
                        home_name = teams.get("home", {}).get("name") if teams else None
                        away_name = teams.get("away", {}).get("name") if teams else None
                        score = g.get("score") or {}
                        ft = score.get("fulltime", {}) if isinstance(score.get("fulltime", {}), dict) else {}
                        out.append({"Date": date_s, "Opponent": home_name if away_name==away else away_name, "Score": f"{ft.get('home','-')} - {ft.get('away','-')}"})
                    st.dataframe(pd.DataFrame(out))
                else:
                    st.info("Últimos jogos não disponíveis via API para este time.")
            else:
                st.info("ID do time ou API não disponível para buscar últimos jogos.")
        with st.expander("Confrontos Diretos (H2H)"):
            if hid and aid and API_FOOTBALL_KEY:
                h2h = fetch_h2h(hid, aid, n=last_n)
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
