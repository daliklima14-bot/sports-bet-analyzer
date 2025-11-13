# sports_app_auto.py
# App completo: busca partidas, H2H, últimos 5 jogos, odds, probabilidades e simulação
import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import date, datetime
import time

# -------------------------
# CONFIGURAÇÕES INICIAIS
# -------------------------
st.set_page_config(page_title="Analisador de Apostas - Completo", page_icon="⚽", layout="wide")
st.title("⚽ Analisador e Simulador de Apostas Esportivas")
st.write("Busca automática: partidas, últimos 5 jogos, H2H, odds (quando disponíveis) e probabilidades ajustadas.")

# -------------------------
# API KEY (via Streamlit Secrets)
# -------------------------
# Certifique-se de ter no Streamlit Secrets:
# api-football = "SUA_CHAVE_AQUI"
API_KEY = st.secrets.get("api-football", "")
if not API_KEY:
    st.error("⚠️ Adicione sua chave da API-Football em Settings → Secrets com a chave 'api-football'.")
    st.stop()

API_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

# -------------------------
# MAPA DE LIGAS (nome -> id)
# Ajuste se quiser adicionar/remover ligas.
# -------------------------
LEAGUES = {
    "Brasileirão Série A": 71,
    "Premier League": 39,
    "La Liga": 140,
    "Serie A (Itália)": 135,
    "Bundesliga": 78,
    "Ligue 1": 61
}

# -------------------------
# UTIL: chamadas HTTP com tratamento simples
# -------------------------
def safe_get(url, params=None, headers=None, timeout=12):
    try:
        r = requests.get(url, params=params, headers=headers or HEADERS, timeout=timeout)
        # respeitar pausa leve
        time.sleep(0.12)
        if r.status_code == 200:
            return r.json()
        else:
            return {"_error_": f"{r.status_code} - {r.text}"}
    except Exception as e:
        return {"_error_": str(e)}

# -------------------------
# BUSCAR PARTIDAS (fixtures) por liga e data
# -------------------------
def fetch_fixtures_by_league_and_date(league_id: int, date_iso: str):
    url = f"{API_URL}/fixtures"
    params = {"league": league_id, "season": datetime.now().year, "date": date_iso}
    return safe_get(url, params=params)

# -------------------------
# BUSCAR DETALHES DO JOGO (match)
# -------------------------
def fetch_match_details(match_id: int):
    url = f"{API_URL}/fixtures"
    params = {"id": match_id}
    return safe_get(url, params=params)

# -------------------------
# BUSCAR ODDS (se disponíveis)
# endpoint: /odds or /fixtures/{id}/odds may vary by plan; try fixtures with bookmakers
# -------------------------
def fetch_odds_for_match(match_id: int):
    # try the odds endpoint
    url = f"{API_URL}/odds"
    params = {"fixture": match_id}
    resp = safe_get(url, params=params)
    if "_error_" in resp:
        # fallback: try to see if match details contain bookmakers / odds
        details = fetch_match_details(match_id)
        if "_error_" in details:
            return None
        # attempt to parse possible odds locations defensively
        responses = details.get("response", [])
        if responses:
            match_obj = responses[0]
            # sometimes odds are inside bookmakers
            bookmakers = match_obj.get("bookmakers") or match_obj.get("odds") or []
            if bookmakers:
                # try to get first bookmaker 1X2
                for bm in bookmakers:
                    # normalize common shapes
                    bets = bm.get("bets") or bm.get("markets") or []
                    for b in bets:
                        values = b.get("values") or b.get("odds") or []
                        if len(values) >= 3:
                            try:
                                h = float(values[0].get("odd") or values[0].get("value") or values[0].get("price"))
                                d = float(values[1].get("odd") or values[1].get("value") or values[1].get("price"))
                                a = float(values[2].get("odd") or values[2].get("value") or values[2].get("price"))
                                return {"home_odd": h, "draw_odd": d, "away_odd": a}
                            except:
                                continue
    else:
        # parse resp format
        data = resp.get("response", [])
        if data:
            # attempt to get odds in common format
            first = data[0]
            # There are many formats; try 1X2 common shape
            if isinstance(first, dict):
                # find keys with 'bookmakers' or 'bets'
                for key in ("bookmakers", "markets", "bets"):
                    if key in first and first[key]:
                        for bm in first[key]:
                            vals = bm.get("bets") or bm.get("values") or bm.get("odds") or []
                            if vals and len(vals) >= 3:
                                try:
                                    # values might be dicts
                                    v0 = vals[0]
                                    v1 = vals[1]
                                    v2 = vals[2]
                                    h = float(v0.get("odd") or v0.get("value") or v0.get("price") or v0)
                                    d = float(v1.get("odd") or v1.get("value") or v1.get("price") or v1)
                                    a = float(v2.get("odd") or v2.get("value") or v2.get("price") or v2)
                                    return {"home_odd": h, "draw_odd": d, "away_odd": a}
                                except:
                                    continue
    return None

