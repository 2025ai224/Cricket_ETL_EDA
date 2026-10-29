
import json
from pathlib import Path

from src.transform import transform_matches
from src.validate import (
    validate_matches,
    validate_batting_records,
    validate_bowling_records,
)
from src.load import load_matches, load_player_performance
from src.player_transform import transform_player_scorecards


def main():
    # Find the project folder
    project_folder = Path(__file__).resolve().parent.parent
    raw_folder = project_folder / "data" / "raw"

    # Step 1: Load previously extracted match data
    with open(raw_folder / "matches.json", "r", encoding="utf-8") as file:
        raw_matches = json.load(file)

    print(f"Matches loaded: {len(raw_matches)}")

    # Step 2: Transform match data
    transformed_matches = transform_matches(raw_matches)

    # Step 3: Validate match records
    validated_matches = validate_matches(transformed_matches)

    # Step 4: Load match records
    load_matches(validated_matches)

    # Step 5: Load previously extracted player scorecards
    with open(
        raw_folder / "player_scorecards.json", "r", encoding="utf-8"
    ) as file:
        scorecards = json.load(file)

    print(f"Scorecards loaded: {len(scorecards)}")

    # Step 6: Transform scorecards into batting and bowling records
    batting, bowling = transform_player_scorecards(scorecards)

    # Step 7: Validate player records
    valid_batting = validate_batting_records(batting)
    valid_bowling = validate_bowling_records(bowling)

    # Step 8: Load player records
    load_player_performance(valid_batting, valid_bowling)

    print("\nETL pipeline completed successfully!")


if __name__ == "__main__":
    main()
