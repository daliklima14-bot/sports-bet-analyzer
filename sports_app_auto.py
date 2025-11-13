# sports_app_auto.py
# Versão com H2H + últimos N jogos (N = 5)
# Substitua seu arquivo atual por este.

import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import date
import time

# -------------------------
# CONFIGURAÇÕES INICIAIS
# -------------------------
st.set_page_config(page_title="Analisador de Apostas", page_icon="⚽", layout="centered")
st.title("⚽ Analisador e Simulador de Apostas Esportivas")
st.write("App automatizado para buscar estatísticas e calcular probabilidades das partidas do dia.")

# Pega API Key do Streamlit secrets
API_KEY = st.secrets.get("FOOTBALL_DATA_API_KEY", "")
API_BASE = "https://api.football-data.org/v4"

HEADERS = {"X-Auth-Token": API_KEY} if API_KEY else {}

# Mapeamento de ligas (adicione/ajuste conforme sua fonte)
LEAGUES_DICT = {
    "Premier League": "PL",
    "La Liga": "PD",
    "Serie A (Itália)": "SA",
    "Bundesliga": "BL1",
    "Ligue 1": "FL1",
    "Brasileirão Série A": "BSA"
}

# -------------------------
# FUNÇÕES AUXILIARES
# -------------------------
def montar_url_matches(league_code: str, data_iso: str):
    return f"{API_BASE}/competitions/{league_code}/matches?dateFrom={data_iso}&dateTo={data_iso}"

def buscar_partidas(data_jogos: date, ligas_selecionadas: list):
    resultados = []
    data_iso = data_jogos.isoformat()

    if not API_KEY:
        st.warning("⚠️ Sem API key configurada. Configure FOOTBALL_DATA_API_KEY em Streamlit Secrets.")
        return pd.DataFrame(resultados)

    for liga_nome in ligas_selecionadas:
        liga_code = LEAGUES_DICT.get(liga_nome, liga_nome)
        url = montar_url_matches(liga_code, data_iso)

        try:
            resp = requests.get(url, headers=HEADERS, timeout=12)
            if resp.status_code == 200:
                dados = resp.json()
                partidas = dados.get("matches", [])
                if not partidas:
                    st.info(f"🔎 Nenhuma partida encontrada para {liga_nome} na data {data_iso}.")
                for p in partidas:
                    utc = p.get("utcDate", "")
                    hora = utc[11:16] if utc else ""
                    home = p.get("homeTeam", {}).get("name", "")
                    away = p.get("awayTeam", {}).get("name", "")
                    home_id = p.get("homeTeam", {}).get("id", None)
                    away_id = p.get("awayTeam", {}).get("id", None)
                    status = p.get("status", "")
                    match_id = str(p.get("id", ""))

                    resultados.append({
                        "Competition": liga_code,
                        "Date": data_iso,
                        "Hour": hora,
                        "HomeTeam": home,
                        "AwayTeam": away,
                        "HomeID": home_id,
                        "AwayID": away_id,
                        "Status": status,
                        "MatchID": match_id
                    })
            else:
                st.warning(f"Erro ao buscar {liga_nome}: {resp.status_code} - {resp.text}")
        except Exception as e:
            st.error(f"Erro ao acessar API para {liga_nome}: {e}")

    df = pd.DataFrame(resultados)
    return df

# =======================================
# Função para buscar dados H2H (últimos 5 confrontos)
# =======================================
def buscar_h2h(home_id, away_id):
    if not API_KEY:
        st.warning("⚠️ Sem API key configurada.")
        return []

    url = f"https://api-football-v1.p.rapidapi.com/v3/fixtures/headtohead?h2h={home_id}-{away_id}&last=5"
    headers = {
        "x-rapidapi-key": API_KEY,
        "x-rapidapi-host": "api-football-v1.p.rapidapi.com"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=12)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("response", [])
        else:
            st.warning(f"Erro ao buscar H2H: {resp.status_code}")
            return []
    except Exception as e:
        st.error(f"Erro ao acessar API H2H: {e}")
        return []
