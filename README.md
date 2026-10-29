# PSL ETL + EDA Pipeline

## 1. Project Overview

This project builds an ETL pipeline using Pakistan Super League (PSL) cricket data from the BigBalls Sports Data API.

The pipeline will extract match and scorecard data, clean it using Pandas, validate it using Pydantic, save it in CSV files and an SQLite database, and perform exploratory data analysis (EDA).

## 2. Dataset

- Sport: Cricket
- Competition: Pakistan Super League (PSL)
- API provider: BigBalls Sports Data
- Catalogue count reported: 357 matches
- Planned scope: Completed PSL matches with available data

The 357 matches are the catalogue count. The number of matches and scorecards successfully extracted will be measured during the project.

## 3. API Endpoints Tested

- `GET /v1/cricket/series` — lists available cricket competitions.
- `GET /v1/matches` — successfully returned completed PSL match records.
- `GET /v1/cricket/matches/:id/scorecard` — returned batting and bowling statistics for a tested match.

The cricket-specific matches endpoint returned no results with the initial series filters. The general matches endpoint worked for PSL data.

## 4. Data Fields

### Match data
- Match ID
- League
- Home and away teams
- Scores
- Match date and status

### Batting data
- Player ID and name
- Runs and balls faced
- Fours and sixes
- Strike rate
- Dismissal type

### Bowling data
- Player ID and name
- Overs and maiden overs
- Runs conceded
- Wickets and economy rate
- Wides and no-balls

## 5. ETL Pipeline

1. Extract data from the API.
2. Transform and clean data with Pandas.
3. Validate records with Pydantic.
4. Load cleaned data into CSV files and SQLite.
5. Perform EDA using Pandas and Matplotlib.

## 6. Planned EDA

- Team wins and scoring performance
- Top run scorers
- Top wicket takers
- Bowling economy comparisons
- Data quality: missing values and duplicates

## 7. Security

The API key is stored locally in `.env`. It must not be committed to GitHub or included in shared screenshots, source code, or project reports.