# -------------------------
# BUSCAR ÚLTIMOS N JOGOS DO TIME
# endpoint: /fixtures?team={team_id}&status=FINISHED&limit=n
# -------------------------
def fetch_last_matches(team_id: int, n: int = 5):
    if not team_id:
        return []
    url = f"{API_URL}/fixtures"
    params = {"team": team_id, "last": n, "status": "FT"}  # 'last' often supported
    resp = safe_get(url, params=params)
    if "_error_" in resp:
        return []
    return resp.get("response", [])

# -------------------------
# BUSCAR H2H entre dois times (últimos n encontros)
# endpoint: /fixtures?h2h={teamA}-{teamB}&last=n
# -------------------------
def fetch_h2h(home_id: int, away_id: int, n: int = 5):
    if not home_id or not away_id:
        return []
    url = f"{API_URL}/fixtures"
    params = {"h2h": f"{home_id}-{away_id}", "last": n}
    resp = safe_get(url, params=params)
    if "_error_" in resp:
        return []
    return resp.get("response", [])

# -------------------------
# CONVERSÕES e CÁLCULOS
# -------------------------
def odds_to_probs_decimal(home, draw, away):
    try:
        inv = np.array([1.0/home, 1.0/draw, 1.0/away])
        probs = inv / inv.sum()
        return float(probs[0]), float(probs[1]), float(probs[2])
    except Exception:
        return None, None, None

def model_probs_from_form(home_matches, away_matches):
    # Simple form model: points per game normalized -> converts to H/D/A proxy
    def ppm(matches, team_id):
        pts = 0
        games = 0
        for m in matches:
            # score
            ft = m.get("score", {}).get("fulltime") or m.get("score", {}).get("fullTime") or {}
            hgo = ft.get("home")
            ago = ft.get("away")
            if hgo is None or ago is None:
                continue
            games += 1
            if team_id == m.get("teams", {}).get("home", {}).get("id") or team_id == m.get("homeTeam", {}).get("id"):
                # home team in this match is the perspective
                # but structure may vary; we attempt both shapes
                # determine winner roughly:
                if hgo > ago:
                    pts += 3
                elif hgo == ago:
                    pts += 1
                else:
                    pts += 0
            else:
                # away perspective
                if ago > hgo:
                    pts += 3
                elif ago == hgo:
                    pts += 1
                else:
                    pts += 0
        if games == 0:
            return 1.0
        return pts / games  # points per game

    # choose ids if present
    hid = None
    aid = None
    if home_matches:
        # try to get team id from first match
        m0 = home_matches[0]
        hid = m0.get("teams", {}).get("home", {}).get("id") or m0.get("homeTeam", {}).get("id")
    if away_matches:
        m0 = away_matches[0]
        aid = m0.get("teams", {}).get("home", {}).get("id") or m0.get("homeTeam", {}).get("id")

    ppm_h = ppm(home_matches, hid) if hid else 1.0
    ppm_a = ppm(away_matches, aid) if aid else 1.0

    # create relative probabilities
    total = ppm_h + ppm_a
    ph = ppm_h / total
    pa = ppm_a / total
    # low draw baseline
    pd = max(0.05, 1 - (ph + pa))
    # normalize
    s = ph + pd + pa
    return round(ph/s, 2), round(pd/s, 2), round(pa/s, 2)

