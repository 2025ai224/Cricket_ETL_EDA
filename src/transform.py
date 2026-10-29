
def transform_matches(matches):
    """
    Convert nested cricket match data into simple records.
    """

    transformed_matches = []

    # Process one match at a time
    for match in matches:

        # Get the team information
        home = match.get("home") or {}
        away = match.get("away") or {}
        score = match.get("score") or {}

        # Get the scores
        home_score = score.get("home")
        away_score = score.get("away")

        # Find the winner when both scores are available
        winner = None

        if home_score is not None and away_score is not None:
            if home_score > away_score:
                winner = home.get("name")
            elif away_score > home_score:
                winner = away.get("name")
            else:
                winner = "Tie"

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

    return transformed_matches
