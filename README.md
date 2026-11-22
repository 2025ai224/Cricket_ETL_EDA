# PSL Cricket Analytics — ETL + EDA Pipeline

An ETL pipeline and data analysis project using **Pakistan Super League (PSL)** cricket data from the **Big Balls Sports Data API**, with an interactive **Streamlit** dashboard.

**Live dashboard:** https://cricket-etl-eda.streamlit.app/
## Results

| Item | Count |
|---|---|
| Completed PSL matches (2016–2026) | 357 |
| Match scorecards | 357 |
| Batting records | 5,666 (422 unique batters) |
| Bowling records | 4,200 (300 unique bowlers) |

## Project structure

```
Cricket_ETL_EDA/
├── src/                      Python source code
│   ├── extract.py            E: get matches from the API          (requests)
│   ├── player_extract.py     E: get each match's scorecard         (requests)
│   ├── transform.py          T: flatten + clean match data         (pandas)
│   ├── player_transform.py   T: split scorecards into batting/bowling
│   ├── validate.py           T: check every record                 (pydantic)
│   ├── load.py               L: save to CSV and SQLite             (pandas, sqlite3)
│   ├── main.py               runs transform → validate → load
│   ├── app.py                Streamlit dashboard                   (streamlit, altair)
│   └── style.css             dashboard design
├── data/
│   ├── raw/                  API responses saved as JSON
│   └── processed/            matches.csv, batting.csv, bowling.csv, cricket.db
├── notebooks/
│   └── cricket_eda.ipynb     exploratory data analysis             (pandas, matplotlib)
├── assets/psl_hero.jpg       dashboard banner image
└── .streamlit/config.toml    dashboard theme
```

## How to run

```bash
pip install -r requirements.txt

# 1. Extract (needs an API key in a .env file:  BBS_API_KEY=your_key)
python -m src.player_extract      # downloads matches + scorecards into data/raw

# 2. Transform, validate and load (no API needed)
python -m src.main                # creates data/processed/*.csv and cricket.db

# 3. Dashboard
python -m streamlit run src/app.py
```

Open `notebooks/cricket_eda.ipynb` in Jupyter for the EDA.

## Data notes

- **Winner** comes from the innings scores. Abandoned matches (a team never batted) have **no result**. In tied matches the **super over** decides the winner, and super-over runs are not added to the team score.
- An empty **dismissal_type** means the batter was **not out**.
- Players are counted by **player_id**, because some names (e.g. Mohammad Irfan) belong to two different players.
- **Overs** use cricket notation: 3.4 overs = 3 overs + 4 balls = 22 balls.

## Security

The API key is stored only in a local `.env` file, which is listed in `.gitignore` and never committed.