# -------------------------
# FUNÇÃO PRINCIPAL: buscar partidas e gerar df
# -------------------------
def get_matches_dataframe(selected_leagues, date_obj: date):
    results = []
    date_iso = date_obj.isoformat()
    for league_name in selected_leagues:
        league_id = LEAGUES.get(league_name, None)
        if league_id is None:
            continue
        resp = fetch_fixtures_by_league_and_date(league_id, date_iso)
        if "_error_" in resp:
            st.warning(f"Erro ao buscar fixtures {league_name}: {resp['_error_']}")
            continue
        fixtures = resp.get("response", [])
        for f in fixtures:
            fix = f.get("fixture") or f
            match_id = fix.get("id") or f.get("id")
            utc = fix.get("date") or fix.get("utcDate") or f.get("utcDate", "")
            hour = ""
            if utc:
                try:
                    hour = utc[11:16]
                except:
                    hour = ""
            league = f.get("league", {}).get("name") or league_name
            teams = f.get("teams") or {}
            home = teams.get("home", {}).get("name") if teams else f.get("homeTeam", {}).get("name") if f.get("homeTeam") else ""
            away = teams.get("away", {}).get("name") if teams else f.get("awayTeam", {}).get("name") if f.get("awayTeam") else ""
            home_id = teams.get("home", {}).get("id") if teams else f.get("homeTeam", {}).get("id") if f.get("homeTeam") else None
            away_id = teams.get("away", {}).get("id") if teams else f.get("awayTeam", {}).get("id") if f.get("awayTeam") else None

            results.append({
                "MatchID": int(match_id) if match_id else None,
                "League": league,
                "Date": date_iso,
                "Hour": hour,
                "Home": home,
                "Away": away,
                "HomeID": home_id,
                "AwayID": away_id
            })
    df = pd.DataFrame(results)
    return df

# -------------------------
# AJUSTE FINAL DE PROBABILIDADES (combina base/form/h2h)
# -------------------------
def combine_probabilities(df, use_h2h=True, last_n=5, weights=(0.6, 0.3, 0.1)):
    # weights: (base_from_odds, form, h2h)
    if df.empty:
        return df
    df = df.copy()
    w_base, w_form, w_h2h = weights
    # ensure base probs exist
    if not all(c in df.columns for c in ("Prob_H", "Prob_D", "Prob_A")):
        # fallback model from form
        df["Prob_H"], df["Prob_D"], df["Prob_A"] = zip(*[model_probs_from_form([], []) for _ in range(len(df))])

    combined = []
    for _, r in df.iterrows():
        # fetch last matches
        hid = r.get("HomeID")
        aid = r.get("AwayID")
        home_matches = fetch_last_matches(hid, n=last_n)
        away_matches = fetch_last_matches(aid, n=last_n)
        # compute form probabilities
        ph_form, pd_form, pa_form = model_probs_from_form(home_matches, away_matches)
        # compute h2h if enabled
        if use_h2h and hid and aid:
            h2h_matches = fetch_h2h(hid, aid, n=last_n)
            # simple h2h factor: fraction of home wins among h2h matches
            if h2h_matches:
                hw = 0; dw = 0; aw = 0; total = 0
                for m in h2h_matches:
                    score = m.get("score", {}).get("fulltime") or m.get("score", {}).get("fullTime") or {}
                    hgo = score.get("home"); ago = score.get("away")
                    if hgo is None or ago is None:
                        continue
                    total += 1
                    if hgo > ago:
                        hw += 1
                    elif hgo < ago:
                        aw += 1
                    else:
                        dw += 1
                if total > 0:
                    ph_h2h = hw/total
                    pd_h2h = dw/total
                    pa_h2h = aw/total
                else:
                    ph_h2h = pd_h2h = pa_h2h = 1/3
            else:
                ph_h2h = pd_h2h = pa_h2h = 1/3
        else:
            ph_h2h = pd_h2h = pa_h2h = 1/3

        # get base probs (from odds if present)
        base_h = float(r.get("Prob_H", 0.33))
        base_d = float(r.get("Prob_D", 0.34))
        base_a = float(r.get("Prob_A", 0.33))

        # combine weighted
        ch = w_base * base_h + w_form * ph_form + w_h2h * ph_h2h
        cd = w_base * base_d + w_form * pd_form + w_h2h * pd_h2h
        ca = w_base * base_a + w_form * pa_form + w_h2h * pa_h2h
        s = ch + cd + ca
        if s <= 0:
            ch, cd, ca = 0.34, 0.32, 0.34
        else:
            ch /= s; cd /= s; ca /= s
        combined.append((round(ch, 2), round(cd, 2), round(ca, 2)))

    df["Prob_Final_H"], df["Prob_Final_D"], df["Prob_Final_A"] = zip(*combined)
    return df