st.dataframe(
    df.rename(columns={
        "Competition": "Comp", "Date": "Data", "Hour": "Hora",
        "HomeTeam": "Mandante", "AwayTeam": "Visitante",
        "Prob_H": "Prob_Mandante", "Prob_D": "Prob_Empate", "Prob_A": "Prob_Visitante",
        "Home_FormPts": "Forma Mandante", "Away_FormPts": "Forma Visitante",
        "Home_GPM": "GPM Mandante", "Away_GPM": "GPM Visitante"
    }),
    use_container_width=True
)

# ==========================================================
# 🔍 Exibir últimos jogos (forma) e confrontos diretos (H2H)
# ==========================================================
if not df_matches.empty:
    st.subheader("📊 Histórico e Forma Recente")

    for _, row in df_matches.iterrows():
        home_team = row['Home']
        away_team = row['Away']

        st.markdown(f"### ⚔️ {home_team} 🆚 {away_team}")

        # Expanders para forma e H2H
        with st.expander(f"📈 Últimos 5 jogos do {home_team}"):
            try:
                url_home_form = f"https://api.theapifootball.com/?action=get_events&team_id={row['HomeID']}&from=2025-01-01&to=2025-12-31&APIkey={API_KEY}"
                r_home = requests.get(url_home_form)
                if r_home.status_code == 200:
                    data_home = r_home.json()[:5]
                    df_home = pd.DataFrame([{
                        "Data": g.get("match_date"),
                        "Adversário": g.get("match_awayteam_name") if g.get("match_hometeam_name") == home_team else g.get("match_hometeam_name"),
                        "Placar": f"{g.get('match_hometeam_score')} - {g.get('match_awayteam_score')}",
                        "Resultado": (
                            "✅ Vitória" if (
                                (g.get("match_hometeam_name") == home_team and int(g.get("match_hometeam_score") or 0) > int(g.get("match_awayteam_score") or 0)) or
                                (g.get("match_awayteam_name") == home_team and int(g.get("match_awayteam_score") or 0) > int(g.get("match_hometeam_score") or 0))
                            ) else "❌ Derrota" if (
                                (g.get("match_hometeam_name") == home_team and int(g.get("match_hometeam_score") or 0) < int(g.get("match_awayteam_score") or 0)) or
                                (g.get("match_awayteam_name") == home_team and int(g.get("match_awayteam_score") or 0) < int(g.get("match_hometeam_score") or 0))
                            ) else "🤝 Empate"
                        )
                    } for g in data_home])
                    st.dataframe(df_home)
                else:
                    st.warning("Não foi possível carregar os últimos jogos do mandante.")
            except Exception as e:
                st.error(f"Erro ao carregar forma do mandante: {e}")

        with st.expander(f"📉 Últimos 5 jogos do {away_team}"):
            try:
                url_away_form = f"https://api.theapifootball.com/?action=get_events&team_id={row['AwayID']}&from=2025-01-01&to=2025-12-31&APIkey={API_KEY}"
                r_away = requests.get(url_away_form)
                if r_away.status_code == 200:
                    data_away = r_away.json()[:5]
                    df_away = pd.DataFrame([{
                        "Data": g.get("match_date"),
                        "Adversário": g.get("match_awayteam_name") if g.get("match_hometeam_name") == away_team else g.get("match_hometeam_name"),
                        "Placar": f"{g.get('match_hometeam_score')} - {g.get('match_awayteam_score')}",
                        "Resultado": (
                            "✅ Vitória" if (
                                (g.get("match_hometeam_name") == away_team and int(g.get("match_hometeam_score") or 0) > int(g.get("match_awayteam_score") or 0)) or
                                (g.get("match_awayteam_name") == away_team and int(g.get("match_awayteam_score") or 0) > int(g.get("match_hometeam_score") or 0))
                            ) else "❌ Derrota" if (
                                (g.get("match_hometeam_name") == away_team and int(g.get("match_hometeam_score") or 0) < int(g.get("match_awayteam_score") or 0)) or
                                (g.get("match_awayteam_name") == away_team and int(g.get("match_awayteam_score") or 0) < int(g.get("match_hometeam_score") or 0))
                            ) else "🤝 Empate"
                        )
                    } for g in data_away])
                    st.dataframe(df_away)
                else:
                    st.warning("Não foi possível carregar os últimos jogos do visitante.")
            except Exception as e:
                st.error(f"Erro ao carregar forma do visitante: {e}")

        with st.expander(f"🏟️ Confrontos Diretos (H2H)"):
            try:
                url_h2h = f"https://api.theapifootball.com/?action=get_H2H&firstTeam={home_team}&secondTeam={away_team}&APIkey={API_KEY}"
                r_h2h = requests.get(url_h2h)
                if r_h2h.status_code == 200:
                    data_h2h = r_h2h.json().get("firstTeam_VS_secondTeam", [])[:5]
                    df_h2h = pd.DataFrame([{
                        "Data": g.get("match_date"),
                        "Casa": g.get("match_hometeam_name"),
                        "Fora": g.get("match_awayteam_name"),
                        "Placar": f"{g.get('match_hometeam_score')} - {g.get('match_awayteam_score')}"
                    } for g in data_h2h])
                    st.dataframe(df_h2h)
                else:
                    st.warning("Não foi possível carregar o histórico H2H.")
            except Exception as e:
                st.error(f"Erro ao carregar H2H: {e}")
