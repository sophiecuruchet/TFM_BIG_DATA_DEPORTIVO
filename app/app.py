
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from urllib.parse import quote
import base64
import unicodedata
from io import StringIO
import re
import requests
from bs4 import BeautifulSoup

st.set_page_config(page_title="ATP Analytics | TFM", layout="wide", page_icon="🎾")

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data" / "processed"
ASSETS = BASE / "app" / "assets"
PLAYER_ASSETS = ASSETS / "players"
ATP_RANKINGS_URL = "https://www.atptour.com/en/rankings/singles"
YEAR_END_RANKING_DATES = {2022: "2022-12-26", 2023: "2023-12-25", 2024: "2024-12-30", 2025: "2025-12-29"}
ALCARAZ = "Carlos Alcaraz"
ALCARAZ_RED = "#ff3b30"
BLUE = "#4f83ff"
GREEN = "#2ecc71"
ORANGE = "#ff8c42"
YELLOW = "#ffc857"
PURPLE = "#9b59b6"
BG = "#f6f8fb"
CARD = "#ffffff"
TEXT = "#101828"
MUTED = "#667085"

# style
def slugify_name(name: str) -> str:
    name = str(name).strip()
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    name = re.sub(r"[^a-zA-Z0-9]+", "_", name.lower()).strip("_")
    return name or "player"

def initials_from_name(name: str) -> str:
    parts = [p for p in re.split(r"\s+", str(name).strip()) if p]
    if not parts: return "ATP"
    if len(parts) == 1: return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()

def is_alcaraz(name) -> bool:
    return "alcaraz" in str(name).lower()

def avatar_data_uri(player_name: str, is_target: bool = False) -> str:
    initials = initials_from_name(player_name)
    bg = ALCARAZ_RED if is_target else "#101c2d"
    stroke = "#ffb2ac" if is_target else BLUE
    svg = f"""<svg xmlns='http://www.w3.org/2000/svg' width='256' height='256' viewBox='0 0 256 256'>
    <defs><radialGradient id='g' cx='35%' cy='20%' r='85%'><stop offset='0' stop-color='{stroke}' stop-opacity='0.9'/><stop offset='1' stop-color='{bg}'/></radialGradient></defs>
    <rect width='256' height='256' rx='128' fill='url(#g)'/>
    <circle cx='128' cy='102' r='42' fill='rgba(255,255,255,0.30)'/>
    <path d='M54 224c12-50 50-78 74-78s62 28 74 78' fill='rgba(255,255,255,0.22)'/>
    <text x='128' y='238' font-family='Arial, Helvetica, sans-serif' font-size='36' font-weight='800' fill='#fff' text-anchor='middle'>{initials}</text>
    </svg>"""
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")

def local_player_image(player_name: str):
    slug = slugify_name(player_name)
    for ext in ["png", "jpg", "jpeg", "webp"]:
        p = PLAYER_ASSETS / f"{slug}.{ext}"
        if p.exists():
            return p
    default = PLAYER_ASSETS / "default_player.png"
    if default.exists():
        return default
    return None

def image_file_to_data_uri(path):
    path = Path(path)
    mime = "image/png"
    if path.suffix.lower() in [".jpg", ".jpeg"]:
        mime = "image/jpeg"
    elif path.suffix.lower() == ".webp":
        mime = "image/webp"
    try:
        return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")
    except Exception:
        return None

@st.cache_data(show_spinner=False, ttl=60*60*24)
def get_player_photo(player_name):
    """Devuelve foto local del jugador. Si no existe, usa una imagen neutra por defecto."""
    local = local_player_image(player_name)
    if local:
        uri = image_file_to_data_uri(local)
        if uri:
            return uri
    default = PLAYER_ASSETS / "default_player.png"
    if default.exists():
        uri = image_file_to_data_uri(default)
        if uri:
            return uri
    return avatar_data_uri("ATP", False)

def palette_for(players):
    shades = [BLUE, GREEN, ORANGE, YELLOW, PURPLE, "#35c2ff", "#98bbff"]
    out, i = {}, 0
    for p in players:
        if is_alcaraz(p): out[p] = ALCARAZ_RED
        else:
            out[p] = shades[i % len(shades)]
            i += 1
    return out

def color_list_by_player(series):
    return [ALCARAZ_RED if is_alcaraz(x) else BLUE for x in series]

def apply_dark_layout(fig, title=None, height=None):
   
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT, family="Arial"),
        title=dict(text=title or fig.layout.title.text, font=dict(size=19, color=TEXT)),
        margin=dict(l=24, r=24, t=58, b=35),
        legend=dict(bgcolor="rgba(255,255,255,0)", font=dict(color=TEXT)),
        height=height or fig.layout.height,
    )
    fig.update_xaxes(gridcolor="rgba(16,24,40,0.10)", zerolinecolor="rgba(16,24,40,0.16)", linecolor="rgba(16,24,40,0.18)", tickfont=dict(color=MUTED), title_font=dict(color=MUTED))
    fig.update_yaxes(gridcolor="rgba(16,24,40,0.10)", zerolinecolor="rgba(16,24,40,0.16)", linecolor="rgba(16,24,40,0.18)", tickfont=dict(color=MUTED), title_font=dict(color=MUTED))
    return fig

