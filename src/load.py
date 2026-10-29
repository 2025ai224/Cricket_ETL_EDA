
import sqlite3
from pathlib import Path

import pandas as pd


# Find the main project folder
project_folder = Path(__file__).resolve().parent.parent

# Choose where processed data will be saved
processed_folder = project_folder / "data" / "processed"


def load_matches(validated_matches):
    """
    Save validated match records to CSV and SQLite.
    """

    # Create the folder if it does not exist
    processed_folder.mkdir(parents=True, exist_ok=True)

    # Convert the records into a Pandas DataFrame
    matches_df = pd.DataFrame(validated_matches)

    # Save the records as a CSV file
    csv_path = processed_folder / "matches.csv"
    matches_df.to_csv(csv_path, index=False)

    # Set the database file path
    database_path = processed_folder / "cricket.db"

    # Connect to SQLite and save the records
    with sqlite3.connect(database_path) as connection:
        matches_df.to_sql(
            "matches",
            connection,
            if_exists="replace",
            index=False
        )

    print(f"Matches saved to CSV: {csv_path}")
    print(f"Matches saved to SQLite: {database_path}")
    print(f"Total matches loaded: {len(matches_df)}")




def load_player_performance(batting_records, bowling_records):
    """Save validated player records to CSV and SQLite."""

    processed_folder.mkdir(parents=True, exist_ok=True)

    batting_df = pd.DataFrame(batting_records)
    bowling_df = pd.DataFrame(bowling_records)

    # Save batting and bowling data as separate CSV files
    batting_df.to_csv(
        processed_folder / "batting.csv",
        index=False
    )

    bowling_df.to_csv(
        processed_folder / "bowling.csv",
        index=False
    )

    # Save both tables in the existing SQLite database
    database_path = processed_folder / "cricket.db"

    with sqlite3.connect(database_path) as connection:
        batting_df.to_sql(
            "batting",
            connection,
            if_exists="replace",
            index=False
        )

        bowling_df.to_sql(
            "bowling",
            connection,
            if_exists="replace",
            index=False
        )

    print(f"Batting records loaded: {len(batting_df)}")
    print(f"Bowling records loaded: {len(bowling_df)}")
