from app.services.nrfi_yrfi_module import NRFIYRFIModule

from app.data.ballpark_data import BALLPARK_DATABASE
from app.data.pitchers_data import PITCHER_DATABASE
from app.data.rpg_data import RPG_DATABASE
from app.data.team_data import TEAM_DATABASE
from app.data.teamnames import TEAM_NAME_MAPPING

engine = NRFIYRFIModule(
    pitcher_db=PITCHER_DATABASE,
    team_db=TEAM_DATABASE,
    ballpark_db=BALLPARK_DATABASE,
    rpg_db=RPG_DATABASE,
    team_name_mapping=TEAM_NAME_MAPPING
)

sonuc_1 = engine.calculate(
    away_team="New York Yankees",
    home_team="Pittsburgh Pirates",
    away_pitcher="Luis Gil",
    home_pitcher="Paul Skenes"
)
print(f"Yankees vs Pirates (Gil vs Skenes) NRFI/YRFI Confidence: {sonuc_1}")

sonuc_2 = engine.calculate(
    away_team="Unknown Team",
    home_team="Chicago Cubs",
    away_pitcher="Bilinmeyen Atici 1",
    home_pitcher="Bilinmeyen Atici 2"
)
print(f"Rookie Testi (Çökmemesi lazım): {sonuc_2}")