# -------------------------
# UI - inputs
# -------------------------
st.sidebar.header("Configuração")
data_sel = st.sidebar.date_input("Data das partidas", value=date.today())
leagues_sel = st.sidebar.multiselect("Ligas", options=list(LEAGUES.keys()), default=["Brasileirão Série A"])
mode = st.sidebar.radio("Modo de análise", ["Odds quando disponível", "Modelo (sem odds)"])
include_h2h = st.sidebar.checkbox("Incluir H2H nos ajustes", value=True)
last_n = st.sidebar.number_input("Últimos N jogos (por time)", min_value=1, max_value=10, value=5)
btn_fetch = st.sidebar.button("Buscar partidas")

# session store
if "matches_df" not in st.session_state:
    st.session_state["matches_df"] = pd.DataFrame()

# -------------------------
# Botão buscar -> carrega partidas e calcula probabilidades iniciais
# -------------------------
if btn_fetch:
    with st.spinner("Buscando partidas..."):
        df_matches = get_matches_dataframe(leagues_sel, data_sel)
        if df_matches.empty:
            st.warning("Nenhuma partida encontrada para a data/ligas selecionadas.")
            st.session_state["matches_df"] = pd.DataFrame()
        else:
            # tentar buscar odds por partida (quando modo selec indica)
            df_matches["home_odd"] = np.nan
            df_matches["draw_odd"] = np.nan
            df_matches["away_odd"] = np.nan
            for i, row in df_matches.iterrows():
                mid = row.get("MatchID")
                if mode == "Odds quando disponível" and mid:
                    try:
                        odds = fetch_odds_for_match(int(mid))
                        if odds:
                            df_matches.at[i, "home_odd"] = odds.get("home_odd")
                            df_matches.at[i, "draw_odd"] = odds.get("draw_odd")
                            df_matches.at[i, "away_odd"] = odds.get("away_odd")
                    except Exception:
                        pass

            # calcular probabilidades base a partir de odds (quando possiveis)
            if df_matches[["home_odd", "draw_odd", "away_odd"]].notna().any(axis=None):
                # odds -> probs
                probs = []
                for _, r in df_matches.iterrows():
                    h, d, a = r.get("home_odd"), r.get("draw_odd"), r.get("away_odd")
                    if pd.notna(h) and pd.notna(d) and pd.notna(a) and h > 0 and d > 0 and a > 0:
                        ph, pd_, pa = odds_to_probs_decimal(h, d, a)
                    else:
                        # fallback model
                        ph, pd_, pa = model_probs_from_form([], [])
                    probs.append((ph, pd_, pa))
                df_matches["Prob_H"], df_matches["Prob_D"], df_matches["Prob_A"] = zip(*probs)
            else:
                # fallback model
                df_matches = mock_df := df_matches.copy()
                df_matches = pd.DataFrame(df_matches)
                df_matches = df_matches.reset_index(drop=True)
                # generate model probs per row
                gens = [model_probs_from_form([], []) for _ in range(len(df_matches))]
                df_matches["Prob_H"], df_matches["Prob_D"], df_matches["Prob_A"] = zip(*gens)

            # combinar com form e h2h
            df_matches = combine_probabilities(df_matches, use_h2h=include_h2h, last_n=int(last_n))
            st.session_state["matches_df"] = df_matches
            st.success("Partidas carregadas e probabilidades calculadas.")