def metric_card(label, value, note="", icon=""):
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{icon} {label}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-note">{note}</div>
    </div>
    """, unsafe_allow_html=True)

def highlight_alcaraz(row):
    name = row.get("player", row.get("Jugador", ""))
    if is_alcaraz(name):
        return [f"color: {ALCARAZ_RED}; font-weight: 800; background-color: rgba(255,59,48,0.10)" for _ in row]
    return ["" for _ in row]

st.markdown(f"""
<style>
/* ===== TFM ATP PLATFORM: estilo claro con sidebar azul oscuro ===== */
.stApp {{
    background: #f6f8fb;
    color: {TEXT};
}}
.block-container {{
    padding-top: 1.5rem;
    padding-bottom: 2.5rem;
    max-width: 1280px;
}}
[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, #021a35 0%, #06284c 55%, #021326 100%);
    border-right: 1px solid rgba(255,255,255,0.12);
}}
[data-testid="stSidebar"] * {{ color: #ffffff !important; }}
[data-testid="stSidebar"] [role="radiogroup"] label {{
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 12px;
    padding: 8px 10px;
    margin: 5px 0;
}}
[data-testid="stSidebar"] [role="radiogroup"] label:hover {{
    background: rgba(30,112,255,0.35);
}}
h1, h2, h3 {{
    color: {TEXT};
    letter-spacing: -0.03em;
    font-weight: 900;
}}
p, span, label, div {{ font-family: Arial, Helvetica, sans-serif; }}
.hero-card {{
    background: linear-gradient(135deg, #ffffff 0%, #f7fbff 100%);
    border: 1px solid #d9e3f0;
    border-radius: 20px;
    padding: 26px 28px;
    box-shadow: 0 16px 40px rgba(16,24,40,0.08);
}}
.hero-title {{
    font-size: 2.4rem;
    font-weight: 950;
    color: #07152a;
    margin-bottom: .25rem;
}}
.hero-subtitle {{ color: {MUTED}; font-size: 1.05rem; }}
.metric-card, .info-card {{
    background: #ffffff;
    border: 1px solid #d9e3f0;
    border-radius: 16px;
    padding: 17px 18px;
    box-shadow: 0 10px 28px rgba(16,24,40,0.07);
}}
.metric-label {{ color: {MUTED}; font-size: 0.86rem; margin-bottom: 0.2rem; }}
.metric-value {{ color: {TEXT}; font-size: 1.75rem; font-weight: 900; line-height: 1.1; }}
.metric-note {{ color: {MUTED}; font-size: 0.8rem; margin-top: 0.2rem; }}
.alcaraz-note {{
    background: rgba(255,59,48,0.08);
    border: 1px solid rgba(255,59,48,0.30);
    border-radius: 14px;
    padding: 12px 14px;
    color: #7a1d17;
    margin: 0.4rem 0 1rem 0;
}}
.rank-card {{
    background: #ffffff;
    border: 1px solid #d9e3f0;
    border-radius: 16px;
    padding: 14px;
    min-height: 255px;
    box-shadow: 0 10px 26px rgba(16,24,40,0.08);
    text-align: center;
}}
.rank-card-alcaraz {{
    border: 2px solid {ALCARAZ_RED};
    box-shadow: 0 0 0 1px rgba(255,59,48,0.18), 0 14px 32px rgba(255,59,48,0.12);
}}
.rank-name {{ font-size: 1.03rem; font-weight: 900; margin-top: 0.6rem; color: {TEXT}; }}
.rank-name-alcaraz {{ color: {ALCARAZ_RED}; }}
.small-muted {{ color: {MUTED}; font-size: 0.82rem; }}
.featured-card {{
    background: #ffffff;
    border: 1px solid #d9e3f0;
    border-radius: 18px;
    padding: 16px;
    text-align:center;
    margin-bottom:12px;
    min-height:250px;
    box-shadow: 0 10px 26px rgba(16,24,40,0.08);
}}
.featured-card-alcaraz {{ border: 2px solid {ALCARAZ_RED}; box-shadow: 0 0 28px rgba(255,59,48,.13); }}
.featured-photo {{
    width:112px;
    height:112px;
    border-radius:999px;
    object-fit:cover;
    border:3px solid #e6eef8;
    background:#eef2f7;
}}
.featured-photo-alcaraz {{ border-color:{ALCARAZ_RED}; }}
.featured-name {{ font-size:1.05rem; font-weight:900; margin-top:.6rem; color:{TEXT}; }}
.featured-name-alcaraz {{ color:{ALCARAZ_RED}; }}
.featured-rank, .featured-country {{ color:{MUTED}; font-size:.82rem; }}
.featured-points {{ font-size:1.2rem; font-weight:900; margin-top:.35rem; color:{TEXT}; }}
.featured-points-alcaraz {{ color:{ALCARAZ_RED}; }}
div[data-testid="stMetric"] {{
    background: #ffffff;
    border: 1px solid #d9e3f0;
    border-radius: 16px;
    padding: 14px 16px;
    box-shadow: 0 10px 24px rgba(16,24,40,0.07);
}}
div[data-testid="stMetricLabel"] p {{ color: {MUTED}; }}
div[data-testid="stMetricValue"] {{ color: {TEXT}; }}
/* Selectores y tablas */
.stSelectbox div[data-baseweb="select"] > div {{
    background: #ffffff;
    border-color: #d0d7e2;
    color: {TEXT};
}}
[data-testid="stDataFrame"] {{
    border: 1px solid #d9e3f0;
    border-radius: 14px;
    overflow: hidden;
    box-shadow: 0 8px 20px rgba(16,24,40,0.05);
}}
/* Contenedor de gráficos */
.js-plotly-plot, .plot-container {{
    background: #ffffff !important;
    border-radius: 16px;
}}
a {{ color: #0b63ce !important; }}
</style>
""", unsafe_allow_html=True)

# Data load
def load_csv(name):
    return pd.read_csv(DATA / name)

summary = load_csv("project_summary.csv").iloc[0]
players_base = load_csv("player_summary_2022_2025.csv")
matches = load_csv("matches_2022_2025.csv")
overview = load_csv("overview_player_match_2022_2025.csv")
al_year = load_csv("alcaraz_year_summary_2022_2025.csv")
al_surface = load_csv("alcaraz_surface_summary_2022_2025.csv")
al_shots = load_csv("alcaraz_shot_types_summary_2022_2025.csv")
rally_alcaraz = load_csv("alcaraz_rally_segments_2022_2025.csv")
rally_all = load_csv("rally_player_segments_2022_2025.csv")
shot_types_all = load_csv("shot_types_player_match_2022_2025.csv")
net_all = load_csv("net_points_player_match_2022_2025.csv")
rankings_fallback = load_csv("atp_year_end_rankings_2022_2025.csv")
alcaraz_matches = load_csv("alcaraz_match_level_2022_2025.csv")
alcaraz_titles = load_csv("alcaraz_titles_2022_2025.csv")
alcaraz_records = load_csv("alcaraz_records_2022_2025.csv")

for df in [players_base, matches, overview, al_year, al_surface, al_shots, rally_alcaraz, rally_all, shot_types_all, net_all]:
    if "year" in df.columns: df["year"] = pd.to_numeric(df["year"], errors="coerce")
    if "Surface" in df.columns: df["Surface"] = df["Surface"].fillna("Unknown")

METRIC_LABELS = {
    "first_won_pct": "% puntos ganados con 1er saque",
    "second_won_pct": "% puntos ganados con 2º saque",
    "return_won_pct": "% puntos ganados al resto",
    "bp_saved_pct": "% break points salvados",
    "winner_ue_ratio": "Ratio winners / errores no forzados",
    "net_won_pct": "% puntos ganados en red",
    "long_rally_won_pct": "% puntos ganados rallies >9",
}
PCT_METRICS = ["first_won_pct", "second_won_pct", "return_won_pct", "bp_saved_pct", "net_won_pct", "long_rally_won_pct"]
SHOT_LABELS = {"Fside":"Lado de derecha", "Bside":"Lado de revés", "Fgs":"Derecha", "Bgs":"Revés", "F":"Derecha", "B":"Revés", "V":"Volea", "Vo":"Volea", "Fv":"Volea de derecha", "Bv":"Volea de revés", "Ov":"Volea alta", "O":"Smash / overhead", "S":"Smash", "Sw":"Swinging volley", "Sl":"Slice", "Dr":"Dejada", "Lo":"Globo", "L":"Globo", "P":"Passing shot", "Net":"Juego en la red", "R":"Resto", "U":"Globo defensivo", "Z":"Dejada", "K":"Slice de revés"}

# Letters exluded to avoid only letters being in the axis
UNKNOWN_SHOT_CODES = ["J", "K", "Y", "H", "Hv", "I", "M", "T"]
PUBLIC_SHOT_CODES = ["O", "Ov", "V", "Vo", "Sw", "Net", "Dr", "Z", "P", "U", "Lo", "L", "Fside", "Bside", "Fgs", "Bgs", "F", "B", "Sl"]
SURFACE_PALETTE = {"Hard": BLUE, "Clay": ORANGE, "Grass": GREEN, "Carpet": PURPLE, "Unknown": "#95a5a6"}
RALLY_ORDER = ["1-3", "4-6", "7-9", ">9"]

# dynamic ETL
def _filter_df(df, year_filter="2022-2025", surface_filter="Todas"):
    d = df.copy()
    if year_filter != "2022-2025" and "year" in d.columns:
        d = d[d["year"] == int(year_filter)]
    if surface_filter != "Todas" and "Surface" in d.columns:
        d = d[d["Surface"] == surface_filter]
    return d

def build_player_metrics(year_filter="2022-2025", surface_filter="Todas"):
    d = _filter_df(overview, year_filter, surface_filter)
    if len(d) == 0:
        return pd.DataFrame()
    agg = d.groupby("player", as_index=False).agg(
        matches=("match_id", "nunique"),
        serve_pts=("serve_pts", "sum"), aces=("aces", "sum"), dfs=("dfs", "sum"),
        first_in=("first_in", "sum"), first_won=("first_won", "sum"),
        second_in=("second_in", "sum"), second_won=("second_won", "sum"),
        bk_pts=("bk_pts", "sum"), bp_saved=("bp_saved", "sum"),
        return_pts=("return_pts", "sum"), return_pts_won=("return_pts_won", "sum"),
        winners=("winners", "sum"), unforced=("unforced", "sum"),
    )
    agg["first_won_pct"] = agg["first_won"] / agg["first_in"].replace(0, np.nan)
    agg["second_won_pct"] = agg["second_won"] / agg["second_in"].replace(0, np.nan)
    agg["return_won_pct"] = agg["return_pts_won"] / agg["return_pts"].replace(0, np.nan)
    agg["bp_saved_pct"] = agg["bp_saved"] / agg["bk_pts"].replace(0, np.nan)
    agg["winner_ue_ratio"] = agg["winners"] / agg["unforced"].replace(0, np.nan)

    n = _filter_df(net_all, year_filter, surface_filter)
    n = n[n["row"].astype(str).str.lower().eq("netpoints")]
    if len(n):
        ng = n.groupby("player", as_index=False).agg(net_pts=("net_pts", "sum"), net_pts_won=("pts_won", "sum"))
        ng["net_won_pct"] = ng["net_pts_won"] / ng["net_pts"].replace(0, np.nan)
        agg = agg.merge(ng[["player", "net_won_pct", "net_pts"]], on="player", how="left")
    else:
        agg["net_won_pct"] = np.nan
        agg["net_pts"] = np.nan

    r = _filter_df(rally_all, year_filter, surface_filter)
    r = r[r["row"].astype(str).isin(["10", "10+", ">9"])]
    if len(r):
        rg = r.groupby("player", as_index=False).agg(long_rally_pts=("pts", "sum"), long_rally_won=("pts_won", "sum"))
        rg["long_rally_won_pct"] = rg["long_rally_won"] / rg["long_rally_pts"].replace(0, np.nan)
        agg = agg.merge(rg[["player", "long_rally_won_pct", "long_rally_pts"]], on="player", how="left")
    else:
        agg["long_rally_won_pct"] = np.nan
        agg["long_rally_pts"] = np.nan
    return agg

def percentile_score(series, value):
    s = pd.to_numeric(series, errors="coerce").dropna()
    if len(s) == 0 or pd.isna(value): return np.nan
    return float((s <= value).mean() * 100)

def build_rally_segments(year_filter="2022-2025", surface_filter="Todas"):
    d = _filter_df(rally_all, year_filter, surface_filter)
    d = d[d["row"].astype(str).isin(["1-3", "4-6", "7-9", "10", "10+", ">9"])].copy()
    d["rally_length"] = d["row"].astype(str).replace({"10": ">9", "10+": ">9"})
    g = d.groupby(["player", "rally_length"], as_index=False).agg(pts=("pts", "sum"), pts_won=("pts_won", "sum"))
    g["pts_won_pct"] = g["pts_won"] / g["pts"].replace(0, np.nan)
    g["rally_length"] = pd.Categorical(g["rally_length"], categories=RALLY_ORDER, ordered=True)
    return g.sort_values(["rally_length", "player"])

# ATP Ranking
def ensure_photo_url_column(df):
    df = df.copy()
    if "photo_url" not in df.columns: df["photo_url"] = ""
    df["photo_url"] = df.apply(lambda r: r["photo_url"] if str(r.get("photo_url", "")).strip() else get_player_photo(r.get("player", "")), axis=1)
    return df

def _clean_points(x):
    return pd.to_numeric(str(x).replace(",", "").replace(" ", ""), errors="coerce")

def _clean_rank(x):
    return pd.to_numeric(re.sub(r"[^0-9]", "", str(x)), errors="coerce")

@st.cache_data(show_spinner=True, ttl=60*60*12)
def load_atp_year_end_top100(year):
    rank_date = YEAR_END_RANKING_DATES[int(year)]
    url = f"{ATP_RANKINGS_URL}?rankDate={rank_date}&countryCode=all&rankRange=1-100"
    headers = {"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9,es;q=0.8"}
    try:
        response = requests.get(url, headers=headers, timeout=18)
        response.raise_for_status()
        html = response.text
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        for tr in soup.select("tr"):
            player_tag = tr.select_one("td.player-cell a, .player-cell a")
            rank_cell = tr.select_one("td.rank-cell, .rank-cell")
            points_cell = tr.select_one("td.points-cell, .points-cell")
            country_tag = tr.select_one("td.country-cell img, .country-cell img")
            age_cell = tr.select_one("td.age-cell, .age-cell")
            if not player_tag: continue
            cells = [c.get_text(" ", strip=True) for c in tr.find_all("td")]
            player = player_tag.get_text(" ", strip=True)
            rank = _clean_rank(rank_cell.get_text(" ", strip=True) if rank_cell else (cells[0] if cells else ""))
            pts = _clean_points(points_cell.get_text(" ", strip=True) if points_cell else (cells[-1] if cells else ""))
            country = (country_tag.get("alt") or country_tag.get("title") or "") if country_tag else ""
            age = age_cell.get_text(" ", strip=True) if age_cell else ""
            if pd.notna(rank) and pd.notna(pts) and player:
                rows.append({"year": int(year), "ranking_date": rank_date, "rank": int(rank), "player": player, "country": country, "age": age, "points": int(pts), "source": "ATP Tour official ranking archive", "ranking_url": url})
        if len(rows) >= 50:
            df = pd.DataFrame(rows).drop_duplicates(subset=["rank", "player"])
            df = df[df["rank"] <= 100].sort_values("rank").head(100)
            return ensure_photo_url_column(df)
        # respaldo por tablas HTML
        for t in pd.read_html(StringIO(html)):
            cols = [str(c).lower() for c in t.columns]
            if any("player" in c for c in cols) and any("point" in c for c in cols):
                df = t.copy()
                rename = {}
                for c in df.columns:
                    cl = str(c).lower()
                    if "rank" in cl: rename[c] = "rank"
                    elif "player" in cl: rename[c] = "player"
                    elif "age" in cl: rename[c] = "age"
                    elif "point" in cl: rename[c] = "points"
                    elif "country" in cl or "nation" in cl: rename[c] = "country"
                df = df.rename(columns=rename)
                keep = [c for c in ["rank", "player", "country", "age", "points"] if c in df.columns]
                df = df[keep].copy()
                df["year"] = int(year); df["ranking_date"] = rank_date
                df["rank"] = df["rank"].map(_clean_rank); df["points"] = df["points"].map(_clean_points)
                if "country" not in df.columns: df["country"] = ""
                if "age" not in df.columns: df["age"] = ""
                df = df.dropna(subset=["rank", "player", "points"])
                df = df[df["rank"] <= 100].sort_values("rank").head(100)
                if len(df) >= 50:
                    df["rank"] = df["rank"].astype(int); df["points"] = df["points"].astype(int)
                    df["source"] = "ATP Tour official ranking archive"; df["ranking_url"] = url
                    return ensure_photo_url_column(df)
    except Exception:
        pass
    df = rankings_fallback.copy()
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["rank"] = pd.to_numeric(df["rank"], errors="coerce")
    df["points"] = pd.to_numeric(df["points"], errors="coerce")
    df = df[(df["year"] == int(year)) & (df["rank"] <= 100)].sort_values("rank").head(100)
    df["ranking_date"] = rank_date; df["age"] = ""; df["source"] = "CSV local de respaldo incluido en el proyecto"; df["ranking_url"] = url
    return ensure_photo_url_column(df)

# Visual components
def render_featured_player_cards(df, cards_per_row=4):
    if df is None or len(df) == 0:
        st.info("No hay jugadores disponibles para mostrar."); return
    df = df.copy().head(12)
    for start in range(0, len(df), cards_per_row):
        cols = st.columns(cards_per_row)
        for col, (_, row) in zip(cols, df.iloc[start:start+cards_per_row].iterrows()):
            player = row.get("player", "")
            al = is_alcaraz(player)
            photo = row.get("photo_url", "") or get_player_photo(player)
            try: points_text = f"{int(float(row.get('points', 0))):,} pts"
            except Exception: points_text = ""
            try: rank_text = f"#{int(float(row.get('rank', 0)))}"
            except Exception: rank_text = "#-"
            with col:
                st.markdown(f"""
                <div class="featured-card {'featured-card-alcaraz' if al else ''}">
                    <img src="{photo}" class="featured-photo {'featured-photo-alcaraz' if al else ''}">
                    <div class="featured-rank">Ranking {rank_text}</div>
                    <div class="featured-name {'featured-name-alcaraz' if al else ''}">{player}</div>
                    <div class="featured-country">{row.get('country','')}</div>
                    <div class="featured-points {'featured-points-alcaraz' if al else ''}">{points_text}</div>
                </div>
                """, unsafe_allow_html=True)

def render_box_with_points(data, x, y, selected_players, title, y_title=None, x_title=None, pct_axis=False):
    fig = px.box(data, x=x, y=y, points=False, color=x if x in data.columns else None, color_discrete_map=SURFACE_PALETTE, title=title)
    pts = data[data["player"].isin(selected_players)].copy()
    if len(pts):
        fig.add_trace(go.Scatter(
            x=pts[x], y=pts[y], mode="markers+text", text=pts["player"], textposition="top center",
            marker=dict(size=13, color=[ALCARAZ_RED if is_alcaraz(p) else BLUE for p in pts["player"]], line=dict(color="white", width=1.2)),
            name="Jugador seleccionado"
        ))
    if pct_axis: fig.update_yaxes(tickformat=".0%")
    fig.update_layout(yaxis_title=y_title or y, xaxis_title=x_title or x)
    return apply_dark_layout(fig)


def leader_card(title, player, value, note="", icon="🏅"):
    al = is_alcaraz(player)
    photo = get_player_photo(player)
    border = ALCARAZ_RED if al else "rgba(255,255,255,0.10)"
    name_color = ALCARAZ_RED if al else TEXT
    st.markdown(f"""
    <div class="info-card" style="text-align:center;border-color:{border};min-height:205px;">
      <img src="{photo}" style="width:72px;height:72px;border-radius:999px;object-fit:cover;border:2px solid {border};">
      <div class="small-muted" style="margin-top:.45rem;">{icon} {title}</div>
      <div style="font-size:1.02rem;font-weight:900;color:{name_color};">{player}</div>
      <div style="font-size:1.35rem;font-weight:900;margin-top:.25rem;">{value}</div>
      <div class="small-muted">{note}</div>
    </div>
    """, unsafe_allow_html=True)


def render_alcaraz_hero_records():
    """Bloque superior de records: debe ser lo primero que se ve en la pestaña Carlos Alcaraz."""
    titles = alcaraz_titles.copy()
    total_titles = int(len(titles))
    grand_slams = int((titles["level"].astype(str).str.lower() == "grand slam").sum())
    masters_1000 = int(titles["level"].astype(str).str.contains("Masters 1000", case=False, na=False).sum())
    atp_500 = int(titles["level"].astype(str).str.contains("500", case=False, na=False).sum())
    atp_250 = int(titles["level"].astype(str).str.contains("250", case=False, na=False).sum())

    c_photo, c_info = st.columns([1.1, 3.9])
    with c_photo:
        alcaraz_photo = get_player_photo(ALCARAZ)
        st.markdown(f"""
        <div style="text-align:center;">
          <img src="{alcaraz_photo}" style="width:190px;height:190px;border-radius:999px;object-fit:cover;border:4px solid {ALCARAZ_RED};box-shadow:0 0 34px rgba(255,59,48,.32);">
        </div>
        """, unsafe_allow_html=True)
    with c_info:
        st.markdown(f"""
        <div class="hero-card">
            <div class="hero-title">Carlos Alcaraz 🇪🇸</div>
            <div class="hero-subtitle">Perfil de rendimiento y palmarés 2022-2025 · Análisis de juego ATP</div>
            <div style="margin-top:.7rem;color:{MUTED};">
                Diestro · Revés a dos manos · Nacido el 5 de mayo de 2003 · España
            </div>
            <div class="alcaraz-note" style="margin-top:.9rem;">
                ⭐ Más joven No. 1 ATP de la historia · Primera semana como No. 1: 12 septiembre 2022
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("### Records principales al cierre del periodo 2022-2025")
    k1,k2,k3,k4,k5 = st.columns(5)
    with k1: metric_card("Grand Slams", grand_slams, "US Open, Wimbledon, Roland Garros", "🏆")
    with k2: metric_card("Masters 1000", masters_1000, "títulos ATP Masters 1000", "⭐")
    with k3: metric_card("ATP 500", atp_500, "títulos ATP 500", "🔥")
    with k4: metric_card("ATP 250", atp_250, "títulos ATP 250", "🎾")
    with k5: metric_card("Títulos totales", total_titles, "2022-2025", "🥇")

    h1,h2,h3,h4 = st.columns(4)
    with h1: metric_card("Primera vez No. 1", "12 sept. 2022", "tras ganar US Open", "👑")
    with h2: metric_card("Más joven No. 1", "19 años", "ATP Rankings", "🚀")
    with h3: metric_card("Mejor ranking", "#1", "ATP singles", "📈")
    with h4: metric_card("Cierre No. 1", "2022 y 2025", "ranking anual", "🏁")

    st.markdown("### Palmarés agregado por categoría")
    cat = titles.groupby("level", as_index=False).size().rename(columns={"size":"Títulos"}).sort_values("Títulos", ascending=False)
    fig = px.bar(cat, x="level", y="Títulos", text="Títulos", title="Títulos de Carlos Alcaraz por categoría (2022-2025)")
    fig.update_traces(textposition="outside")
    fig.update_layout(xaxis_title="Categoría", yaxis_title="Número de títulos")
    apply_dark_layout(fig, height=420)
    st.plotly_chart(fig, use_container_width=True)

def aggregate_player_metrics(base_df):
    if base_df is None or len(base_df) == 0:
        return pd.DataFrame()
    agg = base_df.groupby("player", as_index=False).agg(
        matches=("match_id", "nunique"), serve_pts=("serve_pts", "sum"), aces=("aces", "sum"), dfs=("dfs", "sum"),
        first_in=("first_in", "sum"), first_won=("first_won", "sum"), second_in=("second_in", "sum"), second_won=("second_won", "sum"),
        bk_pts=("bk_pts", "sum"), bp_saved=("bp_saved", "sum"), return_pts=("return_pts", "sum"), return_pts_won=("return_pts_won", "sum"),
        winners=("winners", "sum"), unforced=("unforced", "sum")
    )
    agg["first_won_pct"] = agg["first_won"] / agg["first_in"].replace(0, np.nan)
    agg["second_won_pct"] = agg["second_won"] / agg["second_in"].replace(0, np.nan)
    agg["return_won_pct"] = agg["return_pts_won"] / agg["return_pts"].replace(0, np.nan)
    agg["bp_saved_pct"] = agg["bp_saved"] / agg["bk_pts"].replace(0, np.nan)
    agg["winner_ue_ratio"] = agg["winners"] / agg["unforced"].replace(0, np.nan)
    return agg

def gs_aggregate(df):
    slams = ["Australian Open", "Roland Garros", "Wimbledon", "US Open"]
    d = df[df["Tournament"].isin(slams)].copy()
    g = d.groupby(["year", "Tournament", "Surface"], as_index=False).agg(
        matches=("match_id", "nunique"), serve_pts=("serve_pts", "sum"), aces=("aces", "sum"),
        first_in=("first_in", "sum"), first_won=("first_won", "sum"), second_in=("second_in", "sum"), second_won=("second_won", "sum"),
        return_pts=("return_pts", "sum"), return_pts_won=("return_pts_won", "sum"),
        winners=("winners", "sum"), unforced=("unforced", "sum"), bk_pts=("bk_pts", "sum"), bp_saved=("bp_saved", "sum")
    )
    g["first_won_pct"] = g["first_won"] / g["first_in"].replace(0, np.nan)
    g["second_won_pct"] = g["second_won"] / g["second_in"].replace(0, np.nan)
    g["return_won_pct"] = g["return_pts_won"] / g["return_pts"].replace(0, np.nan)
    g["bp_saved_pct"] = g["bp_saved"] / g["bk_pts"].replace(0, np.nan)
    g["winner_ue_ratio"] = g["winners"] / g["unforced"].replace(0, np.nan)
    return g



def gs_aggregate_total(df):
    """Agregado 2022-2025 por Grand Slam para la tabla resumen."""
    slams = ["Australian Open", "Roland Garros", "Wimbledon", "US Open"]
    d = df[df["Tournament"].isin(slams)].copy()
    if len(d) == 0:
        return pd.DataFrame()
    g = d.groupby(["Tournament", "Surface"], as_index=False).agg(
        matches=("match_id", "nunique"), serve_pts=("serve_pts", "sum"), aces=("aces", "sum"),
        first_in=("first_in", "sum"), first_won=("first_won", "sum"),
        second_in=("second_in", "sum"), second_won=("second_won", "sum"),
        return_pts=("return_pts", "sum"), return_pts_won=("return_pts_won", "sum"),
        winners=("winners", "sum"), unforced=("unforced", "sum"),
        bk_pts=("bk_pts", "sum"), bp_saved=("bp_saved", "sum")
    )
    g["first_won_pct"] = g["first_won"] / g["first_in"].replace(0, np.nan)
    g["second_won_pct"] = g["second_won"] / g["second_in"].replace(0, np.nan)
    g["return_won_pct"] = g["return_pts_won"] / g["return_pts"].replace(0, np.nan)
    g["bp_saved_pct"] = g["bp_saved"] / g["bk_pts"].replace(0, np.nan)
    g["winner_ue_ratio"] = g["winners"] / g["unforced"].replace(0, np.nan)
    title_counts = alcaraz_titles[alcaraz_titles["grand_slam"] == True].groupby("tournament", as_index=False).size().rename(columns={"tournament":"Tournament", "size":"Títulos"})
    g = g.merge(title_counts, on="Tournament", how="left")
    g["Títulos"] = g["Títulos"].fillna(0).astype(int)
    order = {name: i for i, name in enumerate(slams)}
    g["_order"] = g["Tournament"].map(order)
    return g.sort_values("_order").drop(columns="_order")

def friendly_gs_table(df):
    """Renombra columnas técnicas a etiquetas claras para mostrar en Streamlit."""
    if df is None or len(df) == 0:
        return pd.DataFrame()
    cols = [c for c in ["Tournament", "Surface", "matches", "first_won_pct", "second_won_pct", "return_won_pct", "bp_saved_pct", "winner_ue_ratio", "Títulos"] if c in df.columns]
    out = df[cols].copy()
    rename = {
        "Tournament": "Grand Slam",
        "Surface": "Superficie",
        "matches": "Partidos",
        "first_won_pct": "% 1er saque",
        "second_won_pct": "% 2º saque",
        "return_won_pct": "% al resto",
        "bp_saved_pct": "% BP salvados",
        "winner_ue_ratio": "Winner/UE",
    }
    out = out.rename(columns=rename)
    return out

def show_metric_formula_block():
    st.markdown("""
    <div class='info-card'>
    <b>Fórmulas utilizadas en las métricas de Grand Slam</b><br><br>
    <b>% 1er saque</b> = (puntos ganados con primer servicio / total de puntos jugados con primer servicio) × 100<br>
    <b>% 2º saque</b> = (puntos ganados con segundo servicio / total de puntos jugados con segundo servicio) × 100<br>
    <b>% al resto</b> = (puntos ganados restando / total de puntos restados) × 100<br>
    <b>% BP salvados</b> = (break points salvados / break points enfrentados) × 100<br>
    <b>Winner/UE</b> = winners / errores no forzados<br><br>
    <span class='small-muted'>Los porcentajes se muestran en escala 0-100%. El ratio Winner/UE es mejor cuando es superior a 1, porque indica más winners que errores no forzados.</span>
    </div>
    """, unsafe_allow_html=True)

def add_alcaraz_point_to_box(fig, y_value, label="Carlos Alcaraz"):
    """Añade el punto rojo exactamente sobre la misma categoría del boxplot."""
    if pd.isna(y_value):
        return fig
    fig.add_trace(go.Scatter(
        x=["Top 100 ATP"],
        y=[float(y_value)],
        mode="markers+text",
        text=[label],
        textposition="top center",
        marker=dict(size=17, color=ALCARAZ_RED, line=dict(color="white", width=1.5)),
        hovertemplate=f"{label}<br>Valor=%{{y:.2f}}<extra></extra>",
        showlegend=False,
    ))
    fig.update_xaxes(type="category", categoryorder="array", categoryarray=["Top 100 ATP"], title="Distribución Top 100 ATP")
    fig.update_layout(showlegend=False)
    return fig

# Sidebar
st.sidebar.markdown("""
<div style='padding: 10px 0 18px 0;'>
  <div style='font-size:1.55rem;font-weight:900;'>🎾 ATP ANALYTICS</div>
  <div style='color:#b7c2d0;font-weight:600;'>Top 100 · 2022-2025</div>
</div>
""", unsafe_allow_html=True)
st.sidebar.markdown("---")

section = st.sidebar.radio("Navegación", ["Inicio", "Dashboard ATP", "Carlos Alcaraz", "Comparador ATP", "Ranking ATP cierre de año", "Metodología y fuentes"])
st.sidebar.markdown("---")
st.sidebar.markdown(f"<div class='alcaraz-note'>🔴 <b>Carlos Alcaraz</b> se resalta en rojo cuando aparece comparado con otros jugadores.</div>", unsafe_allow_html=True)

st.markdown("""
<div class="hero-card">
    <div class="hero-title">TFM: ATP Top 100 Analytics Platform with an enfasis on Carlos Alcaraz.</div>
    <div class="hero-subtitle">Plataforma web de análisis de juego ATP 2022-2025 con énfasis en Carlos Alcaraz.</div>
</div>
""", unsafe_allow_html=True)
st.write("")

# Inicio
if section == "Inicio":
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: metric_card("Partidos", f"{int(summary['matches_2022_2025']):,}", "2022-2025", "🎾")
    with c2: metric_card("Jugadores", f"{int(summary['players_with_overview_stats']):,}", "con estadísticas", "👤")
    with c3: metric_card("Partidos Alcaraz", f"{int(summary['alcaraz_matches']):,}", "caso de estudio", "🔴")
    with c4: metric_card("Puntos", f"{int(summary['point_rows_2022_2025']):,}", "procesados", "📊")
    with c5: metric_card("Temporadas", "4", "2022-2025", "📅")

    st.subheader("Objetivo del proyecto")
    st.markdown("""
    <div class="info-card">
    Desarrollar una herramienta web interactiva que permita analizar patrones de juego del circuito ATP, comparar jugadores del Top 100 y profundizar en el perfil táctico de Carlos Alcaraz. La aplicación integra ETL, visualización, métricas de servicio/resto, rallies, golpes y ranking ATP de cierre anual.
    </div>
    """, unsafe_allow_html=True)

    st.subheader("Jugadores destacados")
    featured = load_atp_year_end_top100(2025).sort_values("rank").head(8)
    render_featured_player_cards(featured, cards_per_row=4)

    st.subheader("Qué contiene la herramienta")
    a,b,c = st.columns(3)
    with a: st.markdown("<div class='info-card'><b>Dashboard ATP</b><br>Líderes 2025, tendencias, superficies, correlaciones y un único box plot.</div>", unsafe_allow_html=True)
    with b: st.markdown("<div class='info-card'><b>Carlos Alcaraz</b><br>Rallies, superficies, golpes efectivos y comparación contra el circuito.</div>", unsafe_allow_html=True)
    with c: st.markdown("<div class='info-card'><b>Comparador ATP</b><br>Cualquier jugador vs cualquier jugador, con percentiles Top 100.</div>", unsafe_allow_html=True)

# Dashboard ATP
elif section == "Dashboard ATP":
    st.subheader("Dashboard ATP - resumen ejecutivo Top 100")

    min_matches = st.slider("Mínimo de partidos para incluir jugador", 3, 60, 12, step=1)
    pmetrics = players_base[players_base["matches"] >= min_matches].copy()

    c1, c2, c3, c4 = st.columns(4)
    with c1: metric_card("Jugadores incluidos", f"{len(pmetrics):,}", f"mín. {min_matches} partidos", "👥")
    with c2: metric_card("Winner/UE medio", f"{pmetrics['winner_ue_ratio'].mean():.2f}", "Top 100 charted", "🔥")
    with c3: metric_card("1er saque ganado", f"{pmetrics['first_won_pct'].mean():.1%}", "media muestra", "🎯")
    with c4: metric_card("Puntos al resto", f"{pmetrics['return_won_pct'].mean():.1%}", "media muestra", "↩️")

    st.subheader("Líderes Top 100 ATP 2025")
    st.caption("Resumen del Top 100 al 2025: derecha, revés, drop shot, aces, primer saque, resto, Winner/UE y red. Las fichas usan fotos locales/cacheadas.")
    ov25 = overview[(overview["year"] == 2025)].copy()
    metr25 = aggregate_player_metrics(ov25)
    metr25 = metr25[metr25["matches"] >= 3].copy()
    shots25 = shot_types_all[shot_types_all["year"] == 2025].copy()
    shots25 = shots25.groupby(["player", "row"], as_index=False).agg(shots=("shots", "sum"), winners=("winners", "sum"))
    shots25["winner_per_100_shots"] = shots25["winners"] / shots25["shots"].replace(0, np.nan) * 100
    net25 = net_all[(net_all["year"] == 2025) & (net_all["row"].astype(str).str.lower().eq("netpoints"))].copy()
    net25 = net25.groupby("player", as_index=False).agg(net_pts=("net_pts", "sum"), net_pts_won=("pts_won", "sum"))
    net25["net_won_pct"] = net25["net_pts_won"] / net25["net_pts"].replace(0, np.nan)

    def shot_leader(rows, min_shots=120):
        d = shots25[(shots25["row"].isin(rows)) & (shots25["shots"] >= min_shots)].sort_values("winner_per_100_shots", ascending=False)
        return d.iloc[0] if len(d) else None

    leaders = []
    fh = shot_leader(["Fside", "Fgs", "F"]); bh = shot_leader(["Bside", "Bgs", "B"]); dr = shot_leader(["Dr", "Z"], min_shots=25)
    if fh is not None: leaders.append(("Efectividad derecha", fh.player, f"{fh.winner_per_100_shots:.1f}", "winners / 100 golpes", "💪"))
    if bh is not None: leaders.append(("Efectividad revés", bh.player, f"{bh.winner_per_100_shots:.1f}", "winners / 100 golpes", "🎯"))
    if dr is not None: leaders.append(("Efectividad drop shot", dr.player, f"{dr.winner_per_100_shots:.1f}", "winners / 100 golpes", "🪄"))
    if len(metr25):
        r = metr25.sort_values("aces", ascending=False).iloc[0]; leaders.append(("Mayor número de aces", r.player, f"{int(r.aces):,}", "aces charted 2025", "🚀"))
        r = metr25.dropna(subset=["first_won_pct"]).sort_values("first_won_pct", ascending=False).iloc[0]; leaders.append(("Mejor 1er saque", r.player, f"{r.first_won_pct:.1%}", "puntos ganados", "🥇"))
        r = metr25.dropna(subset=["return_won_pct"]).sort_values("return_won_pct", ascending=False).iloc[0]; leaders.append(("Mejor rendimiento al resto", r.player, f"{r.return_won_pct:.1%}", "puntos ganados", "↩️"))
        r = metr25.dropna(subset=["winner_ue_ratio"]).sort_values("winner_ue_ratio", ascending=False).iloc[0]; leaders.append(("Mejor Winner/UE", r.player, f"{r.winner_ue_ratio:.2f}", "winners / ENF", "🔥"))
    if len(net25):
        net_eligible = net25[net25["net_pts"] >= 20].dropna(subset=["net_won_pct"])
        if len(net_eligible):
            r = net_eligible.sort_values("net_won_pct", ascending=False).iloc[0]
            leaders.append(("Mejor juego en la red", r.player, f"{r.net_won_pct:.1%}", "net points won", "🕸️"))
    for i in range(0, len(leaders), 4):
        cols = st.columns(4)
        for col, item in zip(cols, leaders[i:i+4]):
            with col: leader_card(*item)

    st.subheader("Ranking visual de líderes: Winner/UE Ratio")
    top_ratio = pmetrics.dropna(subset=["winner_ue_ratio"]).sort_values("winner_ue_ratio", ascending=False).head(10).sort_values("winner_ue_ratio")
    fig = go.Figure(go.Bar(
        x=top_ratio["winner_ue_ratio"],
        y=top_ratio["player"],
        orientation="h",
        marker_color=color_list_by_player(top_ratio["player"]),
        text=[f"{v:.2f}" for v in top_ratio["winner_ue_ratio"]],
        textposition="outside",
        hovertemplate="Jugador=%{y}<br>Winner/UE=%{x:.2f}<extra></extra>"
    ))
    fig.update_layout(title="Top 10 jugadores por Winner/UE Ratio", xaxis_title="Winner/UE Ratio", yaxis_title="Jugador")
    apply_dark_layout(fig, height=520)
    st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Distribución de partidos por superficie")
    
        superficies_validas = ["Hard", "Clay", "Grass"]
    
        surf_matches = matches.dropna(subset=["year", "Surface"]).copy()
        surf_matches["Surface"] = surf_matches["Surface"].astype(str).str.strip()
        surf_matches = surf_matches[surf_matches["Surface"].isin(superficies_validas)]
    
        surf_matches["year"] = surf_matches["year"].astype(int)
    
        surf = (
            surf_matches
            .groupby(["year", "Surface"], as_index=False)
            .agg(partidos=("match_id", "nunique"))
        )
        fig = px.bar(surf, x="year", y="partidos", color="Surface", barmode="stack", color_discrete_map=SURFACE_PALETTE, title="Partidos charted por superficie y año")
        fig.update_layout(xaxis_title="Año", yaxis_title="Número de partidos")
        fig.update_xaxes(tickmode="array", tickvals=[2022, 2023, 2024, 2025], ticktext=["2022", "2023", "2024", "2025"])
        apply_dark_layout(fig, height=500)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.subheader("Tendencia anual Top 100")
        year_player = overview.groupby(["year", "player"], as_index=False).agg(
            matches=("match_id", "nunique"), first_in=("first_in", "sum"), first_won=("first_won", "sum"), return_pts=("return_pts", "sum"), return_pts_won=("return_pts_won", "sum"), winners=("winners", "sum"), unforced=("unforced", "sum")
        )
        year_player["first_won_pct"] = year_player["first_won"] / year_player["first_in"].replace(0, np.nan)
        year_player["return_won_pct"] = year_player["return_pts_won"] / year_player["return_pts"].replace(0, np.nan)
        year_player["winner_ue_ratio"] = year_player["winners"] / year_player["unforced"].replace(0, np.nan)
        trend = year_player[year_player["matches"] >= 3].groupby("year", as_index=False).agg(
            first_won_pct=("first_won_pct", "mean"), return_won_pct=("return_won_pct", "mean"), winner_ue_ratio=("winner_ue_ratio", "mean")
        )
        trend_long = trend.melt(id_vars="year", value_vars=["first_won_pct", "return_won_pct"], var_name="metric", value_name="value")
        trend_long["Métrica"] = trend_long["metric"].map(METRIC_LABELS)
        fig = px.line(trend_long, x="year", y="value", color="Métrica", markers=True, title="Evolución media de porcentajes clave")
        fig.update_yaxes(tickformat=".0%", title="Porcentaje medio")
        fig.update_xaxes(title="Año", tickmode="array", tickvals=[2022, 2023, 2024, 2025], ticktext=["2022", "2023", "2024", "2025"], dtick=1)
        apply_dark_layout(fig, height=500)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("% puntos ganados con primer servicio")
    st.caption("La caja representa la distribución del Top 100; el punto rojo sitúa a Carlos Alcaraz.")
    box_df = pmetrics.dropna(subset=["first_won_pct"]).copy()
    box_df["Grupo"] = "Top 100 ATP"
    fig = px.box(box_df, x="Grupo", y="first_won_pct", points="outliers", title="Distribución Top 100: puntos ganados con 1er saque")
    al_val = box_df.loc[box_df["player"].apply(is_alcaraz), "first_won_pct"]
    if len(al_val):
        fig = add_alcaraz_point_to_box(fig, al_val.iloc[0])
    fig.update_yaxes(tickformat=".0%", title="% puntos ganados con 1er saque")
    apply_dark_layout(fig, height=520)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Heatmap de correlaciones")
    corr_cols = ["first_won_pct", "second_won_pct", "return_won_pct", "bp_saved_pct", "winner_ue_ratio"]
    cm = pmetrics[corr_cols].corr()
    fig = px.imshow(cm, text_auto=".2f", color_continuous_scale="RdBu", zmin=-1, zmax=1, title="Correlación entre métricas de rendimiento")
    fig.update_xaxes(ticktext=[METRIC_LABELS[c] for c in corr_cols], tickvals=list(range(len(corr_cols))), title="Métrica")
    fig.update_yaxes(ticktext=[METRIC_LABELS[c] for c in corr_cols], tickvals=list(range(len(corr_cols))), title="Métrica")
    apply_dark_layout(fig, height=600)
    st.plotly_chart(fig, use_container_width=True)

# Carlos Alcaraz
elif section == "Carlos Alcaraz":
    st.subheader("Carlos Alcaraz - records, palmarés y análisis táctico")

    render_alcaraz_hero_records()

    st.subheader("Récord anual 2022-2025")
    cols = st.columns(4)
    for col, (_, row) in zip(cols, alcaraz_records.iterrows()):
        with col:
            metric_card(str(int(row["year"])), row["record"], f"{row['win_pct']:.1%} · {int(row['titles'])} títulos · cierre #{int(row['year_end_rank'])}", "📅")

    st.markdown("### Grand Slams ganados")
    gs = alcaraz_titles[alcaraz_titles["grand_slam"] == True].copy()
    for i in range(0, len(gs), 4):
        cols = st.columns(4)
        for col, (_, r) in zip(cols, gs.iloc[i:i+4].iterrows()):
            with col:
                surface_color = SURFACE_PALETTE.get(str(r["surface"]).replace(" (indoor)", ""), BLUE)
                st.markdown(f"""
                <div class="info-card" style="border-color:{surface_color};min-height:170px;">
                  <div class="small-muted">🏅 Grand Slam · {int(r['year'])}</div>
                  <div style="font-size:1.25rem;font-weight:900;">{r['tournament']}</div>
                  <div class="small-muted">Final vs {r['final_opponent']}</div>
                  <div style="margin-top:.4rem;font-weight:800;">{r['final_score']}</div>
                  <div class="small-muted">Superficie: {r['surface']}</div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("### Torneos ganados por año")
    for y in [2022, 2023, 2024, 2025]:
        won = alcaraz_titles[alcaraz_titles["year"] == y].copy()
        st.markdown(f"**{y}: {len(won)} títulos**")
        st.dataframe(won[["tournament", "level", "surface", "final_opponent", "final_score"]], use_container_width=True, hide_index=True)

    st.subheader("Australian Open: el Grand Slam pendiente dentro del periodo 2022-2025")
    st.markdown("<div class='info-card'>Hasta el cierre de 2025, Alcaraz había ganado US Open, Wimbledon y Roland Garros, pero no el Australian Open dentro del periodo analizado. Esta sección compara sus métricas en Melbourne con los Grand Slams que sí conquistó para construir una hipótesis táctica basada en datos.</div>", unsafe_allow_html=True)
    c_ao1, c_ao2, c_ao3, c_ao4 = st.columns(4)
    with c_ao1: metric_card("Australian Open", "0 títulos", "periodo 2022-2025", "🇦🇺")
    with c_ao2: metric_card("US Open", "2 títulos", "2022 y 2025", "🇺🇸")
    with c_ao3: metric_card("Wimbledon", "2 títulos", "2023 y 2024", "🇬🇧")
    with c_ao4: metric_card("Roland Garros", "2 títulos", "2024 y 2025", "🇫🇷")
    show_metric_formula_block()
    gs_metrics = gs_aggregate(alcaraz_matches)
    gs_total = gs_aggregate_total(alcaraz_matches)
    gs_order = ["Australian Open", "Roland Garros", "Wimbledon", "US Open"]
    gs_metrics["Tournament"] = pd.Categorical(gs_metrics["Tournament"], categories=gs_order, ordered=True)
    gs_total["Tournament"] = pd.Categorical(gs_total["Tournament"], categories=gs_order, ordered=True)

    st.markdown("### Tabla 1 · Rendimiento acumulado por Grand Slam (2022-2025)")
    total_show = friendly_gs_table(gs_total)
    total_fmt = {"% 1er saque":"{:.1%}", "% 2º saque":"{:.1%}", "% al resto":"{:.1%}", "% BP salvados":"{:.1%}", "Winner/UE":"{:.2f}"}
    st.dataframe(total_show.style.format(total_fmt), use_container_width=True, hide_index=True)

    fig = px.bar(gs_total.sort_values("Tournament"), x="Tournament", y="winner_ue_ratio", color="Tournament", color_discrete_map={"Australian Open": BLUE, "Roland Garros": ORANGE, "Wimbledon": GREEN, "US Open": ALCARAZ_RED}, title="Winner/UE Ratio acumulado por Grand Slam (2022-2025)")
    fig.update_layout(showlegend=False, xaxis_title="Grand Slam", yaxis_title="Winner/UE Ratio")
    apply_dark_layout(fig, height=480); st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Tabla 2 · Comparación anual: Australian Open vs Grand Slams del mismo año")
    year_gs = st.selectbox("Año de comparación", [2022, 2023, 2024, 2025], index=3)
    comp_gs = gs_metrics[gs_metrics["year"] == year_gs].copy()
    if len(comp_gs):
        show = friendly_gs_table(comp_gs)
        st.dataframe(show.style.format(total_fmt), use_container_width=True, hide_index=True)
        mm = comp_gs.melt(id_vars="Tournament", value_vars=["first_won_pct", "second_won_pct", "return_won_pct", "bp_saved_pct", "winner_ue_ratio"], var_name="metric", value_name="value")
        mm["Métrica"] = mm["metric"].map(METRIC_LABELS)
        fig = px.bar(mm, x="Métrica", y="value", color="Tournament", barmode="group", color_discrete_map={"Australian Open": BLUE, "Roland Garros": ORANGE, "Wimbledon": GREEN, "US Open": ALCARAZ_RED}, title=f"AO vs otros Grand Slams: métricas {year_gs}")
        fig.update_layout(xaxis_title="Métrica", yaxis_title="Valor")
        apply_dark_layout(fig); st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay partidos de Grand Slam registrados para este año en el dataset filtrado.")
    st.markdown("""
    <div class='alcaraz-note'>
    <b>Hipótesis analítica:</b> en Melbourne, el margen entre agresividad y error ha sido menos favorable que en los Slams donde Alcaraz ya ganó. Cuando su Winner/UE, eficacia de primer saque y rendimiento al resto aumentan, su perfil se acerca al de US Open, Wimbledon o Roland Garros. Por tanto, el Australian Open aparece como un objetivo pendiente más relacionado con ajuste táctico y gestión de condiciones que con una debilidad estructural.
    </div>
    """, unsafe_allow_html=True)



    st.subheader("Evolución anual de métricas de juego")
    metric_names = {"first_won_pct":"1er servicio ganado", "second_won_pct":"2º servicio ganado", "return_won_pct":"Puntos al resto", "bp_saved_pct":"Break points salvados"}
    al_year_long = al_year.melt(id_vars="year", value_vars=list(metric_names.keys()), var_name="Métrica", value_name="Porcentaje")
    al_year_long["Métrica"] = al_year_long["Métrica"].map(metric_names)
    fig = px.line(al_year_long, x="year", y="Porcentaje", color="Métrica", markers=True, color_discrete_map={"1er servicio ganado": BLUE, "2º servicio ganado": GREEN, "Puntos al resto": ORANGE, "Break points salvados": YELLOW}, title="Carlos Alcaraz: evolución anual de métricas clave")
    fig.update_yaxes(tickformat=".0%", title="Porcentaje")
    fig.update_xaxes(title="Año", tickmode="array", tickvals=[2022, 2023, 2024, 2025], ticktext=["2022", "2023", "2024", "2025"], dtick=1)
    apply_dark_layout(fig)
    st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        fig = px.line(al_surface.sort_values("Surface"), x="Surface", y="winner_ue_ratio", color="Surface", markers=True, color_discrete_map=SURFACE_PALETTE, hover_data=["matches", "winners", "unforced"], title="Winner/UE por superficie")
        apply_dark_layout(fig); st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.markdown("""
        <div class='info-card'>
        <b>Fórmula:</b> Efectividad del golpe = (winners del tipo de golpe / golpes totales de ese tipo) × 100.<br>
        <span class='small-muted'>Periodo: 2022-2025. Se muestran los tipos de golpe más efectivos de Carlos Alcaraz.</span>
        </div>
        """, unsafe_allow_html=True)
        # Se excluyen códigos internos no documentados o ambiguos como "J" para que el gráfico sea defendible.
        shot = al_shots[
            (~al_shots["row"].isin(["Total", "Base", "Gs"] + UNKNOWN_SHOT_CODES))
            & (al_shots["row"].isin(PUBLIC_SHOT_CODES))
        ].copy()
        shot["Tipo de golpe"] = shot["row"].map(SHOT_LABELS).fillna(shot["row"])
        # En caso de que varios códigos correspondan a una misma familia de golpe, se agregan antes de ordenar.
        shot = (
            shot.groupby("Tipo de golpe", as_index=False)
            .agg(shots=("shots", "sum"), winners=("winners", "sum"), unforced=("unforced", "sum"), matches=("matches", "sum"))
        )
        shot["winner_per_100_shots"] = shot["winners"] / shot["shots"].replace(0, np.nan) * 100
        shot = shot.sort_values("winner_per_100_shots", ascending=False).head(10)
        fig = px.bar(shot, x="Tipo de golpe", y="winner_per_100_shots", hover_data={"shots": True, "winners": True, "unforced": True}, title="Carlos Alcaraz: golpes más efectivos (2022-2025)", color="winner_per_100_shots", color_continuous_scale=[BLUE, ORANGE, GREEN])
        fig.update_layout(coloraxis_showscale=False, xaxis_tickangle=-25, xaxis_title="Tipo de golpe", yaxis_title="Winners cada 100 ejecuciones")
        apply_dark_layout(fig); st.plotly_chart(fig, use_container_width=True)

    st.subheader("Rallies: % puntos ganados por longitud y superficie")
    rr = rally_alcaraz[rally_alcaraz["row"].astype(str).isin(["1-3", "4-6", "7-9", "10", "10+", ">9"])].copy()
    rr["rally_length"] = rr["row"].replace({"10": ">9", "10+": ">9"})
    rr = rr.groupby(["Surface", "rally_length"], as_index=False).agg(pts=("pts", "sum"), pts_won=("pts_won", "sum"))
    rr["pts_won_pct"] = rr["pts_won"] / rr["pts"].replace(0, np.nan)
    rr["rally_length"] = pd.Categorical(rr["rally_length"], categories=RALLY_ORDER, ordered=True)
    fig = px.line(rr.sort_values(["Surface", "rally_length"]), x="rally_length", y="pts_won_pct", color="Surface", markers=True, category_orders={"rally_length": RALLY_ORDER}, color_discrete_map=SURFACE_PALETTE, title="Carlos Alcaraz: puntos ganados según longitud del rally")
    fig.update_yaxes(tickformat=".0%", title="% puntos ganados")
    apply_dark_layout(fig); st.plotly_chart(fig, use_container_width=True)

    st.subheader("Winner/UE vs Top 100")
    pmetrics = players_base[players_base["matches"] >= 10].copy()
    box_df = pmetrics.dropna(subset=["winner_ue_ratio"]).copy()
    box_df["Grupo"] = "Top 100 ATP"
    fig = px.box(box_df, x="Grupo", y="winner_ue_ratio", points="outliers", title="Distribución Top 100: Winner/UE Ratio")
    al_val = box_df.loc[box_df["player"].apply(is_alcaraz), "winner_ue_ratio"]
    if len(al_val):
        fig = add_alcaraz_point_to_box(fig, al_val.iloc[0])
    fig.update_yaxes(title="Winner/UE Ratio")
    apply_dark_layout(fig); st.plotly_chart(fig, use_container_width=True)

# Comparador ATP
elif section == "Comparador ATP":
    st.subheader("Comparador ATP - cualquier jugador del Top 100")
    year_filter = st.selectbox("Temporada", ["2022-2025", "2022", "2023", "2024", "2025"], index=0)
    surface_filter = st.selectbox("Superficie", ["Todas", "Hard", "Clay", "Grass"], index=0)
    stats = build_player_metrics(year_filter, surface_filter)
    stats = stats[stats["matches"] >= 3].copy()
    player_options = sorted(stats["player"].dropna().unique())
    if not player_options:
        st.error("No hay datos suficientes para los filtros seleccionados.")
        st.stop()
    idx_a = player_options.index(ALCARAZ) if ALCARAZ in player_options else 0
    player_a = st.selectbox("Jugador A", player_options, index=idx_a)
    idx_b = player_options.index("Jannik Sinner") if "Jannik Sinner" in player_options else min(1, len(player_options)-1)
    player_b = st.selectbox("Jugador B", player_options, index=idx_b)
    selected = [player_a, player_b]
    colors = palette_for(selected)

    comp = stats[stats["player"].isin(selected)].copy()
    show_cols = ["player", "matches", "first_won_pct", "second_won_pct", "return_won_pct", "bp_saved_pct", "winner_ue_ratio", "net_won_pct", "long_rally_won_pct"]
    st.dataframe(comp[show_cols].style.apply(highlight_alcaraz, axis=1).format({c:"{:.1%}" for c in PCT_METRICS if c in show_cols}).format({"winner_ue_ratio":"{:.2f}"}), use_container_width=True, hide_index=True)

    st.subheader("Radar normalizado por percentiles del Top 100")
    radar_metrics = ["first_won_pct", "second_won_pct", "return_won_pct", "bp_saved_pct", "winner_ue_ratio", "long_rally_won_pct", "net_won_pct"]
    fig = go.Figure()
    radar_rows = []
    for _, row in comp.iterrows():
        values = []
        for m in radar_metrics:
            p = percentile_score(stats[m], row.get(m, np.nan))
            values.append(p)
            radar_rows.append({"player": row["player"], "metric": METRIC_LABELS[m], "percentil": p})
        values_closed = values + [values[0]]
        cats = [METRIC_LABELS[m] for m in radar_metrics] + [METRIC_LABELS[radar_metrics[0]]]
        fig.add_trace(go.Scatterpolar(r=values_closed, theta=cats, fill="toself", name=row["player"], line=dict(color=colors[row["player"]]), marker=dict(color=colors[row["player"]])))
    fig.update_layout(polar=dict(bgcolor="rgba(0,0,0,0)", radialaxis=dict(visible=True, range=[0,100], gridcolor="rgba(255,255,255,0.12)")), showlegend=True)
    apply_dark_layout(fig, "Radar 0-100: percentiles frente al Top 100")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Cada eje está normalizado de 0 a 100 usando percentiles de los jugadores disponibles del Top 100 para el filtro seleccionado. Así se evitan comparaciones engañosas entre porcentajes y ratios.")

    st.subheader("Efectividad por tipo de golpe")
    st.markdown("""
    <div class='info-card'>
    <b>Fórmula:</b> Efectividad del golpe = (winners del tipo de golpe / golpes totales de ese tipo) × 100.<br>
    <span class='small-muted'>Sirve para comparar qué golpes generan más winners por volumen de ejecución en cada jugador.</span>
    </div>
    """, unsafe_allow_html=True)
    min_shots = st.slider("Mínimo de golpes por tipo de tiro", 50, 1000, 200, step=50)
    shot_keep = [code for code in PUBLIC_SHOT_CODES if code not in UNKNOWN_SHOT_CODES]
    shots = _filter_df(shot_types_all, year_filter, surface_filter)
    shots = shots[(shots["player"].isin(selected)) & (shots["row"].isin(shot_keep))].copy()
    shots = shots.groupby(["player", "row"], as_index=False).agg(shots=("shots", "sum"), winners=("winners", "sum"), unforced=("unforced", "sum"), matches=("match_id", "nunique"))
    shots = shots[shots["shots"] >= min_shots].copy()
    shots["winner_per_100_shots"] = shots["winners"] / shots["shots"] * 100
    shots["Tipo de golpe"] = shots["row"].map(SHOT_LABELS).fillna(shots["row"])
    if len(shots):
        shots = (
            shots.groupby(["player", "Tipo de golpe"], as_index=False)
            .agg(shots=("shots", "sum"), winners=("winners", "sum"), unforced=("unforced", "sum"), matches=("matches", "sum"))
        )
        shots["winner_per_100_shots"] = shots["winners"] / shots["shots"].replace(0, np.nan) * 100
        order = shots.groupby("Tipo de golpe")["winner_per_100_shots"].mean().sort_values(ascending=False).index.tolist()
        fig = px.bar(shots, x="Tipo de golpe", y="winner_per_100_shots", color="player", barmode="group", text="winner_per_100_shots", category_orders={"Tipo de golpe": order}, color_discrete_map=colors, title="Winners cada 100 ejecuciones por tipo de golpe")
        fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
        fig.update_layout(xaxis_tickangle=-25, yaxis_title="Winners por 100 golpes")
        apply_dark_layout(fig); st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No hay suficientes datos para ese umbral. Baja el mínimo de golpes.")

    st.subheader("Errores no forzados por tipo de golpe")
    st.markdown("""
    <div class='info-card'>
    <b>Fórmula:</b> Errores no forzados cada 100 golpes = (errores no forzados del tipo de golpe / golpes totales de ese tipo) × 100.<br>
    <span class='small-muted'>Se comparan tres familias claras de golpe: derecha, revés y volea. En los datos se usan Fgs para derecha, Bgs para revés y Vo para voleas.</span>
    </div>
    """, unsafe_allow_html=True)
    ue_codes = {"Fgs": "Derecha", "Bgs": "Revés", "Vo": "Volea"}
    ue = _filter_df(shot_types_all, year_filter, surface_filter)
    ue = ue[(ue["player"].isin(selected)) & (ue["row"].isin(ue_codes.keys()))].copy()
    if len(ue):
        ue = (
            ue.groupby(["player", "row"], as_index=False)
            .agg(golpes=("shots", "sum"), errores_no_forzados=("unforced", "sum"), partidos=("match_id", "nunique"))
        )
        ue["Tipo de golpe"] = ue["row"].map(ue_codes)
        ue["Errores no forzados / 100 golpes"] = ue["errores_no_forzados"] / ue["golpes"].replace(0, np.nan) * 100
        order_ue = ["Derecha", "Revés", "Volea"]
        fig = px.bar(
            ue,
            x="Tipo de golpe",
            y="Errores no forzados / 100 golpes",
            color="player",
            barmode="group",
            text="Errores no forzados / 100 golpes",
            category_orders={"Tipo de golpe": order_ue},
            color_discrete_map=colors,
            title="Errores no forzados cada 100 golpes: derecha, revés y volea"
        )
        fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
        fig.update_layout(xaxis_title="Tipo de golpe", yaxis_title="Errores no forzados cada 100 golpes")
        apply_dark_layout(fig)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(
            ue[["player", "Tipo de golpe", "golpes", "errores_no_forzados", "Errores no forzados / 100 golpes"]]
            .rename(columns={"player": "Jugador", "golpes": "Golpes", "errores_no_forzados": "Errores no forzados"})
            .style.apply(highlight_alcaraz, axis=1)
            .format({"Errores no forzados / 100 golpes": "{:.1f}"}),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("No hay datos suficientes de errores no forzados por tipo de golpe para los filtros seleccionados.")

    st.subheader("Winner/UE Ratio")
    st.caption("La caja representa la distribución del Top 100 para el filtro elegido; los puntos muestran a los dos jugadores seleccionados.")
    box_df = stats.dropna(subset=["winner_ue_ratio"]).copy()
    box_df["Grupo"] = "Top 100 ATP"
    fig = px.box(box_df, x="Grupo", y="winner_ue_ratio", points="outliers", title="Distribución Top 100: Winner/UE Ratio")
    sp = stats[stats["player"].isin(selected)].dropna(subset=["winner_ue_ratio"])
    if len(sp):
        fig.add_trace(go.Scatter(
            x=["Top 100 ATP"] * len(sp),
            y=sp["winner_ue_ratio"],
            mode="markers+text",
            text=sp["player"],
            textposition="top center",
            marker=dict(size=14, color=[colors[p] for p in sp["player"]], line=dict(color="white", width=1)),
            showlegend=False
        ))
    fig.update_xaxes(title="Distribución Top 100")
    fig.update_yaxes(title="Winner/UE Ratio")
    apply_dark_layout(fig)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Rallies: línea comparativa por longitud")
    st.caption("No es box plot: compara directamente el % de puntos ganados por longitud de rally para los jugadores seleccionados.")
    rall = build_rally_segments(year_filter, surface_filter)
    sr = rall[(rall["player"].isin(selected)) & (rall["pts"] >= 20)].copy()
    if len(sr):
        fig = px.line(
            sr,
            x="rally_length",
            y="pts_won_pct",
            color="player",
            markers=True,
            category_orders={"rally_length": RALLY_ORDER},
            color_discrete_map=colors,
            title="% puntos ganados por longitud de rally"
        )
        fig.update_yaxes(tickformat=".0%", title="% puntos ganados")
        apply_dark_layout(fig)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay suficientes puntos de rally para comparar con estos filtros.")

    st.subheader("Interpretación automática")
    radar_df = pd.DataFrame(radar_rows)
    if len(radar_df):
        for p in selected:
            topm = radar_df[radar_df["player"] == p].sort_values("percentil", ascending=False).head(2)
            st.markdown(f"<div class='info-card'><b>{p}</b>: destaca en " + ", ".join([f"{r.metric} (P{r.percentil:.0f})" for r in topm.itertuples()]) + ".</div>", unsafe_allow_html=True)

# Ranking ATP
elif section == "Ranking ATP cierre de año":
    st.subheader("Top 100 ATP - Ranking de cierre de temporada")
    selected_year = st.selectbox("Año del ranking", [2022, 2023, 2024, 2025], index=3)
    rank_date = YEAR_END_RANKING_DATES[selected_year]
    ranking_url = f"{ATP_RANKINGS_URL}?rankDate={rank_date}&countryCode=all&rankRange=1-100"
    st.caption(f"Fecha usada para {selected_year}: {rank_date}. Fuente principal: ATP Tour Rankings Archive.")
    st.link_button("Abrir ranking oficial ATP de ese año", ranking_url)
    d = load_atp_year_end_top100(selected_year).copy()
    d["rank"] = pd.to_numeric(d["rank"], errors="coerce"); d["points"] = pd.to_numeric(d["points"], errors="coerce")
    d = d[d["rank"] <= 100].sort_values("rank").head(100)
    c1,c2,c3,c4 = st.columns(4)
    with c1: metric_card("Año", selected_year, "ranking seleccionado", "📅")
    with c2: metric_card("Fecha", rank_date, "cierre anual ATP", "🏁")
    with c3: metric_card("Jugadores", len(d), "Top 100", "👥")
    with c4: metric_card("No. 1 ATP", d.iloc[0]["player"] if len(d) else "-", "líder del ranking", "🏆")
    if len(d) and "source" in d.columns: st.caption(f"Fuente usada por la app: {d.iloc[0]['source']}")
    st.caption("Las fotos se cargan desde assets locales/cacheados; si no existe foto, aparece un avatar generado automáticamente para evitar fichas vacías.")

    st.markdown("### Fichas Top 100")
    for start in range(0, len(d), 4):
        cols = st.columns(4)
        for col, (_, row) in zip(cols, d.iloc[start:start+4].iterrows()):
            al = is_alcaraz(row["player"])
            with col:
                st.markdown(f"<div class='rank-card {'rank-card-alcaraz' if al else ''}'>", unsafe_allow_html=True)
                photo = get_player_photo(row["player"])
                st.markdown(f"<div style='text-align:center;'><img src='{photo}' class='featured-photo {'featured-photo-alcaraz' if al else ''}'></div>", unsafe_allow_html=True)
                st.markdown(f"<div class='rank-name {'rank-name-alcaraz' if al else ''}'>#{int(row['rank'])} {row['player']}</div>", unsafe_allow_html=True)
                if str(row.get("country", "")).strip(): st.markdown(f"<div class='small-muted'>{row.get('country','')}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='metric-value' style='font-size:1.35rem;color:{ALCARAZ_RED if al else TEXT};'>{int(row['points']):,} pts</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("### Tabla completa")
    cols = [c for c in ["rank", "player", "country", "age", "points", "ranking_date"] if c in d.columns]
    st.dataframe(d[cols].style.apply(highlight_alcaraz, axis=1), use_container_width=True, hide_index=True)

# Metodología
else:
    st.subheader("Metodología y fuentes")
    st.markdown(f"""
    <div class="info-card">
    <p><b>Fuentes:</b> Tennis Charting Project de Jeff Sackmann, ATP Tour Rankings Archive y Tennis Abstract como referencia complementaria.</p>
    <p><b>ETL:</b> extracción de CSV, limpieza de fechas, unión con metadatos de partido, agregación por jugador/temporada/superficie y generación de métricas para Streamlit.</p>
    <p><b>Métricas:</b> Winner/UE = winners / errores no forzados. Efectividad por tiro = winners / golpes ejecutados × 100. Radar = percentiles 0-100 frente a todos los jugadores filtrados.</p><p><b>Records y palmarés:</b> capa contextual añadida a partir de ATP Tour, Tennis.com, Reuters y medios deportivos. Se separa de las métricas de juego, que se calculan desde Tennis Charting Project.</p><p><b>Australian Open pendiente dentro del periodo 2022-2025:</b> análisis comparativo de métricas de Alcaraz en Melbourne frente a Roland Garros, Wimbledon y US Open.</p>
    <p><b>Limitación:</b> el análisis de juego se basa en partidos charted disponibles públicamente, no en el universo completo de partidos ATP.</p>
    </div>
    """, unsafe_allow_html=True)
    st.code("python etl/build_processed_data.py\nstreamlit run app/app.py", language="bash")