def buscar_odds_para_match(match_id: str):
    
    # Buscar histórico H2H e últimos jogos por time
h2h_data = buscar_h2h(match_id)
home_form = buscar_ultimos_jogos(row["HomeTeam"], last_n=5)
away_form = buscar_ultimos_jogos(row["AwayTeam"], last_n=5)

# Adicionar média de pontos e gols
df.at[row.name, "Home_FormPts"] = home_form["pontos_medios"]
df.at[row.name, "Away_FormPts"] = away_form["pontos_medios"]
df.at[row.name, "Home_GPM"] = home_form["gols_marcados"]
df.at[row.name, "Away_GPM"] = away_form["gols_marcados"]
    """
    Tentativa de buscar odds. football-data.org geralmente não fornece odds; este é um fallback
    que tenta /matches/{id}/odds se disponível. Caso contrário retorna None.
    """
    url = f"{API_BASE}/matches/{match_id}/odds"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=8)
        if resp.status_code == 200:
            j = resp.json()
            # Estruturas variam muito; extrair com defensividade
            if "odds" in j:
                o = j["odds"]
                if all(k in o for k in ("home", "draw", "away")):
                    return {"home_odd": float(o["home"]), "draw_odd": float(o["draw"]), "away_odd": float(o["away"])}
            # fallback: procurar bookmakers/markets
            if isinstance(j, dict):
                for k in ("bookmakers", "markets", "bets"):
                    if k in j and isinstance(j[k], list) and j[k]:
                        first = j[k][0]
                        # procura por valores numéricos
                        for v in (first.get("values") or first.get("bets") or []):
                            # tenta extrair 3 valores
                            vals = []
                            if isinstance(v, dict):
                                # pode ter keys 'odd' ou 'value' ou 'price'
                                for entry in (v.get("values") or []):
                                    val = entry.get("odd") or entry.get("value") or entry.get("price")
                                    if val is not None:
                                        try:
                                            vals.append(float(val))
                                        except:
                                            pass
                                if len(vals) >= 3:
                                    return {"home_odd": vals[0], "draw_odd": vals[1], "away_odd": vals[2]}
            return None
        else:
            return None
    except Exception:
        return None

def fetch_last_matches(team_id: int, n: int = 5):
    """
    Busca últimos n jogos do time. Retorna lista de partidas (json) ou [].
    Endpoint usado: /teams/{team_id}/matches?status=FINISHED&limit=n (tenta params defensivo)
    """
    if not team_id:
        return []
    url = f"{API_BASE}/teams/{team_id}/matches"
    params = {"status": "FINISHED", "limit": n}
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
        if resp.status_code == 200:
            j = resp.json()
            return j.get("matches", [])
        else:
            return []
    except Exception:
        return []