# -------------------------
# Exibir tabela principal
# -------------------------
df_show = st.session_state.get("matches_df", pd.DataFrame())
if not df_show.empty:
    display_df = df_show[[
        "MatchID","League","Date","Hour","Home","Away",
        "home_odd","draw_odd","away_odd",
        "Prob_H","Prob_D","Prob_A","Prob_Final_H","Prob_Final_D","Prob_Final_A"
    ]].rename(columns={
        "home_odd":"Odd_H","draw_odd":"Odd_D","away_odd":"Odd_A",
        "Prob_H":"Base_H","Prob_D":"Base_D","Prob_A":"Base_A",
        "Prob_Final_H":"Final_H","Prob_Final_D":"Final_D","Prob_Final_A":"Final_A"
    })
    st.dataframe(display_df, use_container_width=True)

    # ==========================================================
    # 🔍 Exibir últimos jogos (forma) e confrontos diretos (H2H)
    # ==========================================================
    st.subheader("📊 Últimos 5 jogos e H2H (detalhado por partida)")
    for _, row in df_show.iterrows():
        mid = row.get("MatchID")
        home = row.get("Home")
        away = row.get("Away")
        hid = row.get("HomeID")
        aid = row.get("AwayID")

        st.markdown(f"### ⚔️ {home}  x  {away}")

        # Home last 5
        with st.expander(f"📈 Últimos {last_n} jogos de {home}"):
            last_home = fetch_last_matches(hid, n=last_n)
            if last_home:
                rows = []
                for m in last_home[:last_n]:
                    utc = m.get("fixture", {}).get("date") or m.get("utcDate") or m.get("match_date")
                    when = utc[:10] if utc else ""
                    home_name = m.get("teams", {}).get("home", {}).get("name") or m.get("homeTeam", {}).get("name")
                    away_name = m.get("teams", {}).get("away", {}).get("name") or m.get("awayTeam", {}).get("name")
                    score = m.get("score", {}).get("fulltime") or m.get("score", {}).get("fullTime") or {}
                    hgo = score.get("home") if isinstance(score, dict) else None
                    ago = score.get("away") if isinstance(score, dict) else None
                    if hgo is None or ago is None:
                        placar = "-"
                        res = "-"
                    else:
                        placar = f"{hgo} - {ago}"
                        if home_name == home:
                            res = "V" if hgo > ago else "E" if hgo == ago else "D"
                        else:
                            res = "V" if ago > hgo else "E" if ago == hgo else "D"
                    rows.append({"Data": when, "Adversário": away_name if home_name == home else home_name, "Placar": placar, "Res": res})
                st.dataframe(pd.DataFrame(rows))
            else:
                st.info(f"Últimos jogos de {home} não disponíveis.")
              # Away last 5
        with st.expander(f"📉 Últimos {last_n} jogos de {away}"):
            last_away = fetch_last_matches(aid, n=last_n)
            if last_away:
                rows = []
                for m in last_away[:last_n]:
                    utc = m.get("fixture", {}).get("date") or m.get("utcDate") or m.get("match_date")
                    when = utc[:10] if utc else ""
                    home_name = m.get("teams", {}).get("home", {}).get("name") or m.get("homeTeam", {}).get("name")
                    away_name = m.get("teams", {}).get("away", {}).get("name") or m.get("awayTeam", {}).get("name")
                    score = m.get("score", {}).get("fulltime") or m.get("score", {}).get("fullTime") or {}
                    hgo = score.get("home") if isinstance(score, dict) else None
                    ago = score.get("away") if isinstance(score, dict) else None
                    if hgo is None or ago is None:
                        placar = "-"
                        res = "-"
                    else:
                        placar = f"{hgo} - {ago}"
                        if away_name == away:
                            res = "V" if ago > hgo else "E" if ago == hgo else "D"
                        else:
                            res = "V" if hgo > ago else "E" if hgo == ago else "D"
                    rows.append({"Data": when, "Adversário": home_name if away_name == away else away_name, "Placar": placar, "Res": res})
                st.dataframe(pd.DataFrame(rows))
            else:
                st.info(f"Últimos jogos de {away} não disponíveis.")

        # H2H
        with st.expander("🏟️ Confrontos Diretos (H2H)"):
            h2h = fetch_h2h(hid, aid, n=last_n)
            if h2h:
                rows = []
                for m in h2h[:last_n]:
                    utc = m.get("fixture", {}).get("date") or m.get("utcDate") or m.get("match_date")
                    when = utc[:10] if utc else ""
                    home_name = m.get("teams", {}).get("home", {}).get("name") or m.get("homeTeam", {}).get("name")
                    away_name = m.get("teams", {}).get("away", {}).get("name") or m.get("awayTeam", {}).get("name")
                    score = m.get("score", {}).get("fulltime") or m.get("score", {}).get("fullTime") or {}
                    hgo = score.get("home") if isinstance(score, dict) else None
                    ago = score.get("away") if isinstance(score, dict) else None
                    placar = f"{hgo} - {ago}" if hgo is not None and ago is not None else "-"
                    rows.append({"Data": when, "Casa": home_name, "Fora": away_name, "Placar": placar})
                st.dataframe(pd.DataFrame(rows))
            else:
                st.info("H2H não disponível para este confronto.")

        st.markdown("---")

