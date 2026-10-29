
import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

from src.extract import extract_matches


# Find the project folder
project_folder = Path(__file__).resolve().parent.parent

# Load the API key
load_dotenv(project_folder / ".env")

# API address and raw data folder
api_url = "https://api.bigballsdata.com"
raw_folder = project_folder / "data" / "raw"


def extract_player_scorecards(matches):
    """
    Fetch and save the scorecard for each match.
    """

    api_key = os.getenv("BBS_API_KEY")

    if not api_key:
        raise ValueError("API key is missing. Check your .env file.")

    headers = {
        "Authorization": f"Bearer {api_key}"
    }

    all_scorecards = []

    # Request a scorecard for each match
    for match in matches:
        match_id = match["id"]

        url = f"{api_url}/v1/cricket/matches/{match_id}/scorecard"

        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )

        # Stop if the API request failed
        response.raise_for_status()

        result = response.json()

        # Get the scorecard data
        scorecard = result.get("data")

        if not scorecard:
            print(f"No scorecard data returned for match: {match_id}")
            continue

        # Keep the match ID with the complete scorecard
        all_scorecards.append(scorecard)

        print(f"Scorecard extracted: {match_id}")

    # Create the raw folder if needed
    raw_folder.mkdir(parents=True, exist_ok=True)

    # Save the original scorecard data
    file_path = raw_folder / "player_scorecards.json"

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(all_scorecards, file, indent=4)

    print(f"\nScorecards extracted: {len(all_scorecards)}")
    print(f"Raw scorecards saved to: {file_path}")

    return all_scorecards


if __name__ == "__main__":
    # Get the matches already supported by our pipeline
    matches = extract_matches()

    # Extract their player scorecards
    if matches:
        extract_player_scorecards(matches)
    else:
        print("No matches available for scorecard extraction.")