def calcular_stats_ultimos_jogos(matches_list, team_id):
    """
    A partir de lista de matches (json) calcula stats: pts por jogo, gols pró/contra, W/D/L counts.
    """
    if not matches_list:
        return {"games": 0, "pts": 0, "g_for": 0, "g_against": 0, "wins": 0, "draws": 0, "losses": 0}

    pts = 0
    g_for = 0
    g_against = 0
    wins = draws = losses = 0
    games = 0

    for m in matches_list:
        # procurar score final em m["score"] ou m["fullTime"]
        score = m.get("score", {})
        full = score.get("fullTime", {}) or score.get("fullTime", {})
        home_id = m.get("homeTeam", {}).get("id")
        away_id = m.get("awayTeam", {}).get("id")
        home_goals = full.get("home") if isinstance(full.get("home"), int) else None
        away_goals = full.get("away") if isinstance(full.get("away"), int) else None

        if home_goals is None or away_goals is None:
            # se não houver placar final, pula
            continue

        games += 1
        if team_id == home_id:
            gf, ga = home_goals, away_goals
            is_win = gf > ga
            is_draw = gf == ga
        else:
            gf, ga = away_goals, home_goals
            is_win = gf > ga
            is_draw = gf == ga

        g_for += gf
        g_against += ga
        if is_win:
            pts += 3
            wins += 1
        elif is_draw:
            pts += 1
            draws += 1
        else:
            losses += 1

    return {
        "games": games,
        "pts": pts,
        "g_for": g_for,
        "g_against": g_against,
        "wins": wins,
        "draws": draws,
        "losses": losses
    }

def calcular_h2h(home_id, away_id, n=5):
    """
    Calcula head-to-head recente entre as duas equipes.
    Método: pega últimos n jogos de cada time e filtra aqueles contra o outro time.
    Retorna dict com contagem e proporção.
    """
    if not home_id or not away_id:
        return {"h2h_games": 0, "h2h_home_wins": 0, "h2h_away_wins": 0, "h2h_draws": 0}

    home_matches = fetch_last_matches(home_id, n*3)  # pegar mais para tentar encontrar H2H
    away_matches = fetch_last_matches(away_id, n*3)

    # encontrar jogos onde ambos aparecem
    encounters = []
    # varre home_matches e pega aqueles com opponent = away_id
    for m in home_matches:
        hid = m.get("homeTeam", {}).get("id")
        aid = m.get("awayTeam", {}).get("id")
        if hid == home_id and (aid == away_id):
            encounters.append(m)
        elif aid == home_id and (hid == away_id):
            encounters.append(m)
    # também varre away_matches -> de-dup com encounters
    for m in away_matches:
        hid = m.get("homeTeam", {}).get("id")
        aid = m.get("awayTeam", {}).get("id")
        if (hid == home_id and aid == away_id) or (aid == home_id and hid == away_id):
            if m not in encounters:
                encounters.append(m)

    # limitar a n últimos encontros por ordem original (podemos ordenar por utcDate desc)
    encounters = sorted(encounters, key=lambda x: x.get("utcDate", ""), reverse=True)[:n]

    h2h_home_wins = h2h_away_wins = h2h_draws = 0
    for m in encounters:
        full = m.get("score", {}).get("fullTime", {}) or {}
        home_goals = full.get("home")
        away_goals = full.get("away")
        if home_goals is None or away_goals is None:
            continue
        if home_goals > away_goals:
            # home team of that match won
            if m.get("homeTeam", {}).get("id") == home_id:
                h2h_home_wins += 1
            else:
                h2h_away_wins += 1
        elif home_goals < away_goals:
            if m.get("awayTeam", {}).get("id") == home_id:
                h2h_home_wins += 1
            else:
                h2h_away_wins += 1
        else:
            h2h_draws += 1

    return {"h2h_games": len(encounters), "h2h_home_wins": h2h_home_wins, "h2h_away_wins": h2h_away_wins, "h2h_draws": h2h_draws}

