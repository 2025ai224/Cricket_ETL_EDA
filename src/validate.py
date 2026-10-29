
from pydantic import BaseModel, ConfigDict


class CricketMatch(BaseModel):
    # Allow extra API fields without causing an error
    model_config = ConfigDict(extra="ignore")

    match_id: str
    league: str | None = None
    match_date: str | None = None
    status: str | None = None
    home_team: str
    away_team: str
    home_score: int | None = None
    away_score: int | None = None
    winner: str | None = None


def validate_matches(matches):
    """
    Validate transformed match records with Pydantic.
    """

    validated_matches = []

    for match in matches:
        # Check the record against our model
        valid_match = CricketMatch.model_validate(match)

        # Convert the validated model back into a dictionary
        validated_matches.append(valid_match.model_dump())

    return validated_matches




from pydantic import BaseModel, ConfigDict


class BattingPerformance(BaseModel):
    model_config = ConfigDict(extra="ignore")

    match_id: str
    innings_number: int
    player_id: str
    player_name: str
    runs: int
    balls: int
    fours: int
    sixes: int
    strike_rate: float
    dismissal_type: str | None = None
    dismissal_bowler_id: str | None = None


class BowlingPerformance(BaseModel):
    model_config = ConfigDict(extra="ignore")

    match_id: str
    innings_number: int
    player_id: str
    player_name: str
    overs: str
    maidens: int
    runs: int
    wickets: int
    economy: float
    wides: int
    no_balls: int


def validate_batting_records(records):
    """Validate batting records once."""
    validated_records = []

    for record in records:
        player = BattingPerformance.model_validate(record)
        validated_records.append(player.model_dump())

    return validated_records


def validate_bowling_records(records):
    """Validate bowling records once."""
    validated_records = []

    for record in records:
        player = BowlingPerformance.model_validate(record)
        validated_records.append(player.model_dump())

    return validated_records
