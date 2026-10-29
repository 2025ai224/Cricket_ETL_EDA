"""PSL Cricket Analytics - Streamlit dashboard (ETL + EDA academic project)."""

from functools import lru_cache
from pathlib import Path
import base64
import hashlib
import html
import math
import re

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st


# ============================================================
# 1. PAGE SETTINGS
# ============================================================

st.set_page_config(
    page_title="PSL Cricket Analytics",
    page_icon="🏏",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Paths are built from this file's location, so the app works from any terminal folder
SRC_FOLDER = Path(__file__).resolve().parent          # ...\Cricket_ETL_EDA\src
PROJECT_FOLDER = SRC_FOLDER.parent                     # ...\Cricket_ETL_EDA
DATA_FOLDER = PROJECT_FOLDER / "data" / "processed"
ASSETS_FOLDER = PROJECT_FOLDER / "assets"
LOGO_FOLDER = ASSETS_FOLDER / "logos"
CSS_FILE = SRC_FOLDER / "style.css"                    # style.css sits next to app.py

# Newer Streamlit uses width="stretch"; older versions use use_container_width
_VERSION = tuple(int(part) for part in re.findall(r"\d+", st.__version__)[:2])
FULL_WIDTH = {"width": "stretch"} if _VERSION >= (1, 50) else {"use_container_width": True}

# Colour themes. Each one fills the CSS variables used in src/style.css.
THEMES = {
    "Stadium Green": {
        "pitch": "#0d3b2e", "pitch-deep": "#06231a", "turf": "#138a5c",
        "floodlight": "#f2b632", "accent-2": "#d9931a", "floodlight-soft": "#fff5d9",
        "accent-border": "#f0d58a", "accent-ink": "#6b4a00",
        "chalk": "#f5f8f4", "ink": "#102620", "muted": "#5d7268", "line": "#e1eae5",
        "on-dark": "#e8f4ee", "on-dark-soft": "#cfe6da", "on-dark-muted": "#a9cbbb",
    },
    "Night Match": {
        "pitch": "#13254f", "pitch-deep": "#0a1530", "turf": "#2563eb",
        "floodlight": "#22d3ee", "accent-2": "#0ea5e9", "floodlight-soft": "#e0f7fd",
        "accent-border": "#a5e8f5", "accent-ink": "#075e72",
        "chalk": "#f3f6fb", "ink": "#0f1a33", "muted": "#5b6785", "line": "#e1e7f2",
        "on-dark": "#e6edff", "on-dark-soft": "#c7d4f5", "on-dark-muted": "#95a6cf",
    },
    "Royal Gold": {
        "pitch": "#34184f", "pitch-deep": "#1d0b2e", "turf": "#7c3aed",
        "floodlight": "#f5c542", "accent-2": "#e09b1a", "floodlight-soft": "#fff6dc",
        "accent-border": "#f1d98c", "accent-ink": "#6b4a00",
        "chalk": "#f7f5fa", "ink": "#1e1330", "muted": "#6c6080", "line": "#e9e3f1",
        "on-dark": "#f1eafc", "on-dark-soft": "#d9cdee", "on-dark-muted": "#ab9cc6",
    },
    "Sunset Blaze": {
        "pitch": "#4a1020", "pitch-deep": "#2a0812", "turf": "#e11d48",
        "floodlight": "#fb923c", "accent-2": "#ea580c", "floodlight-soft": "#fff1e6",
        "accent-border": "#fdc9a2", "accent-ink": "#7c2d12",
        "chalk": "#faf6f4", "ink": "#2a1216", "muted": "#7a5f63", "line": "#efe4e2",
        "on-dark": "#fdebee", "on-dark-soft": "#f2cdd3", "on-dark-muted": "#c99aa3",
    },
}

# Chart colours (updated when the user picks a theme in the sidebar)
PITCH = "#0d3b2e"
TURF = "#138a5c"
FLOODLIGHT = "#f2b632"
INK = "#102620"
MUTED = "#5d7268"
GRID = "#e6eee9"

# Used only when player names can't tell us which side batted in an innings
HOME_BATTING_INNINGS_FALLBACK = 1
HOME_BOWLING_INNINGS_FALLBACK = 2


def load_css():
    """Load src/style.css and insert the optional hero photo (psl_hero.* in src/ or assets/)."""
    if not CSS_FILE.exists():
        st.warning(f"Style file not found: {CSS_FILE}. "
                   "The dashboard still works, but without its design.")
        return

    css_code = CSS_FILE.read_text(encoding="utf-8")
    image_types = {".png": "png", ".jpg": "jpeg", ".jpeg": "jpeg", ".webp": "webp"}
    hero_file = None
    for folder in [SRC_FOLDER, ASSETS_FOLDER]:
        for ext in image_types:
            if hero_file is None and (folder / f"psl_hero{ext}").exists():
                hero_file = folder / f"psl_hero{ext}"

    if hero_file:
        encoded = base64.b64encode(hero_file.read_bytes()).decode("utf-8")
        css_code = css_code.replace(
            "__PSL_HERO_IMAGE__",
            f"data:image/{image_types[hero_file.suffix.lower()]};base64,{encoded}",
        )
    else:
        css_code = css_code.replace('url("__PSL_HERO_IMAGE__")', "none")

    st.markdown(f"<style>{css_code}</style>", unsafe_allow_html=True)


load_css()


# ============================================================
# 2. TEAM BRANDING (crests + colours)
# ============================================================
# Each team gets an original shield crest in its club colours.
# To use your own image instead, save it as assets/logos/<team_slug>.png
# e.g. assets/logos/lahore_qalandars.png  (svg, jpg, webp also work)

TEAM_COLOURS = {
    "lahore": ("#00a651", "#e4002b"),
    "karachi": ("#1b3f8b", "#e5b53b"),
    "islamabad": ("#d71920", "#f4f4f4"),
    "peshawar": ("#f7b500", "#1f1f1f"),
    "quetta": ("#5b2d86", "#f2c230"),
    "multan": ("#0d8b7a", "#f5a623"),
    "hyderabad": ("#0f4c81", "#d4af37"),
    "rawalpindi": ("#7a1f2b", "#f0c05a"),
}
FALLBACK_COLOURS = [
    "#2b6cb0", "#9b2c2c", "#2f855a", "#6b46c1",
    "#c05621", "#2c7a7b", "#b83280", "#4a5568",
]


def esc(value):
    return html.escape(str(value))


def team_initials(name):
    words = [word for word in re.split(r"[^A-Za-z]+", str(name)) if word]
    if not words:
        return "?"
    if len(words) == 1:
        return words[0][:2].upper()
    return (words[0][0] + words[1][0]).upper()


def team_slug(name):
    return re.sub(r"[^a-z0-9]+", "_", str(name).lower()).strip("_")


def shade(hex_colour, factor):
    """Darken (factor < 1) or lighten (factor > 1) a hex colour."""
    hex_colour = hex_colour.lstrip("#")
    channels = [int(hex_colour[i:i + 2], 16) for i in (0, 2, 4)]
    channels = [max(0, min(255, int(c * factor))) for c in channels]
    return "#" + "".join(f"{c:02x}" for c in channels)


def is_light(hex_colour):
    hex_colour = hex_colour.lstrip("#")
    r, g, b = (int(hex_colour[i:i + 2], 16) for i in (0, 2, 4))
    return (0.299 * r + 0.587 * g + 0.114 * b) > 170


@lru_cache(maxsize=None)
def get_brand(team):
    key = str(team).lower()
    for city, (primary, secondary) in TEAM_COLOURS.items():
        if city in key:
            return {"short": team_initials(team), "primary": primary, "secondary": secondary}

    index = int(hashlib.md5(key.encode()).hexdigest(), 16) % len(FALLBACK_COLOURS)
    return {"short": team_initials(team), "primary": FALLBACK_COLOURS[index], "secondary": FLOODLIGHT}


def team_crest_svg(team):
    brand = get_brand(team)
    primary, secondary = brand["primary"], brand["secondary"]
    text_colour = "#17130a" if is_light(primary) else "#ffffff"
    font_size = 34 if len(brand["short"]) <= 2 else 26

    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 116">'
        '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{shade(primary, 1.18)}"/>'
        f'<stop offset="1" stop-color="{shade(primary, 0.6)}"/>'
        '</linearGradient></defs>'
        f'<path d="M50 4 L93 18 V58 C93 85 74 103 50 112 C26 103 7 85 7 58 V18 Z" '
        f'fill="url(#g)" stroke="{secondary}" stroke-width="5" stroke-linejoin="round"/>'
        '<path d="M50 14 L84 25 V58 C84 79 70 93 50 101 C30 93 16 79 16 58 V25 Z" '
        'fill="none" stroke="#ffffff" stroke-opacity="0.35" stroke-width="2"/>'
        f'<path d="M32 31 H68" stroke="{secondary}" stroke-width="4" stroke-linecap="round"/>'
        f'<text x="50" y="70" text-anchor="middle" font-family="Barlow Condensed, Arial Narrow, Arial, sans-serif" '
        f'font-weight="800" font-size="{font_size}" fill="{text_colour}" letter-spacing="1">'
        f'{esc(brand["short"])}</text>'
        f'<circle cx="50" cy="88" r="4" fill="{secondary}"/>'
        '</svg>'
    )


