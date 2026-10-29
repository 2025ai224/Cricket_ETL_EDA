
def transform_player_scorecards(scorecards):
    """
    Separate scorecards into batting and bowling records.
    """

    batting_records = []
    bowling_records = []

    # Process each match scorecard
    for scorecard in scorecards:
        match_id = scorecard.get("match_id")

        # Each match can have multiple innings
        for innings in scorecard.get("innings", []):
            innings_number = innings.get("innings_number")

            # Extract batting performance
            for player in innings.get("batting", []):
                batting_record = {
                    "match_id": match_id,
                    "innings_number": innings_number,
                    "player_id": player.get("player_id"),
                    "player_name": player.get("player_name"),
                    "runs": player.get("runs"),
                    "balls": player.get("balls"),
                    "fours": player.get("fours"),
                    "sixes": player.get("sixes"),
                    "strike_rate": player.get("strike_rate"),
                    "dismissal_type": player.get("dismissal_type"),
                    "dismissal_bowler_id": player.get(
                        "dismissal_bowler_id"
                    )
                }

                batting_records.append(batting_record)

            # Extract bowling performance
            for player in innings.get("bowling", []):
                bowling_record = {
                    "match_id": match_id,
                    "innings_number": innings_number,
                    "player_id": player.get("player_id"),
                    "player_name": player.get("player_name"),
                    "overs": player.get("overs"),
                    "maidens": player.get("maidens"),
                    "runs": player.get("runs"),
                    "wickets": player.get("wickets"),
                    "economy": player.get("economy"),
                    "wides": player.get("wides"),
                    "no_balls": player.get("no_balls")
                }

                bowling_records.append(bowling_record)

    return batting_records, bowling_records
