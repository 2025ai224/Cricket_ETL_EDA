
import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# Find the main project folder
project_folder = Path(__file__).resolve().parent.parent

# Load the API key from the .env file
load_dotenv(project_folder / ".env")

# API address and raw data folder
api_url = "https://api.bigballsdata.com/v1/matches"
raw_folder = project_folder / "data" / "raw"


def extract_matches():
    # Get the API key
    api_key = os.getenv("BBS_API_KEY")

    if not api_key:
        raise ValueError("API key is missing. Check your .env file.")

    # Prepare the API request
    headers = {
        "Authorization": f"Bearer {api_key}"
    }

    all_matches = []
    page = 1

    while True:
        parameters = {
            "sport": "cricket",
            "league": "psl",
            "status": "finished",
            "limit": 200,
            "page": page
        }

        response = requests.get(
            api_url,
            headers=headers,
            params=parameters,
            timeout=30
        )

        response.raise_for_status()

        data = response.json()
        matches = data.get("data", [])

        if not matches:
            break

        all_matches.extend(matches)
        print(f"Page {page}: {len(matches)} matches extracted")

        if len(matches) < 200:
            break

        page += 1

    # Create the raw data folder if needed
    raw_folder.mkdir(parents=True, exist_ok=True)

    # Save the complete API response in a JSON file
    file_path = raw_folder / "matches.json"

    with open(file_path, "w", encoding="utf-8") as file:
            json.dump(all_matches, file, indent=4)

    print(f"Number of matches extracted: {len(all_matches)}")
    print(f"Raw data saved to: {file_path}")

    return all_matches


# Run this code when we execute extract.py directly
if __name__ == "__main__":
    matches = extract_matches()

    if matches:
        first_match = matches[0]

        print("\nFirst match:")
        print(first_match["home"]["name"], "vs", first_match["away"]["name"])