@lru_cache(maxsize=None)
def team_logo(team):
    """Return a data URI: your own logo file if present, otherwise the crest."""
    slug = team_slug(team)
    file_types = {
        ".png": "image/png", ".svg": "image/svg+xml", ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg", ".webp": "image/webp",
    }
    for ext, mime in file_types.items():
        logo_file = LOGO_FOLDER / f"{slug}{ext}"
        if logo_file.exists():
            return f"data:{mime};base64," + base64.b64encode(logo_file.read_bytes()).decode()

    svg = team_crest_svg(team)
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode()


def logo_img(team, size=40, extra_class=""):
    if not team:
        return ""
    return (
        f'<img class="team-logo {extra_class}" src="{team_logo(team)}" '
        f'width="{size}" height="{size}" alt="{esc(team)} crest">'
    )


def valid_team(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    if value is pd.NA:
        return ""
    text = str(value).strip()
    return "" if text.lower() in ("", "nan", "none") else text


# ============================================================
# 3. LOAD AND CLEAN DATA
# ============================================================

# Columns each file must have (exact names saved by the ETL pipeline)
REQUIRED_COLUMNS = {
    "matches.csv": ["match_id", "match_date", "home_team", "away_team",
                    "home_score", "away_score", "winner"],
    "batting.csv": ["match_id", "innings_number", "player_name", "runs", "balls",
                    "fours", "sixes", "strike_rate", "dismissal_type"],
    "bowling.csv": ["match_id", "innings_number", "player_name", "overs", "maidens",
                    "runs", "wickets", "economy", "wides", "no_balls"],
}


@st.cache_data
def read_csv_file(file_path, last_modified):
    """Read one CSV file. `last_modified` refreshes the cache after the ETL runs again."""
    return pd.read_csv(file_path)


def load_data():
    """Load the three CSV files and collect any problems as clear messages."""
    tables = {}
    problems = []
    for file_name, needed_columns in REQUIRED_COLUMNS.items():
        file_path = DATA_FOLDER / file_name
        if not file_path.exists():
            problems.append(f"Missing file: `{file_path}`")
            continue
        try:
            table = read_csv_file(str(file_path), file_path.stat().st_mtime)
        except pd.errors.EmptyDataError:
            problems.append(f"`{file_name}` is completely empty.")
            continue
        missing = [column for column in needed_columns if column not in table.columns]
        if missing:
            problems.append(f"`{file_name}` is missing column(s): {', '.join(missing)}")
            continue
        tables[file_name] = table.copy()
    return tables, problems


tables, problems = load_data()

if problems:
    st.error("The dashboard cannot start because of these data problems:")
    for problem in problems:
        st.markdown(f"- {problem}")
    st.info("Run the ETL pipeline first from the project folder: `python -m src.main`")
    st.stop()

matches = tables["matches.csv"]
batting = tables["batting.csv"]
bowling = tables["bowling.csv"]

if matches.empty:
    st.warning("matches.csv has no rows yet. Run the ETL pipeline: `python -m src.main`")
    st.stop()

for column in ["home_score", "away_score"]:
    matches[column] = pd.to_numeric(matches[column], errors="coerce")

for column in ["runs", "balls", "fours", "sixes", "innings_number"]:
    batting[column] = pd.to_numeric(batting[column], errors="coerce")

for column in ["runs", "wickets", "maidens", "wides", "no_balls", "innings_number"]:
    bowling[column] = pd.to_numeric(bowling[column], errors="coerce")

matches["match_date"] = pd.to_datetime(matches["match_date"], errors="coerce", utc=True)
for column in ["home_team", "away_team"]:
    matches[column] = matches[column].astype(str).str.strip()
matches["winner"] = matches["winner"].map(valid_team)

# Match status (e.g. "finished") is used for "completed matches" and the status filter
HAS_STATUS = "status" in matches.columns
if HAS_STATUS:
    matches["status"] = matches["status"].map(valid_team)

# player_key identifies a player. The player ID is the reliable choice, because two
# different players can share a short name. If an ID is missing we use the name.
# (This is an extra column in memory only; the CSV files are not changed.)
for table in [batting, bowling]:
    if "player_id" not in table.columns:
        table["player_id"] = ""
    table["player_key"] = table["player_id"].map(valid_team)
    missing_id = table["player_key"] == ""
    table.loc[missing_id, "player_key"] = table.loc[missing_id, "player_name"].map(valid_team)


# ============================================================
# 4. LINK PLAYERS TO TEAMS
# ============================================================
# batting.csv / bowling.csv have no team column. A player's own team appears
# in every match he plays, while opponents change, so the most frequent team
# across his matches is his team. A majority vote of players then decides
# which side batted (or bowled) in each innings.

def infer_player_teams(match_info, frames):
    counts = {}
    for frame in frames:
        pairs = frame[["match_id", "player_name"]].dropna().drop_duplicates()
        for match_id, player in zip(pairs["match_id"], pairs["player_name"]):
            for team in set(match_info.get(match_id, ())):
                counts.setdefault(player, {})
                counts[player][team] = counts[player].get(team, 0) + 1

    player_team = {}
    for player, team_counts in counts.items():
        ranked = sorted(team_counts.items(), key=lambda item: item[1], reverse=True)
        if len(ranked) == 1 or ranked[0][1] > ranked[1][1]:
            player_team[player] = ranked[0][0]
    return player_team


def assign_innings_team(frame, player_team, match_info, home_innings_fallback):
    out = frame.copy()
    out["team"] = None
    rows = out.dropna(subset=["match_id", "innings_number"])
    if rows.empty:
        return out

    guesses = rows["player_name"].map(player_team)
    lookup = {}

    for (match_id, innings), group in guesses.groupby([rows["match_id"], rows["innings_number"]]):
        if match_id not in match_info:
            continue
        home, away = match_info[match_id]
        votes = group.value_counts()
        home_votes, away_votes = int(votes.get(home, 0)), int(votes.get(away, 0))
        if home_votes != away_votes:
            lookup[(match_id, innings)] = home if home_votes > away_votes else away

    # Fill innings the vote could not decide
    for match_id, group in rows.groupby("match_id"):
        if match_id not in match_info:
            continue
        home, away = match_info[match_id]
        innings_list = group["innings_number"].unique().tolist()
        for innings in innings_list:
            if (match_id, innings) in lookup:
                continue
            decided = [lookup[(match_id, other)] for other in innings_list
                       if other != innings and (match_id, other) in lookup]
            if decided:
                lookup[(match_id, innings)] = away if decided[0] == home else home
            else:
                lookup[(match_id, innings)] = home if innings == home_innings_fallback else away

    out["team"] = [lookup.get((m, i)) for m, i in zip(out["match_id"], out["innings_number"])]
    return out


@st.cache_data(show_spinner=False)
def link_players_to_teams(matches_df, batting_df, bowling_df):
    unique_matches = matches_df.dropna(subset=["match_id"]).drop_duplicates("match_id")
    match_info = {
        row.match_id: (row.home_team, row.away_team)
        for row in unique_matches.itertuples()
    }
    player_team = infer_player_teams(match_info, [batting_df, bowling_df])
    batting_with_team = assign_innings_team(
        batting_df, player_team, match_info, HOME_BATTING_INNINGS_FALLBACK
    )
    bowling_with_team = assign_innings_team(
        bowling_df, player_team, match_info, HOME_BOWLING_INNINGS_FALLBACK
    )

    return batting_with_team, bowling_with_team


def main_team_map(batting_df, bowling_df):
    """Each player's most frequent team in the given rows."""
    stacked = pd.concat([
        batting_df[["player_name", "team"]],
        bowling_df[["player_name", "team"]],
    ]).dropna()
    if stacked.empty:
        return {}
    return (
        stacked.groupby("player_name")["team"]
        .agg(lambda s: s.value_counts().index[0])
        .to_dict()
    )


# Link players using every season, so the vote has the most evidence
batting, bowling = link_players_to_teams(matches, batting, bowling)


# ============================================================
# 5. HELPER FUNCTIONS
# ============================================================

def format_score(value):
    if pd.isna(value):
        return "–"
    try:
        return f"{int(value)}"
    except (ValueError, TypeError):
        return str(value)


def format_date(value, pattern="%d %b %Y"):
    return value.strftime(pattern) if pd.notna(value) else "Date unavailable"


def overs_to_balls(overs):
    """
    Convert cricket overs to balls. In cricket 3.4 overs means
    3 full overs and 4 balls = 3 x 6 + 4 = 22 balls (NOT 3.4 decimal overs).
    Returns None when the value cannot be read, so it is never counted wrongly.
    """
    if pd.isna(overs):
        return None
    parts = str(overs).strip().split(".")
    try:
        complete_overs = int(parts[0])
        extra_balls = int(parts[1]) if len(parts) > 1 and parts[1] != "" else 0
    except ValueError:
        return None
    if complete_overs < 0 or extra_balls < 0 or extra_balls > 5:
        return None
    return complete_overs * 6 + extra_balls


def balls_to_overs(balls):
    balls = int(balls) if pd.notna(balls) else 0
    return f"{balls // 6}.{balls % 6}"


def show_html(markup):
    st.markdown(markup, unsafe_allow_html=True)


def tidy_value(value):
    """Show one table value: '—' when missing, whole numbers without '.0'."""
    if pd.isna(value):
        return "—"
    if isinstance(value, (int, float, np.integer, np.floating)):
        if float(value).is_integer():
            return str(int(value))
        return f"{value:.2f}"
    return str(value)


def show_tidy_table(table):
    """Show a small table with missing values as '—' instead of blanks or zeros."""
    st.dataframe(table.apply(lambda column: column.map(tidy_value)), **FULL_WIDTH, hide_index=True)


def is_completed(status):
    """A match counts as completed when its status says it finished."""
    return str(status).strip().lower() in ["finished", "completed", "complete", "result"]


def keep_valid_choice(key, options, default):
    """If a saved filter value is no longer in the list (e.g. after changing season), reset it."""
    if st.session_state.get(key) not in options:
        st.session_state[key] = default


def section_title(title, note=None):
    note_html = f'<p class="section-note">{note}</p>' if note else ""
    show_html(f'<div class="section-head"><div class="section-title">{title}</div>{note_html}</div>')


def rolling_number(text):
    """
    Show a number like a stadium scoreboard: each digit rolls into place.
    Commas and other characters stay as they are.
    """
    parts = []
    for position, character in enumerate(str(text)):
        if character.isdigit():
            digits = "".join(f"<span>{d}</span>" for d in range(10))
            parts.append(
                f'<span class="odo"><span class="odo-strip" '
                f'style="--d:{character};animation-delay:{position * 0.05:.2f}s">{digits}</span></span>'
            )
        else:
            parts.append(esc(character))
    return f'<span class="odo-number" aria-label="{esc(text)}">{"".join(parts)}</span>'


def stat_strip(items):
    """A scoreboard-style band of headline numbers: (label, value, detail)."""
    cells = "".join(
        f'<div class="stat-cell"><div class="stat-value">{rolling_number(value)}</div>'
        f'<div class="stat-label">{label}</div>'
        + (f'<div class="stat-detail">{detail}</div>' if detail else "")
        + "</div>"
        for label, value, detail in items
    )
    show_html(f'<div class="stat-strip">{cells}</div>')


def form_dots(results):
    symbols = {"W": "W", "L": "L", "NR": "–"}
    return "".join(
        f'<span class="dot {result.lower()}" title="{result}">{symbols[result]}</span>'
        for result in results
    )


def match_card(row):
    home, away = row["home_team"], row["away_team"]
    winner = row["winner"]
    home_state = "win" if winner == home else ("lose" if winner == away else "")
    away_state = "win" if winner == away else ("lose" if winner == home else "")
    if winner in (home, away):
        result = f"{esc(winner)} won"
    elif winner == "Tie":
        result = "Match tied"
    else:
        result = "No result"

    return (
        f'<div class="match-card" style="--home:{get_brand(home)["primary"]};--away:{get_brand(away)["primary"]}">'
        f'<div class="mc-date">{format_date(row["match_date"], "%a %d %b %Y")}</div>'
        f'<div class="mc-row {home_state}">{logo_img(home, 34)}'
        f'<span class="mc-team">{esc(home)}</span>'
        f'<span class="mc-score">{format_score(row["home_score"])}</span></div>'
        '<div class="mc-vs"><span>v</span></div>'
        f'<div class="mc-row {away_state}">{logo_img(away, 34)}'
        f'<span class="mc-team">{esc(away)}</span>'
        f'<span class="mc-score">{format_score(row["away_score"])}</span></div>'
        f'<div class="mc-result">{result}</div></div>'
    )


def show_match_cards(data):
    if data.empty:
        st.info("No matches to show. Clear the filters to see every match.")
        return
    cards = "".join(match_card(row) for _, row in data.iterrows())
    show_html(f'<div class="match-grid">{cards}</div>')


def make_match_table(data):
    table = data[["match_date", "home_team", "home_score",
                  "away_team", "away_score", "winner"]].copy()
    table.insert(1, "Home Logo", table["home_team"].map(team_logo))
    table.insert(4, "Away Logo", table["away_team"].map(team_logo))
    table["match_date"] = table["match_date"].map(format_date)
    table["winner"] = table["winner"].replace("", "No result")
    return table.rename(columns={
        "match_date": "Match Date", "home_team": "Home Team", "home_score": "Home Score",
        "away_team": "Away Team", "away_score": "Away Score", "winner": "Winner",
    })


MATCH_TABLE_CONFIG = {
    "Home Logo": st.column_config.ImageColumn("", width="small"),
    "Away Logo": st.column_config.ImageColumn("", width="small"),
    "Home Score": st.column_config.NumberColumn(format="%d"),
    "Away Score": st.column_config.NumberColumn(format="%d"),
}


def podium(entries):
    """Top three players: list of dicts with name, team, main, sub."""
    medals = ["1st", "2nd", "3rd"]
    cards = []
    for rank, entry in enumerate(entries):
        team = valid_team(entry["team"])
        colour = get_brand(team)["primary"] if team else TURF
        cards.append(
            f'<div class="podium-card rank-{rank + 1}" style="--accent:{colour}">'
            f'<div class="podium-rank">{medals[rank]}</div>'
            f'{logo_img(team, 46)}'
            f'<div class="podium-name">{esc(entry["name"])}</div>'
            f'<div class="podium-team">{esc(team) if team else "Team unknown"}</div>'
            f'<div class="podium-main">{entry["main"]}</div>'
            f'<div class="podium-sub">{entry["sub"]}</div></div>'
        )
    show_html(f'<div class="podium">{"".join(cards)}</div>')


def bar_chart(data, label, value, colours=None, default_colour=None, height=320):
    """Horizontal bars. `colours` maps each label to a colour (e.g. team colours)."""
    chart_data = data[[label, value]].dropna().copy()
    if chart_data.empty:
        st.info("Nothing to chart yet.")
        return
    default_colour = default_colour or TURF
    chart_data["_colour"] = [
        (colours or {}).get(item, default_colour) for item in chart_data[label]
    ]

    # Make the axis 20% longer than the biggest bar,
    # so the number written after each bar is not cut off
    axis_end = max(chart_data[value].max() * 1.2, 1)

    bars = alt.Chart(chart_data).mark_bar(cornerRadiusEnd=5, size=20).encode(
        y=alt.Y(f"{label}:N", sort="-x", title=None,
                axis=alt.Axis(labelLimit=200, labelColor=INK, labelFontSize=12)),
        x=alt.X(f"{value}:Q", title=None,
                scale=alt.Scale(domain=[0, axis_end]),
                axis=alt.Axis(gridColor=GRID, labelColor=MUTED, tickCount=5)),
        color=alt.Color("_colour:N", scale=None, legend=None),
        tooltip=[alt.Tooltip(f"{label}:N"), alt.Tooltip(f"{value}:Q", format=",.0f")],
    )
    labels = bars.mark_text(align="left", dx=6, fontWeight="bold", fontSize=12).encode(
        text=alt.Text(f"{value}:Q", format=",.0f"), color=alt.value(INK)
    )
    chart = (
        (bars + labels).properties(height=height, padding={"left": 14, "right": 14, "top": 6, "bottom": 6})
        .configure_view(strokeWidth=0)
        .configure_axis(domain=False, labelFont="Barlow", titleFont="Barlow")
    )
    st.altair_chart(chart, **FULL_WIDTH)


def scatter_chart(data, x, y, size, label, x_title, y_title, colours, height=360):
    chart_data = data.dropna(subset=[x, y]).copy()
    if chart_data.empty:
        st.info("Not enough data for this chart. Try lowering the minimum filter.")
        return
    chart_data["_colour"] = [colours.get(item, TURF) for item in chart_data[label]]

    points = alt.Chart(chart_data).mark_circle(opacity=0.85, stroke="white", strokeWidth=1).encode(
        x=alt.X(f"{x}:Q", title=x_title, axis=alt.Axis(gridColor=GRID, labelColor=MUTED)),
        y=alt.Y(f"{y}:Q", title=y_title, scale=alt.Scale(zero=False),
                axis=alt.Axis(gridColor=GRID, labelColor=MUTED)),
        size=alt.Size(f"{size}:Q", legend=None, scale=alt.Scale(range=[40, 520])),
        color=alt.Color("_colour:N", scale=None, legend=None),
        tooltip=[label, alt.Tooltip(f"{x}:Q", format=",.0f"),
                 alt.Tooltip(f"{y}:Q", format=".2f"), alt.Tooltip(f"{size}:Q", format=",.0f")],
    )
    chart = points.properties(height=height, padding={"left": 14, "right": 14, "top": 6, "bottom": 6}).configure_view(strokeWidth=0).configure_axis(
        domain=False, labelFont="Barlow", titleFont="Barlow", titleColor=MUTED
    )
    st.altair_chart(chart, **FULL_WIDTH)


# ============================================================
# 6. SEASON FILTER
# ============================================================

if "season" not in matches.columns or matches["season"].isna().all():
    matches["season"] = matches["match_date"].dt.year
matches["season"] = pd.to_numeric(matches["season"], errors="coerce")
all_matches = matches.copy()

season_options = sorted(matches["season"].dropna().astype(int).unique().tolist(), reverse=True)


def season_label(season):
    # PSL 1 was played in 2016
    return "All seasons" if season == "All seasons" else f"PSL {season - 2015} ({season})"


with st.sidebar:
    show_html(
        '<div class="side-brand"><div class="side-mark">PSL</div>'
        '<div><div class="side-title">Cricket Analytics</div>'
        '<div class="side-sub">Pakistan Super League</div></div></div>'
    )
    selected_season = st.selectbox(
        "Season", ["All seasons"] + season_options,
        format_func=season_label, key="season_filter",
    )
    selected_theme = st.selectbox("Colour theme", list(THEMES), key="colour_theme")


def hex_to_rgb(hex_colour):
    """'#f2b632' -> '242, 182, 50' (used inside CSS rgba())."""
    hex_colour = hex_colour.lstrip("#")
    return ", ".join(str(int(hex_colour[i:i + 2], 16)) for i in (0, 2, 4))


# Send the chosen theme's colours to the CSS
theme = THEMES[selected_theme]
css_variables = "".join(f"--{name}: {colour};" for name, colour in theme.items())
css_variables += (
    f"--accent-rgb: {hex_to_rgb(theme['floodlight'])};"
    f"--turf-rgb: {hex_to_rgb(theme['turf'])};"
    f"--pitch-rgb: {hex_to_rgb(theme['pitch'])};"
    f"--deep-rgb: {hex_to_rgb(theme['pitch-deep'])};"
)
show_html(f"<style>:root {{ {css_variables} }}</style>")

# Use the same colours in the charts
PITCH, TURF, FLOODLIGHT = theme["pitch"], theme["turf"], theme["floodlight"]
INK, MUTED, GRID = theme["ink"], theme["muted"], theme["line"]

if selected_season != "All seasons":
    matches = matches[matches["season"] == selected_season].copy()
    batting = batting[batting["match_id"].isin(matches["match_id"])].copy()
    bowling = bowling[bowling["match_id"].isin(matches["match_id"])].copy()

# Player teams for the selected season(s); players can move between teams
PLAYER_TEAM = main_team_map(batting, bowling)


# ============================================================
# 7. TEAM SUMMARIES
# ============================================================

teams = sorted(
    {team for team in pd.concat([matches["home_team"], matches["away_team"]])
     if valid_team(team)}
)


def team_games(team):
    games = matches[(matches["home_team"] == team) | (matches["away_team"] == team)].copy()
    is_home = games["home_team"] == team
    games["opponent"] = np.where(is_home, games["away_team"], games["home_team"])
    games["scored"] = pd.to_numeric(np.where(is_home, games["home_score"], games["away_score"]), errors="coerce")
    games["conceded"] = pd.to_numeric(np.where(is_home, games["away_score"], games["home_score"]), errors="coerce")
    games["result"] = np.where(
        games["winner"] == team, "W",
        np.where(games["winner"] == games["opponent"], "L", "NR"),
    )
    return games.sort_values("match_date")


def build_standings():
    rows = []
    for team in teams:
        games = team_games(team)
        wins = int((games["result"] == "W").sum())
        losses = int((games["result"] == "L").sum())
        no_result = int((games["result"] == "NR").sum())
        played = len(games)
        decided = wins + losses
        rows.append({
            "Logo": team_logo(team),
            "Team": team,
            "P": played,
            "W": wins,
            "L": losses,
            "NR": no_result,
            "Pts": wins * 2 + no_result,
            "Win %": (wins / decided * 100) if decided else 0.0,
            "Avg Score": games["scored"].mean(),
            "Runs": games["scored"].sum(),
            "Form": " ".join({"W": "🟢", "L": "🔴", "NR": "⚪"}[r] for r in games["result"].tail(5)),
            "form_list": games["result"].tail(5).tolist(),
        })
    table = pd.DataFrame(rows)
    if table.empty:
        return table
    return table.sort_values(["Pts", "Win %"], ascending=False).reset_index(drop=True)


standings = build_standings()

total_matches = len(matches)
total_teams = len(teams)
total_runs = matches["home_score"].sum() + matches["away_score"].sum()
total_wickets = bowling["wickets"].fillna(0).sum()
total_sixes = batting["sixes"].fillna(0).sum()
scores = pd.concat([matches["home_score"], matches["away_score"]]).dropna()
avg_team_score = scores.mean() if not scores.empty else 0
highest_score = scores.max() if not scores.empty else 0
TEAM_COLOURS_MAP = {team: get_brand(team)["primary"] for team in teams}
PLAYER_COLOURS = {player: get_brand(team)["primary"] for player, team in PLAYER_TEAM.items()}


# ============================================================
# 8. SIDEBAR
# ============================================================

PAGES = {
    "Overview": "🏟️",
    "Team Profiles": "🛡️",
    "Match Centre": "📅",
    "Match Scorecard": "📋",
    "Batting Analysis": "🏏",
    "Bowling Analysis": "🎯",
}

with st.sidebar:
    page = st.radio(
        "Navigate",
        list(PAGES),
        format_func=lambda name: f"{PAGES[name]}   {name}",
        key="main_navigation",
        label_visibility="collapsed",
    )
    if teams:
        crests = "".join(
            f'<div class="side-crest" title="{esc(team)}">{logo_img(team, 34)}</div>'
            for team in teams
        )
        show_html(f'<div class="side-label">Teams</div><div class="side-crests">{crests}</div>')
    show_html(
        f'<div class="side-status"><div><b>{total_matches:,}</b> matches</div>'
        f'<div><b>{total_teams}</b> teams</div>'
        f'<div><b>{batting["player_name"].nunique():,}</b> players</div></div>'
        '<div class="side-foot">Built on the Cricket ETL + EDA pipeline</div>'
    )


# ============================================================
# 9. HERO
# ============================================================

hero_crests = "".join(
    f'<div class="hero-crest" style="animation-delay:{i * 0.07:.2f}s">{logo_img(team, 58)}'
    f'<span>{esc(get_brand(team)["short"])}</span></div>'
    for i, team in enumerate(teams[:8])
)
latest = matches.dropna(subset=["match_date"]).sort_values("match_date").tail(1)
season_text = (
    f'Updated to {format_date(latest["match_date"].iloc[0])}' if not latest.empty else "No matches yet"
)
if selected_season != "All seasons":
    season_text = f"{season_label(selected_season)} · {season_text}"

# Stadium stands, flashing crowd, floodlight beams, a cricket ball and a bat (decoration only)
hero_effects = (
    '<div class="hero-fx" aria-hidden="true">'
    '<span class="stadium"></span><span class="crowd"></span>'
    '<span class="beam beam-1"></span><span class="beam beam-2"></span>'
    '<span class="ball"></span><span class="bat"></span></div>'
)

show_html(
    f'<div class="hero">{hero_effects}<div class="hero-text">'
    f'<div class="hero-kicker"><span class="live-dot"></span>{season_text}</div>'
    '<h1>PSL Cricket Analytics</h1>'
    '<p>Results, scorecards and player numbers from every match in your dataset.</p>'
    '<div class="hero-scoreline">'
    f'<div><b>{rolling_number(f"{total_matches:,}")}</b><span>Matches</span></div>'
    f'<div><b>{rolling_number(f"{total_runs:,.0f}")}</b><span>Runs</span></div>'
    f'<div><b>{rolling_number(f"{total_wickets:,.0f}")}</b><span>Wickets</span></div>'
    f'<div><b>{rolling_number(f"{total_sixes:,.0f}")}</b><span>Sixes</span></div>'
    '</div></div>'
    f'<div class="hero-crests">{hero_crests}</div></div>'
)

# Scrolling results ticker, like a TV score bar
recent_for_ticker = matches.sort_values("match_date", ascending=False).head(12)
if not recent_for_ticker.empty:
    ticker_items = ""
    for _, row in recent_for_ticker.iterrows():
        home, away, winner = row["home_team"], row["away_team"], row["winner"]
        result = f"{esc(get_brand(winner)['short'])} won" if winner in (home, away) else "No result"
        ticker_items += (
            f'<span class="tick">{logo_img(home, 22)}<b>{esc(get_brand(home)["short"])}</b> '
            f'{format_score(row["home_score"])}<i>v</i>{format_score(row["away_score"])} '
            f'<b>{esc(get_brand(away)["short"])}</b>{logo_img(away, 22)}'
            f'<em>{result}</em></span>'
        )
    # The items are repeated twice so the scroll loops without a gap
    seconds = max(20, len(recent_for_ticker) * 4)
    show_html(
        '<div class="ticker"><div class="ticker-label"><span class="live-dot"></span>Latest</div>'
        f'<div class="ticker-window"><div class="ticker-track" style="animation-duration:{seconds}s">'
        f'{ticker_items}{ticker_items}</div></div></div>'
    )


# ============================================================
# 10. OVERVIEW
# ============================================================

if page == "Overview":
    # Unique players are counted by distinct player ID (name only if the ID is missing).
    # Batters and bowlers are counted separately and never added together.
    unique_batters = batting["player_key"].nunique()
    unique_bowlers = bowling["player_key"].nunique()
    if HAS_STATUS:
        completed_matches = f"{int(matches['status'].map(is_completed).sum()):,}"
        completed_note = "status is finished"
    else:
        completed_matches = "—"
        completed_note = "no status column"

    # Total matches is already shown in the banner at the top of every page
    stat_strip([
        ("Unique batters", f"{unique_batters:,}", "distinct player IDs"),
        ("Unique bowlers", f"{unique_bowlers:,}", "distinct player IDs"),
        ("Completed matches", completed_matches, completed_note),
        ("Teams", f"{total_teams}", "in the dataset"),
    ])

    # --- Top 3 batters and bowlers ---
    batter_totals = (
        batting.groupby("player_key")
        .agg(Batter=("player_name", "first"), Runs=("runs", "sum"), Balls=("balls", "sum"))
        .sort_values("Runs", ascending=False)
    )
    bowler_totals = (
        bowling.groupby("player_key")
        .agg(Bowler=("player_name", "first"), Wickets=("wickets", "sum"), Runs=("runs", "sum"))
        .sort_values(["Wickets", "Runs"], ascending=[False, True])
    )

    left, right = st.columns(2, gap="large")
    with left:
        section_title("Top 3 batters", "By total runs.")
        if batter_totals.empty:
            st.info("No batting records yet.")
        else:
            podium([
                {"name": row["Batter"], "team": PLAYER_TEAM.get(row["Batter"]),
                 "main": f"{row['Runs']:,.0f} runs", "sub": f"{row['Balls']:,.0f} balls faced"}
                for _, row in batter_totals.head(3).iterrows()
            ])
    with right:
        section_title("Top 3 bowlers", "By total wickets.")
        if bowler_totals.empty:
            st.info("No bowling records yet.")
        else:
            podium([
                {"name": row["Bowler"], "team": PLAYER_TEAM.get(row["Bowler"]),
                 "main": f"{row['Wickets']:,.0f} wickets", "sub": f"{row['Runs']:,.0f} runs conceded"}
                for _, row in bowler_totals.head(3).iterrows()
            ])

    section_title("Teams", "Record and last five results for each side.")
    if standings.empty:
        st.info("No teams found in matches.csv.")
    else:
        tiles = ""
        for _, row in standings.iterrows():
            # The ring around the right side shows the win percentage
            tiles += (
                f'<div class="team-tile" style="--team:{get_brand(row["Team"])["primary"]}">'
                f'{logo_img(row["Team"], 52)}<div class="tile-body">'
                f'<div class="tile-name">{esc(row["Team"])}</div>'
                f'<div class="tile-record">{row["W"]} won · {row["L"]} lost</div>'
                f'<div class="form">{form_dots(row["form_list"])}</div></div>'
                f'<div class="tile-ring" style="--pct:{row["Win %"]:.0f}">'
                f'<span>{row["Win %"]:.0f}%</span></div></div>'
            )
        show_html(f'<div class="team-grid">{tiles}</div>')

        table_col, chart_col = st.columns([3, 2], gap="large")
        with table_col:
            section_title("Most successful teams", "Sorted by points: two for a win, one for no result.")
            st.dataframe(
                standings.drop(columns=["form_list", "Runs"]),
                **FULL_WIDTH,
                hide_index=True,
                column_config={
                    "Logo": st.column_config.ImageColumn("", width="small"),
                    "Win %": st.column_config.ProgressColumn(
                        "Win %", format="%.0f%%", min_value=0, max_value=100
                    ),
                    "Avg Score": st.column_config.NumberColumn(format="%.0f"),
                },
            )
        with chart_col:
            section_title("Wins by team")
            bar_chart(standings, "Team", "W", TEAM_COLOURS_MAP, height=330)

    left, right = st.columns(2, gap="large")
    with left:
        section_title("Leading batters", "Top 10 by runs. Bars use each player's team colour.")
        bar_chart(batter_totals.head(10), "Batter", "Runs", PLAYER_COLOURS, height=360)
    with right:
        section_title("Leading wicket-takers", "Top 10 by wickets.")
        bar_chart(bowler_totals.head(10), "Bowler", "Wickets", PLAYER_COLOURS, height=360)

    if selected_season == "All seasons" and len(season_options) > 1:
        section_title("Season by season", "Pick a season in the sidebar to see it on its own.")
        season_rows = []
        for season in season_options:
            season_matches = all_matches[all_matches["season"] == season]
            ids = season_matches["match_id"]
            season_bat = batting[batting["match_id"].isin(ids)]
            season_bowl = bowling[bowling["match_id"].isin(ids)]
            top_bat = season_bat.groupby("player_name")["runs"].sum().sort_values(ascending=False).head(1)
            top_bowl = season_bowl.groupby("player_name")["wickets"].sum().sort_values(ascending=False).head(1)
            season_rows.append({
                "Season": season_label(season),
                "Matches": len(season_matches),
                "Runs": season_matches["home_score"].sum() + season_matches["away_score"].sum(),
                "Most runs": f"{top_bat.index[0]} ({top_bat.iloc[0]:,.0f})" if not top_bat.empty else "–",
                "Most wickets": f"{top_bowl.index[0]} ({top_bowl.iloc[0]:,.0f})" if not top_bowl.empty else "–",
            })
        st.dataframe(
            pd.DataFrame(season_rows), **FULL_WIDTH, hide_index=True,
            column_config={"Runs": st.column_config.NumberColumn(format="%d")},
        )

    section_title("Latest results")
    show_match_cards(matches.sort_values("match_date", ascending=False).head(6))


# ============================================================
# 11. TEAM PROFILES
# ============================================================

elif page == "Team Profiles":
    if not teams:
        st.info("No teams found in matches.csv.")
        st.stop()

    team = st.selectbox("Choose a team", teams, key="profile_team")
    brand = get_brand(team)
    games = team_games(team)
    record = standings.set_index("Team").loc[team]

    show_html(
        f'<div class="team-hero" style="--team:{brand["primary"]};--team-2:{brand["secondary"]}">'
        f'{logo_img(team, 108, "team-hero-logo")}'
        f'<div class="team-hero-body"><h2>{esc(team)}</h2>'
        f'<div class="team-hero-record">{record["W"]} wins from {record["P"]} matches '
        f'· {record["Win %"]:.0f}% of decided games won</div>'
        f'<div class="form big">{form_dots(record["form_list"])}</div></div></div>'
    )

    stat_strip([
        ("Matches", f'{record["P"]}', None),
        ("Points", f'{record["Pts"]}', None),
        ("Average score", f'{record["Avg Score"]:.0f}' if pd.notna(record["Avg Score"]) else "–", None),
        ("Highest score", format_score(games["scored"].max()), None),
        ("Lowest score", format_score(games["scored"].min()), None),
    ])

    left, right = st.columns(2, gap="large")
    with left:
        section_title("Top batters")
        team_batters = (
            batting[batting["team"] == team].groupby("player_name")["runs"].sum()
            .sort_values(ascending=False).head(6).reset_index()
            .rename(columns={"player_name": "Batter", "runs": "Runs"})
        )
        bar_chart(team_batters, "Batter", "Runs", default_colour=brand["primary"], height=260)
    with right:
        section_title("Top bowlers")
        team_bowlers = (
            bowling[bowling["team"] == team].groupby("player_name")["wickets"].sum()
            .sort_values(ascending=False).head(6).reset_index()
            .rename(columns={"player_name": "Bowler", "wickets": "Wickets"})
        )
        bar_chart(team_bowlers, "Bowler", "Wickets", default_colour=brand["secondary"]
                  if not is_light(brand["secondary"]) else shade(brand["primary"], 0.75), height=260)

    section_title("Head to head", f"{esc(team)}'s record against each opponent.")
    head_to_head = (
        games.groupby("opponent")["result"]
        .agg(P="count", W=lambda s: (s == "W").sum(), L=lambda s: (s == "L").sum())
        .reset_index().rename(columns={"opponent": "Opponent"})
    )
    head_to_head.insert(0, "Logo", head_to_head["Opponent"].map(team_logo))
    head_to_head["Win %"] = np.where(
        (head_to_head["W"] + head_to_head["L"]) > 0,
        head_to_head["W"] / (head_to_head["W"] + head_to_head["L"]).replace(0, np.nan) * 100, 0,
    )
    st.dataframe(
        head_to_head.sort_values("P", ascending=False),
        **FULL_WIDTH, hide_index=True,
        column_config={
            "Logo": st.column_config.ImageColumn("", width="small"),
            "Win %": st.column_config.ProgressColumn("Win %", format="%.0f%%", min_value=0, max_value=100),
        },
    )

    section_title("Recent matches")
    show_match_cards(games.sort_values("match_date", ascending=False).head(6))


# ============================================================
# 12. MATCH CENTRE
# ============================================================

elif page == "Match Centre":
    section_title("Match centre", "Search and filter PSL matches. All filters work together.")

    # Options for the filters
    team_options = ["All teams"] + teams
    winner_values = sorted({winner for winner in matches["winner"] if winner})
    winner_options = ["All results"] + winner_values + ["No result"]
    if HAS_STATUS:
        status_options = ["All statuses"] + sorted({status for status in matches["status"] if status})
    else:
        status_options = ["All statuses"]

    match_days = matches["match_date"].dropna().dt.date
    has_dates = not match_days.empty
    if has_dates:
        first_day, last_day = match_days.min(), match_days.max()

    def reset_match_filters():
        """Put every Match Centre filter back to its starting value."""
        st.session_state["match_search"] = ""
        st.session_state["mc_home"] = "All teams"
        st.session_state["mc_away"] = "All teams"
        st.session_state["mc_winner"] = "All results"
        st.session_state["mc_status"] = "All statuses"
        st.session_state["match_page"] = 1
        if has_dates:
            st.session_state["mc_dates"] = (first_day, last_day)

    # Start values (only the first time) and repair values that no longer fit,
    # for example after picking another season in the sidebar
    if "match_search" not in st.session_state:
        st.session_state["match_search"] = ""
    keep_valid_choice("mc_home", team_options, "All teams")
    keep_valid_choice("mc_away", team_options, "All teams")
    keep_valid_choice("mc_winner", winner_options, "All results")
    keep_valid_choice("mc_status", status_options, "All statuses")
    if has_dates:
        saved_dates = st.session_state.get("mc_dates")
        if (not isinstance(saved_dates, (tuple, list)) or len(saved_dates) != 2
                or saved_dates[0] < first_day or saved_dates[1] > last_day):
            st.session_state["mc_dates"] = (first_day, last_day)

    # Row 1: search and team filters
    column_1, column_2, column_3 = st.columns([2, 1, 1])
    column_1.text_input("Search by team name", placeholder="Either team, e.g. Karachi", key="match_search")
    column_2.selectbox("Home team", team_options, key="mc_home")
    column_3.selectbox("Away team", team_options, key="mc_away")

    # Row 2: result, status and dates
    column_1, column_2, column_3 = st.columns([1, 1, 2])
    column_1.selectbox("Winner", winner_options, key="mc_winner")
    column_2.selectbox("Match status", status_options, key="mc_status", disabled=not HAS_STATUS)
    if has_dates:
        column_3.date_input("Match dates (from – to)", min_value=first_day, max_value=last_day, key="mc_dates")
    else:
        column_3.caption("Match dates could not be read, so date filtering is off.")

    # Row 3: view and reset
    column_1, column_2 = st.columns([3, 1])
    with column_1:
        view = st.radio("View", ["Cards", "Table"], horizontal=True, key="match_view")
    with column_2:
        st.button("Reset filters", on_click=reset_match_filters, **FULL_WIDTH)

    # Apply every filter one after another, so they all work together
    found = matches.copy()

    search_text = st.session_state["match_search"].strip()
    if search_text:
        in_home = found["home_team"].str.contains(search_text, case=False, regex=False)
        in_away = found["away_team"].str.contains(search_text, case=False, regex=False)
        found = found[in_home | in_away]

    if st.session_state["mc_home"] != "All teams":
        found = found[found["home_team"] == st.session_state["mc_home"]]

    if st.session_state["mc_away"] != "All teams":
        found = found[found["away_team"] == st.session_state["mc_away"]]

    chosen_winner = st.session_state["mc_winner"]
    if chosen_winner == "No result":
        found = found[found["winner"] == ""]
    elif chosen_winner != "All results":
        found = found[found["winner"] == chosen_winner]

    if HAS_STATUS and st.session_state["mc_status"] != "All statuses":
        found = found[found["status"] == st.session_state["mc_status"]]

    if has_dates:
        chosen_dates = st.session_state["mc_dates"]
        # While picking, the calendar briefly returns only a start date; filter once both are chosen
        if isinstance(chosen_dates, (tuple, list)) and len(chosen_dates) == 2:
            start_day, end_day = chosen_dates
            day_of_match = found["match_date"].dt.date
            found = found[(day_of_match >= start_day) & (day_of_match <= end_day)]

    found = found.sort_values("match_date", ascending=False)
    st.caption(f"{len(found)} of {len(matches)} matches match these filters")

    if found.empty:
        st.warning("No matches found. Change the search or filters, or press **Reset filters**.")
    elif view == "Cards":
        per_page = 12
        pages = max(1, math.ceil(len(found) / per_page))
        page_number = 1
        if pages > 1:
            keep_valid_choice("match_page", list(range(1, pages + 1)), 1)
            page_number = st.selectbox(
                "Page", list(range(1, pages + 1)),
                format_func=lambda n: f"Page {n} of {pages}", key="match_page",
            )
        start = (page_number - 1) * per_page
        show_match_cards(found.iloc[start:start + per_page])
    else:
        table = make_match_table(found)
        if HAS_STATUS:
            table["Status"] = found["status"].replace("", "—").values
        st.dataframe(table, **FULL_WIDTH, hide_index=True, height=480, column_config=MATCH_TABLE_CONFIG)


# ============================================================
# 13. MATCH SCORECARD
# ============================================================

elif page == "Match Scorecard":
    section_title("Match scorecard", "Pick a match to see both innings in full.")

    if matches.empty:
        st.info("No matches found in matches.csv.")
        st.stop()

    options = matches.sort_values("match_date", ascending=False)
    match_labels = {}
    for _, option in options.iterrows():
        match_labels[option["match_id"]] = (
            f'{option["home_team"]} vs {option["away_team"]}  |  {format_date(option["match_date"])}'
        )
    selected_id = st.selectbox("Select a match", list(match_labels),
                               format_func=lambda match_id: match_labels[match_id])
    selected_match = options[options["match_id"] == selected_id].iloc[0]

    match_id = selected_match["match_id"]
    match_batting = batting[batting["match_id"] == match_id].copy()
    match_bowling = bowling[bowling["match_id"] == match_id].copy()

    home_team = selected_match["home_team"]
    away_team = selected_match["away_team"]
    winner_name = selected_match["winner"]

    def score_side(team, score):
        state = " is-winner" if winner_name == team else ""
        return (
            f'<div class="score-team{state}">{logo_img(team, 84, "score-logo")}'
            f'<div class="team-name">{esc(team)}</div>'
            f'<div class="team-score">{format_score(score)}</div></div>'
        )

    if winner_name in (home_team, away_team):
        result_text = f"{esc(winner_name)} won"
    elif winner_name == "Tie":
        result_text = "Match tied"
    else:
        result_text = "No result"
    show_html(
        f'<div class="scoreboard" style="--home:{get_brand(home_team)["primary"]};'
        f'--away:{get_brand(away_team)["primary"]}">'
        f'{score_side(home_team, selected_match["home_score"])}'
        f'<div class="score-vs"><span>v</span><small>{format_date(selected_match["match_date"])}</small></div>'
        f'{score_side(away_team, selected_match["away_score"])}</div>'
        f'<div class="winner-banner">🏆 {result_text}</div>'
    )

    left_col, right_col = st.columns(2, gap="large")
    with left_col:
        section_title("Top 3 batters")
        if match_batting.empty:
            st.info("No batting records for this match.")
        else:
            top_three = match_batting.sort_values(["runs", "balls"], ascending=[False, True]).head(3)
            podium([
                {"name": r.player_name, "team": r.team,
                 "main": f"{format_score(r.runs)} runs",
                 "sub": f"{format_score(r.balls)} balls · {format_score(r.fours)}×4 · {format_score(r.sixes)}×6"}
                for r in top_three.itertuples()
            ])
    with right_col:
        section_title("Wicket takers")
        wicket_takers = match_bowling[match_bowling["wickets"] > 0].sort_values(
            ["wickets", "runs"], ascending=[False, True]
        )
        if wicket_takers.empty:
            st.info("No wickets recorded in the available bowling data.")
        else:
            podium([
                {"name": r.player_name, "team": r.team,
                 "main": f"{format_score(r.wickets)}/{format_score(r.runs)}",
                 "sub": f"{r.overs} overs"}
                for r in wicket_takers.head(3).itertuples()
            ])

    section_title("Innings", "Batting card and the bowling figures for each innings.")
    st.caption(
        "The data has no team column, so the team for each innings is worked out from which "
        "players appear for each side across all matches. Bowling rows use the same innings "
        "number as the batting they bowled to. Missing values are shown as —."
    )

    # Innings found in either the batting or the bowling records of this match
    innings_list = sorted(set(match_batting["innings_number"].dropna()) | set(match_bowling["innings_number"].dropna()))
    if not innings_list:
        st.info("No innings data for this match.")
    else:
        batting_columns = {
            "player_name": "Batter", "dismissal_type": "Dismissal", "runs": "Runs",
            "balls": "Balls", "fours": "4s", "sixes": "6s", "strike_rate": "Strike rate",
        }
        bowling_columns = {
            "player_name": "Bowler", "overs": "Overs", "maidens": "Maidens", "runs": "Runs conceded",
            "wickets": "Wickets", "economy": "Economy", "wides": "Wides", "no_balls": "No-balls",
        }
        labels = []
        for innings in innings_list:
            innings_teams = match_batting.loc[match_batting["innings_number"] == innings, "team"].dropna()
            labels.append((innings, valid_team(innings_teams.iloc[0]) if not innings_teams.empty else ""))

        tabs = st.tabs([f"{team or 'Team not identified'} · innings {int(innings)}" for innings, team in labels])
        for tab, (innings, batting_team) in zip(tabs, labels):
            with tab:
                if batting_team == home_team:
                    opponent, team_score = away_team, selected_match["home_score"]
                elif batting_team == away_team:
                    opponent, team_score = home_team, selected_match["away_score"]
                else:
                    opponent, team_score = "the other team", None

                show_html(
                    f'<div class="innings-head">{logo_img(batting_team, 40)}'
                    f'<div><b>{esc(batting_team or "Team not identified")}</b>'
                    f'<span>{format_score(team_score)} runs against {esc(opponent)}</span></div></div>'
                )

                # Batting card for this innings
                innings_batting = match_batting[match_batting["innings_number"] == innings].copy()
                if innings_batting.empty:
                    st.info("No batting records for this innings.")
                else:
                    # In this data an empty dismissal means the batter was not out
                    innings_batting["dismissal_type"] = innings_batting["dismissal_type"].map(
                        lambda value: valid_team(value) or "not out")
                    show_tidy_table(innings_batting[list(batting_columns)].rename(columns=batting_columns))

                # Bowling figures: bowlers with the SAME innings number bowled this innings
                innings_bowling = match_bowling[match_bowling["innings_number"] == innings].copy()
                st.caption(f"Bowling by {opponent}")
                if innings_bowling.empty:
                    st.info("No bowling records for this innings.")
                else:
                    # Keep overs as written (3.4 means 3 overs and 4 balls)
                    innings_bowling["overs"] = innings_bowling["overs"].map(
                        lambda value: "—" if pd.isna(value) else str(value))
                    show_tidy_table(innings_bowling[list(bowling_columns)].rename(columns=bowling_columns))


# ============================================================
# 14. BATTING ANALYSIS
# ============================================================

elif page == "Batting Analysis":
    section_title("Batting analysis", "Search a batter, sort the leaderboard and view one player's innings.")

    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
    search_player = c1.text_input("Search batter", placeholder="Any part of a name, e.g. Babar", key="batting_search")
    team_choice = c2.selectbox("Team", ["All teams"] + teams, key="bat_team")
    sort_choice = c3.selectbox("Sort by", ["Runs", "Balls", "Fours", "Sixes", "Strike Rate"], key="bat_sort")
    min_balls = c4.number_input("Minimum balls faced", 0, 5000, 30, step=10, key="bat_min_balls",
                                help="Used for strike rate, so a 1-ball innings does not top the list.")

    source = batting if team_choice == "All teams" else batting[batting["team"] == team_choice]
    # In this data an empty dismissal means "not out"
    source = source.assign(
        is_out=source["dismissal_type"].map(lambda value: valid_team(value).lower() not in
                                            ["", "not out", "did not bat", "retired hurt"])
    )

    # One row per player (grouped by player ID), adding up every innings
    summary = (
        source.groupby("player_key")
        .agg(Batter=("player_name", "first"), Inns=("match_id", "size"), Runs=("runs", "sum"),
             Balls=("balls", "sum"), Outs=("is_out", "sum"), Fours=("fours", "sum"),
             Sixes=("sixes", "sum"), Best=("runs", "max"))
        .reset_index()
    )
    # Overall strike rate = total runs / total balls x 100 (not an average of strike rates).
    # Zero balls becomes "missing" so we never divide by zero.
    summary["Strike Rate"] = summary["Runs"] / summary["Balls"].replace(0, np.nan) * 100
    summary["Average"] = summary["Runs"] / summary["Outs"].replace(0, np.nan)
    summary["Team"] = summary["Batter"].map(PLAYER_TEAM)
    summary.insert(0, "Logo", summary["Team"].map(lambda t: team_logo(t) if valid_team(t) else None))

    if search_player.strip():
        summary = summary[summary["Batter"].astype(str).str.contains(
            search_player.strip(), case=False, na=False, regex=False)]
    summary = summary.sort_values("Runs", ascending=False)

    if summary.empty:
        st.warning("No batter matches that search. Check the spelling or clear the search box.")
    else:
        stat_strip([
            ("Batters", f"{len(summary):,}", None),
            ("Runs", f"{summary['Runs'].sum():,.0f}", None),
            ("Fours", f"{summary['Fours'].sum():,.0f}", None),
            ("Sixes", f"{summary['Sixes'].sum():,.0f}", None),
        ])

        section_title("Leading run scorers")
        podium([
            {"name": row["Batter"], "team": row["Team"], "main": f"{row['Runs']:,.0f} runs",
             "sub": (f"Strike rate {row['Strike Rate']:.1f}" if pd.notna(row["Strike Rate"]) else "Strike rate –")
             + f" · best {format_score(row['Best'])}"}
            for _, row in summary.head(3).iterrows()
        ])

        left, right = st.columns(2, gap="large")
        with left:
            section_title("Top 10 batters", "By total runs.")
            bar_chart(summary.head(10), "Batter", "Runs", PLAYER_COLOURS, height=360)
        with right:
            section_title("Runs vs strike rate", f"Batters with at least {min_balls} balls faced. Bubble size is balls faced.")
            scatter_chart(summary[summary["Balls"] >= min_balls], "Runs", "Strike Rate", "Balls",
                          "Batter", "Runs", "Strike rate", PLAYER_COLOURS)

        # Leaderboard sorted by the chosen column (highest first)
        ranked = summary
        if sort_choice == "Strike Rate":
            ranked = summary[summary["Balls"] >= min_balls]
        ranked = ranked.sort_values(sort_choice, ascending=False, na_position="last")
        show_all = st.checkbox("Show all batters (not just the top 10)", key="bat_show_all")
        if not show_all:
            ranked = ranked.head(10)

        note = f" (at least {min_balls} balls faced)" if sort_choice == "Strike Rate" else ""
        section_title("Batting leaderboard", f"Sorted by {sort_choice.lower()}{note}.")
        if ranked.empty:
            st.info("No batters meet the minimum balls faced. Lower the minimum to see more.")
        else:
            st.dataframe(
                ranked[["Logo", "Batter", "Team", "Inns", "Runs", "Balls", "Best",
                        "Average", "Strike Rate", "Fours", "Sixes"]],
                **FULL_WIDTH, hide_index=True,
                column_config={
                    "Logo": st.column_config.ImageColumn("", width="small"),
                    "Runs": st.column_config.NumberColumn(format="%d"),
                    "Balls": st.column_config.NumberColumn(format="%d"),
                    "Best": st.column_config.NumberColumn(format="%d"),
                    "Fours": st.column_config.NumberColumn(format="%d"),
                    "Sixes": st.column_config.NumberColumn(format="%d"),
                    "Average": st.column_config.NumberColumn(format="%.2f"),
                    "Strike Rate": st.column_config.NumberColumn(format="%.2f"),
                },
            )

        # --- One batter's statistics and every innings ---
        section_title("Individual batting statistics")
        batter_names = dict(zip(summary["player_key"], summary["Batter"]))
        chosen_key = st.selectbox("Choose a batter", list(batter_names),
                                  format_func=lambda key: batter_names[key], key="selected_batter")
        player = summary[summary["player_key"] == chosen_key].iloc[0]
        stat_strip([
            ("Innings", f"{player['Inns']:,}", None),
            ("Runs", f"{player['Runs']:,.0f}", None),
            ("Strike rate", f"{player['Strike Rate']:.1f}" if pd.notna(player["Strike Rate"]) else "—", None),
            ("Average", f"{player['Average']:.1f}" if pd.notna(player["Average"]) else "—", "runs per dismissal"),
            ("Best", format_score(player["Best"]), None),
        ])
        innings_rows = source[source["player_key"] == chosen_key].merge(
            matches[["match_id", "match_date", "home_team", "away_team"]], on="match_id", how="left"
        ).sort_values("match_date", ascending=False)
        innings_rows["Date"] = innings_rows["match_date"].map(format_date)
        innings_rows["Match"] = innings_rows["home_team"] + " vs " + innings_rows["away_team"]
        innings_rows["dismissal_type"] = innings_rows["dismissal_type"].map(lambda value: valid_team(value) or "not out")
        show_tidy_table(innings_rows[["Date", "Match", "runs", "balls", "fours", "sixes", "strike_rate", "dismissal_type"]]
                        .rename(columns={"runs": "Runs", "balls": "Balls", "fours": "4s", "sixes": "6s",
                                         "strike_rate": "Strike rate", "dismissal_type": "Dismissal"}))


# ============================================================
# 15. BOWLING ANALYSIS
# ============================================================

elif page == "Bowling Analysis":
    section_title("Bowling analysis", "Wickets, economy and every spell for any bowler.")

    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
    search_bowler = c1.text_input("Search bowler", placeholder="Any part of a name", key="bowling_search")
    team_choice = c2.selectbox("Team", ["All teams"] + teams, key="bowl_team")
    sort_choice = c3.selectbox("Sort by", ["Wickets", "Runs Conceded", "Overs", "Economy"], key="bowl_sort")
    min_overs = c4.number_input("Minimum overs bowled", 0, 2000, 5, step=1, key="bowl_min_overs",
                                help="Used for economy, so a 1-over spell does not top the list.")

    bowling_data = bowling if team_choice == "All teams" else bowling[bowling["team"] == team_choice]
    bowling_data = bowling_data.assign(balls_bowled=bowling_data["overs"].map(overs_to_balls))

    # Rows whose overs could not be read are left out of economy (and reported below)
    readable = bowling_data["balls_bowled"].notna()
    bowling_data = bowling_data.assign(runs_for_economy=bowling_data["runs"].where(readable))
    unreadable_overs = int((~readable).sum())

    summary = (
        bowling_data.groupby("player_key")
        .agg(Bowler=("player_name", "first"), Inns=("match_id", "size"), Wickets=("wickets", "sum"),
             Runs_Conceded=("runs", "sum"), Balls_Bowled=("balls_bowled", "sum"),
             Economy_Runs=("runs_for_economy", "sum"), Maidens=("maidens", "sum"))
        .reset_index()
        .rename(columns={"Runs_Conceded": "Runs Conceded", "Balls_Bowled": "Balls Bowled"})
    )
    summary["Overs"] = summary["Balls Bowled"].map(balls_to_overs)
    # Economy = runs conceded per over = runs x 6 / balls (balls avoid the 3.4-overs trap)
    summary["Economy"] = summary["Economy_Runs"] * 6 / summary["Balls Bowled"].replace(0, np.nan)
    summary["Average"] = summary["Runs Conceded"] / summary["Wickets"].replace(0, np.nan)
    summary["Team"] = summary["Bowler"].map(PLAYER_TEAM)
    summary.insert(0, "Logo", summary["Team"].map(lambda t: team_logo(t) if valid_team(t) else None))

    if search_bowler.strip():
        summary = summary[summary["Bowler"].astype(str).str.contains(
            search_bowler.strip(), case=False, na=False, regex=False)]
    summary = summary.sort_values(["Wickets", "Economy"], ascending=[False, True], na_position="last")

    if unreadable_overs:
        st.caption(f"{unreadable_overs} spell(s) have overs that could not be read; "
                   "they are left out of overs and economy.")

    if summary.empty:
        st.warning("No bowler matches that search. Check the spelling or clear the search box.")
    else:
        stat_strip([
            ("Bowlers", f"{len(summary):,}", None),
            ("Wickets", f"{summary['Wickets'].sum():,.0f}", None),
            ("Runs conceded", f"{summary['Runs Conceded'].sum():,.0f}", None),
            ("Maidens", f"{summary['Maidens'].sum():,.0f}", None),
        ])

        section_title("Leading wicket-takers")
        podium([
            {"name": row["Bowler"], "team": row["Team"], "main": f"{row['Wickets']:,.0f} wickets",
             "sub": f"Economy {row['Economy']:.2f}" if pd.notna(row["Economy"]) else "Economy –"}
            for _, row in summary.head(3).iterrows()
        ])

        left, right = st.columns(2, gap="large")
        with left:
            section_title("Top 10 wicket-takers", "By total wickets.")
            bar_chart(summary.head(10), "Bowler", "Wickets", PLAYER_COLOURS, height=360)
        with right:
            section_title("Wickets vs economy",
                          f"Bowlers with at least {min_overs} overs. Lower is better on the economy axis.")
            scatter_chart(summary[summary["Balls Bowled"] >= min_overs * 6], "Wickets", "Economy",
                          "Balls Bowled", "Bowler", "Wickets", "Economy", PLAYER_COLOURS)

        # Leaderboard sorted by the chosen column. Economy: lowest is best.
        # Overs are sorted using balls, because "10.2" overs is text.
        ranked = summary
        if sort_choice == "Economy":
            ranked = summary[summary["Balls Bowled"] >= min_overs * 6].sort_values("Economy", na_position="last")
        elif sort_choice == "Overs":
            ranked = summary.sort_values("Balls Bowled", ascending=False)
        else:
            ranked = summary.sort_values(sort_choice, ascending=False)
        show_all = st.checkbox("Show all bowlers (not just the top 10)", key="bowl_show_all")
        if not show_all:
            ranked = ranked.head(10)

        if sort_choice == "Economy":
            note = f"Sorted by economy, lowest first (at least {min_overs} overs)."
        else:
            note = f"Sorted by {sort_choice.lower()}, highest first."
        section_title("Bowling leaderboard", note)
        if ranked.empty:
            st.info("No bowlers meet the minimum overs. Lower the minimum to see more.")
        else:
            st.dataframe(
                ranked[["Logo", "Bowler", "Team", "Inns", "Overs", "Maidens",
                        "Runs Conceded", "Wickets", "Average", "Economy"]],
                **FULL_WIDTH, hide_index=True,
                column_config={
                    "Logo": st.column_config.ImageColumn("", width="small"),
                    "Wickets": st.column_config.NumberColumn(format="%d"),
                    "Runs Conceded": st.column_config.NumberColumn(format="%d"),
                    "Maidens": st.column_config.NumberColumn(format="%d"),
                    "Average": st.column_config.NumberColumn(format="%.2f"),
                    "Economy": st.column_config.NumberColumn(format="%.2f"),
                },
            )

        # --- One bowler's statistics and every spell ---
        section_title("Individual bowling records")
        bowler_names = dict(zip(summary["player_key"], summary["Bowler"]))
        chosen_key = st.selectbox("Choose a bowler", list(bowler_names),
                                  format_func=lambda key: bowler_names[key], key="selected_bowler")
        player = summary[summary["player_key"] == chosen_key].iloc[0]
        stat_strip([
            ("Spells", f"{player['Inns']:,}", None),
            ("Wickets", f"{player['Wickets']:,.0f}", None),
            ("Overs", player["Overs"], None),
            ("Economy", f"{player['Economy']:.2f}" if pd.notna(player["Economy"]) else "—", "runs per over"),
            ("Average", f"{player['Average']:.1f}" if pd.notna(player["Average"]) else "—", "runs per wicket"),
        ])
        spells = bowling_data[bowling_data["player_key"] == chosen_key].merge(
            matches[["match_id", "match_date", "home_team", "away_team"]], on="match_id", how="left"
        ).sort_values("match_date", ascending=False)
        spells["Date"] = spells["match_date"].map(format_date)
        spells["Match"] = spells["home_team"] + " vs " + spells["away_team"]
        spells["overs"] = spells["overs"].map(lambda value: "—" if pd.isna(value) else str(value))
        show_tidy_table(spells[["Date", "Match", "overs", "maidens", "runs", "wickets", "economy", "wides", "no_balls"]]
                        .rename(columns={"overs": "Overs", "maidens": "Maidens", "runs": "Runs conceded",
                                         "wickets": "Wickets", "economy": "Economy", "wides": "Wides",
                                         "no_balls": "No-balls"}))


# ============================================================
# 16. FOOTER
# ============================================================

show_html('<div class="small-footer">PSL Cricket Analytics · ETL + EDA academic project</div>')