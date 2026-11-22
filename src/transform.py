import pandas as pd


def find_winner(home_name, away_name, home_innings, away_innings):
    """
    Decide the result from each team's innings scores (the API's "linescore").

    - If a team did not bat at all, the match was abandoned: no result (None).
    - Otherwise the team with more runs in the main innings wins.
    - If the main innings are tied, the super over (second number) decides.
    - If there is still no difference, the match is a tie.
    """
    if not home_innings or not away_innings:
        return None

    if home_innings[0] > away_innings[0]:
        return home_name
    if away_innings[0] > home_innings[0]:
        return away_name

    # Main innings tied: look at the super over, if one was played
    if len(home_innings) > 1 and len(away_innings) > 1:
        if home_innings[1] > away_innings[1]:
            return home_name
        if away_innings[1] > home_innings[1]:
            return away_name

    return "Tie"


def transform_matches(matches):
    """
    Convert nested cricket match data into simple, clean records.
    """

    transformed_matches = []

    # Process one match at a time
    for match in matches:

        # Get the team information
        home = match.get("home") or {}
        away = match.get("away") or {}
        score = match.get("score") or {}
        linescore = match.get("linescore") or {}

        # Runs of each innings, e.g. [121] or [121, 15] when there was a super over
        home_innings = linescore.get("home") or []
        away_innings = linescore.get("away") or []

        # Team score = the main innings only (super-over runs are not added).
        # A team that did not bat gets no score (None) instead of a misleading 0.
        if linescore:
            home_score = home_innings[0] if home_innings else None
            away_score = away_innings[0] if away_innings else None
            winner = find_winner(home.get("name"), away.get("name"), home_innings, away_innings)
        else:
            # Older API responses without a linescore: compare the total scores
            home_score = score.get("home")
            away_score = score.get("away")
            winner = find_winner(home.get("name"), away.get("name"), [home_score], [away_score])

        # Create a flat record for this match
        match_record = {
            "match_id": match.get("id"),
            "league": match.get("league"),
            "match_date": match.get("kickoff_utc"),
            "status": match.get("status"),
            "home_team": home.get("name"),
            "away_team": away.get("name"),
            "home_score": home_score,
            "away_score": away_score,
            "winner": winner
        }

        transformed_matches.append(match_record)

    # Clean the records with Pandas
    matches_df = pd.DataFrame(transformed_matches)

    # Remove repeated matches and extra spaces in team names
    matches_df = matches_df.drop_duplicates(subset="match_id")
    for column in ["home_team", "away_team", "winner"]:
        matches_df[column] = matches_df[column].str.strip()

    # Oldest match first (match_id breaks ties, so every run gives the same order)
    matches_df = matches_df.sort_values(["match_date", "match_id"])

    # Pandas uses NaN for empty values; Pydantic expects None
    matches_df = matches_df.astype(object).where(matches_df.notna(), None)

    return matches_df.to_dict("records")