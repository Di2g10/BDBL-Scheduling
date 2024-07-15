import pickle
import warnings
from pathlib import Path


from src.league_structure.league import League
from src.import_league import _get_id_from_url, load_league_data, get_path_to_data_folder


def test_load_league_data():
    league_url = "https://docs.google.com/spreadsheets/d/1cN1hr5q8is1uMnm6_hI7YusYKAEfD6o5SVSGpodTyzw/edit?usp=sharing"
    file_id = _get_id_from_url(league_url)
    Path.unlink(Path(f"{file_id}.pkl"), missing_ok=True)
    league = load_league_data(league_url, use_cache=False)
    assert isinstance(league, League)
    # check cache created
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        league2 = load_league_data(league_url, use_cache=True)
    # check cache created league is a League
    assert isinstance(league2, League)
    # check the caches league is the same as the imported league
    assert league == league2
    # remove cache
    Path.unlink(Path(f"{file_id}.pkl"), missing_ok=True)


def test_load_league_data_cache():
    dummy_url = "https://docs.google.com/spreadsheets/d/12345"
    file_id = _get_id_from_url(dummy_url)
    path = get_path_to_data_folder(file_id)
    with open(path, "wb") as file:
        pickle.dump("dummy_string", file)
    dummy_league = load_league_data(dummy_url, use_cache=True)
    assert dummy_league == "dummy_string"


def test_get_id_from_url():
    url = "https://docs.google.com/spreadsheets/d/1cN1hr5q8is1uMnm6_hI7YusYKAEfD6o5SVSGpodTyzw/edit?usp=sharing"
    sheet_id = "1cN1hr5q8is1uMnm6_hI7YusYKAEfD6o5SVSGpodTyzw"
    assert _get_id_from_url(url) == sheet_id