def calcular_probabilidades_completas(df: pd.DataFrame, use_h2h=True, last_n=5):
    """
    Ajusta e combina probabilidades:
      - Parte base: probabilidades extraídas de odds (se existirem) ou mock/model
      - Parte forma: últimos N jogos (points per match) convertem em fator
      - Parte H2H: vantagem direta recente
    Pesos (ajustáveis):
      w_base = 0.65, w_form = 0.25, w_h2h = 0.10
    """
    if df.empty:
        return df

    df = df.copy()
    # garante colunas de ids existirem
    for c in ["HomeID", "AwayID"]:
        if c not in df.columns:
            df[c] = None

    w_base = 0.65
    w_form = 0.25
    w_h2h = 0.10 if use_h2h else 0.0
    # fallback se sum >1
    total_w = w_base + w_form + w_h2h
    w_base /= total_w; w_form /= total_w; w_h2h /= total_w

    # preenche probabilidades base: se já existe Prob_H/D/A mantem; se não, cria mock
    if not all(c in df.columns for c in ("Prob_H", "Prob_D", "Prob_A")):
        df = mock_calcular_probabilidades_por_modelo(df)

    # para cada linha, pegar stats de últimos N jogos e H2H
    form_H = []
    form_D = []
    form_A = []
    # processa por linha
    for _, r in df.iterrows():
        hid = r.get("HomeID")
        aid = r.get("AwayID")

        # stats home
        stats_home = fetch_last_matches(hid, last_n)
        st_home = calcular_stats_ultimos_jogos(stats_home, hid)
        # stats away
        stats_away = fetch_last_matches(aid, last_n)
        st_away = calcular_stats_ultimos_jogos(stats_away, aid)

        # points per match
        ppm_home = (st_home["pts"] / st_home["games"]) if st_home["games"] > 0 else 1.0
        ppm_away = (st_away["pts"] / st_away["games"]) if st_away["games"] > 0 else 1.0

        # normaliza forma simples: transforma em prob favor do mandante
        total_ppm = ppm_home + ppm_away if (ppm_home + ppm_away) > 0 else 1.0
        prob_form_home = ppm_home / total_ppm
        prob_form_away = ppm_away / total_ppm

        # prob draw baseline from form: média dos dois inversos (mais conservadora)
        prob_form_draw = max(0.05, 1 - (abs(prob_form_home - prob_form_away))) * 0.2  # pequena porção

        # entrevista final das 3 (ajustar para somar 1)
        form_h = prob_form_home * (1 - prob_form_draw)
        form_a = prob_form_away * (1 - prob_form_draw)
        form_d = prob_form_draw

        # H2H
        h2h_info = calcular_h2h(hid, aid, n=last_n) if use_h2h else {"h2h_games": 0, "h2h_home_wins": 0, "h2h_away_wins": 0, "h2h_draws": 0}
        h2h_games = h2h_info.get("h2h_games", 0)
        if h2h_games > 0:
            h2h_home_prob = (h2h_info.get("h2h_home_wins", 0) / h2h_games)
            h2h_away_prob = (h2h_info.get("h2h_away_wins", 0) / h2h_games)
            h2h_draw_prob = (h2h_info.get("h2h_draws", 0) / h2h_games)
        else:
            h2h_home_prob = h2h_away_prob = h2h_draw_prob = 1/3

        form_H.append((form_h, h2h_home_prob))
        form_D.append((form_d, h2h_draw_prob))
        form_A.append((form_a, h2h_away_prob))

        # curto delay pra evitar rate limit
        time.sleep(0.12)

    # agora combina
    new_probs = []
    for idx, r in df.iterrows():
        base_h = float(r.get("Prob_H") or 0)
        base_d = float(r.get("Prob_D") or 0)
        base_a = float(r.get("Prob_A") or 0)

        form_h, h2h_h = form_H[idx]
        form_d, h2h_d = form_D[idx]
        form_a, h2h_a = form_A[idx]

        # combine form and h2h into a single form_h, form_d, form_a using weights w_form and w_h2h internally
        # internal split: form_part = 0.8 of w_form, h2h_part = 0.2 of w_form (already scaled externally by w_form/w_h2h)
        combined_h = w_base * base_h + w_form * form_h + w_h2h * h2h_h
        combined_d = w_base * base_d + w_form * form_d + w_h2h * h2h_d
        combined_a = w_base * base_a + w_form * form_a + w_h2h * h2h_a

        # normaliza
        total = combined_h + combined_d + combined_a
        if total <= 0:
            combined_h, combined_d, combined_a = 0.34, 0.32, 0.34
        else:
            combined_h /= total
            combined_d /= total
            combined_a /= total

        new_probs.append((round(combined_h, 2), round(combined_d, 2), round(combined_a, 2)))

    df["Prob_H"], df["Prob_D"], df["Prob_A"] = zip(*new_probs)
    return df