# -------------------------
# SIMULADOR DE APOSTA (usa Prob_Final_* e odds quando disponiveis)
# -------------------------
st.subheader("💸 Simulação de Aposta")
banca = st.number_input("Banca inicial (R$):", value=100.0, min_value=1.0, step=10.0, format="%.2f")
stake = st.number_input("Valor por aposta (R$):", value=10.0, min_value=0.1, step=1.0, format="%.2f")

if st.button("Simular Retorno"):
    df_sim = st.session_state.get("matches_df", pd.DataFrame())
    if df_sim.empty:
        st.warning("Busque as partidas primeiro.")
    else:
        # seleciona apostas sugeridas: EV positivo se tivermos odds; senão escolhe maior Prob_Final
        total_profit = 0.0
        bets = []
        for _, r in df_sim.iterrows():
            # escolher melhor pick pela prob final
            pick = "H" if r["Prob_Final_H"] >= r["Prob_Final_D"] and r["Prob_Final_H"] >= r["Prob_Final_A"] else ("D" if r["Prob_Final_D"] >= r["Prob_Final_A"] else "A")
            odd = None
            if pick == "H":
                odd = r.get("home_odd")
                prob_model = r.get("Prob_Final_H")
            elif pick == "D":
                odd = r.get("draw_odd")
                prob_model = r.get("Prob_Final_D")
            else:
                odd = r.get("away_odd")
                prob_model = r.get("Prob_Final_A")

            if pd.notna(odd) and odd > 0:
                ev = prob_model * odd - 1
            else:
                ev = prob_model - 0.5  # simple proxy

            # simulate expected profit (stake * ev)
            expected_profit = stake * ev
            total_profit += expected_profit
            bets.append({
                "Match": f"{r['Home']} x {r['Away']}",
                "Pick": pick,
                "Odd": odd,
                "Prob": prob_model,
                "ExpectedProfit": round(expected_profit, 2)
            })

        st.success(f"Lucro esperado total (estimado): R$ {round(total_profit, 2)}")
        if bets:
            st.dataframe(pd.DataFrame(bets))

st.markdown("---")
st.caption("Observação: modelo simples. Para produção recomendamos calibrar pesos e usar endpoints pagos para maior granularidade de dados (lesões, escalações, odds múltiplas).")
