from src.league_structure.league import League
from src.import_league import _get_id_from_url, load_league_data


def test_load_league_data():
    league_url = "https://docs.google.com/spreadsheets/d/1cN1hr5q8is1uMnm6_hI7YusYKAEfD6o5SVSGpodTyzw/edit?usp=sharing"
    league = load_league_data(league_url, use_cache=False)
    assert isinstance(league, League)


def test_get_id_from_url():
    url = "https://docs.google.com/spreadsheets/d/1cN1hr5q8is1uMnm6_hI7YusYKAEfD6o5SVSGpodTyzw/edit?usp=sharing"
    sheet_id = "1cN1hr5q8is1uMnm6_hI7YusYKAEfD6o5SVSGpodTyzw"
    assert _get_id_from_url(url) == sheet_id