def calcular_probabilidades_por_odds(df: pd.DataFrame):
    df = df.copy()
    if not all(c in df.columns for c in ("home_odd", "draw_odd", "away_odd")):
        return df
    for c in ("home_odd", "draw_odd", "away_odd"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    def odds_to_probs(row):
        h, d, a = row["home_odd"], row["draw_odd"], row["away_odd"]
        if pd.isna(h) or pd.isna(d) or pd.isna(a) or any(x <= 0 for x in [h, d, a]):
            return pd.Series([np.nan, np.nan, np.nan])
        inv = np.array([1.0/h, 1.0/d, 1.0/a])
        total = inv.sum()
        probs = inv / total
        return pd.Series(probs)
    probs = df.apply(odds_to_probs, axis=1)
    probs.columns = ["Prob_H", "Prob_D", "Prob_A"]
    df = pd.concat([df, probs], axis=1)
    return df

def mock_calcular_probabilidades_por_modelo(df: pd.DataFrame):
    df = df.copy()
    n = len(df)
    if n == 0:
        return df
    rng = np.random.default_rng(seed=42)
    probs = rng.random((n, 3))
    probs = probs / probs.sum(axis=1, keepdims=True)
    df["Prob_H"] = probs[:, 0].round(2)
    df["Prob_D"] = probs[:, 1].round(2)
    df["Prob_A"] = probs[:, 2].round(2)
    return df

def simular_retorno(df: pd.DataFrame, banca_inicial: float, stake: float):
    if df.empty:
        return 0.0, pd.DataFrame()
    df = df.copy()
    # precisa de Prob_* e odds
    if not all(col in df.columns for col in ("Prob_H", "Prob_D", "Prob_A", "home_odd", "draw_odd", "away_odd")):
        st.warning("Dados insuficientes para simular retorno real — faltam odds ou probabilidades calculadas.")
        return 0.0, pd.DataFrame()
    resultados = []
    banca = banca_inicial
    for _, r in df.iterrows():
        probs = {"H": r["Prob_H"], "D": r["Prob_D"], "A": r["Prob_A"]}
        escolha = max(probs, key=probs.get)
        odd_col = {"H": "home_odd", "D": "draw_odd", "A": "away_odd"}[escolha]
        odd = r.get(odd_col, np.nan)
        rand = np.random.random()
        ganhou = rand < probs[escolha]
        if ganhou:
            ganho = (stake * odd) - stake
            banca += ganho
        else:
            ganho = -stake
            banca += ganho
        resultados.append({
            "Home": r.get("HomeTeam"),
            "Away": r.get("AwayTeam"),
            "Pick": escolha,
            "Odd": odd,
            "Won": ganhou,
            "Profit": round(ganho, 2),
            "Banca_After": round(banca, 2)
        })
    res_df = pd.DataFrame(resultados)
    lucro_total = round(banca - banca_inicial, 2)
    return lucro_total, res_df

# -------------------------
# UI: inputs
# -------------------------
st.subheader("📅 Partidas do Dia")
data_input = st.date_input("Selecione a data:", value=date.today(), key="data_busca")
league_options = list(LEAGUES_DICT.keys())
selected_leagues = st.multiselect("Selecione as ligas:", options=league_options, default=["Brasileirão Série A"])
modo_analise = st.radio("Modo de análise:", options=["Odds Reais (API)", "Simulação Aleatória"], index=0)
enable_h2h = st.checkbox("Incluir H2H e últimos N jogos na análise", value=True)
last_n = st.number_input("Últimos N jogos (por time) para forma/H2H:", min_value=1, max_value=10, value=5, step=1)
buscar_botao = st.button("Buscar Partidas")

# session_state
if "df_matches" not in st.session_state:
    st.session_state["df_matches"] = pd.DataFrame()

# Ao buscar:
if buscar_botao:
    with st.spinner("🔎 Buscando partidas e probabilidades..."):
        df = buscar_partidas(data_input, selected_leagues)
        if df.empty:
            st.session_state["df_matches"] = pd.DataFrame()
            st.warning("Nenhuma partida encontrada para essa data/ligas.")
        else:
            df["home_odd"] = np.nan
            df["draw_odd"] = np.nan
            df["away_odd"] = np.nan

            if modo_analise == "Odds Reais (API)":
                for i, row in df.iterrows():
                    match_id = row.get("MatchID")
                    if match_id:
                        odds = buscar_odds_para_match(match_id)
                        if odds:
                            df.at[i, "home_odd"] = odds.get("home_odd")
                            df.at[i, "draw_odd"] = odds.get("draw_odd")
                            df.at[i, "away_odd"] = odds.get("away_odd")
                    time.sleep(0.15)

            # se houver odds preenchidas, usar; caso contrário mock
            if all(col in df.columns for col in ("home_odd", "draw_odd", "away_odd")) and df[["home_odd","draw_odd","away_odd"]].notna().any(axis=None):
                df = calcular_probabilidades_por_odds(df)
            else:
                df = mock_calcular_probabilidades_por_modelo(df)

            # agora combinar com forma / H2H
            df = calcular_probabilidades_completas(df, use_h2h=enable_h2h, last_n=int(last_n))

            # armazenar
            st.session_state["df_matches"] = df

            st.success("✅ Partidas e probabilidades obtidas com sucesso!")
            st.dataframe(df.rename(columns={
                "Competition": "Comp", "Date": "Data", "Hour": "Hora",
                "HomeTeam": "Mandante", "AwayTeam": "Visitante",
                "Prob_H": "Prob_Mandante", "Prob_D": "Prob_Empate", "Prob_A": "Prob_Visitante",
                "home_odd": "Odd_Mandante", "draw_odd": "Odd_Empate", "away_odd": "Odd_Visitante"
            }), use_container_width=True)

# preview se já carregado
if not st.session_state["df_matches"].empty and not buscar_botao:
    st.info("Partidas carregadas (sessão). Clique em 'Buscar Partidas' para atualizar.")
    st.dataframe(st.session_state["df_matches"].head(50), use_container_width=True)

# -------------------------
# Simulação de Aposta
# -------------------------
st.subheader("💰 Simulação de Aposta")
banca_inicial = st.number_input("Informe sua banca inicial (R$):", value=100.0, min_value=1.0, step=10.0, format="%.2f", key="banca_inicial")
valor_stake = st.number_input("Informe o valor por aposta (stake) (R$):", value=10.0, min_value=0.1, step=1.0, format="%.2f", key="valor_stake")

if st.button("Simular Retorno"):
    df_sim = st.session_state.get("df_matches", pd.DataFrame())
    if df_sim.empty:
        st.warning("Faça a busca de partidas primeiro — sem jogos não há simulação.")
    else:
        lucro, detalhe = simular_retorno(df_sim, banca_inicial, valor_stake)
        st.success(f"Resultado da simulação: lucro estimado R$ {lucro:.2f}")
        if not detalhe.empty:
            st.dataframe(detalhe, use_container_width=True)
        else:
            st.info("Não foi possível gerar detalhes da simulação (falta de odds/probabilidades reais).")

st.markdown("---")
st.markdown("**Observações & próximos passos**")
st.markdown("""
- H2H e últimos N jogos tentam melhorar o peso da forma (últimos jogos) e da história entre os clubes (H2H).
- Se sua conta/planos não devolverem endpoints de team matches/odds, o app continuará com fallbacks (mock).  
- Posso ajustar os pesos (w_base, w_form, w_h2h) ou melhorar o modelo quando tivermos dados adicionais (por ex. ranking, jogadores, lesões).
""")
