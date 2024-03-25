import pickle
import sys

from class_league import League


def reload_league_data_from_gsheet(_load_from_gsheets: bool, _league_management_url: str) -> League:
    """Reload the league data from the Google Sheet."""
    if _load_from_gsheets:
        sys.setrecursionlimit(100000)
        _league = League(_league_management_url)
        with open("league2022.pkl", "ab"):
            pass
        with open("league2022.pkl", "wb") as f:
            pickle.dump(_league, f)
        print("Session Saved")
    else:
        with open("league2022.pkl", "rb") as f:
            _league = pickle.load(f)
        print("Session loaded")

    if _league:
        return _league
    print("Load Error")
    return None

def load_league_data(league_management_url:str, use_cache: bool = False) -> League:
    """

    Load League Data

    Load data for a specific league from the league management URL.

    :param league_management_url: The URL of the league management system.
    :type league_management_url: str
    :param use_cache: Whether to use cached data if available. Default is False.
    :type use_cache: bool
    :return: The league data.
    :rtype: League

    """
    id = _get_id_from_url(league_management_url)
    if use_cache:
        return _load_from_pickle(True, id)
    league = _load_from_gsheet(league_management_url)
    _save_to_pickle(league,id)
    return league

def _load_from_gsheet(league_management_url: str) -> League:
    """Load the league data from google sheets"""
    pass

def _load_from_pickle(id: str) -> League:
    """Load the League Data from Pickle file"""
    with open(f'{id}.pkl', 'rb') as f:
        return pickle.load(f)

def _save_to_pickle(league: League, id:  str) -> None:
    """Save the league to pickle file"""
    with open(f'{id}.pkl', 'wb') as file:
        pickle.dump(league, file)

def _get_id_from_url(url: str) -> str:
    """returns the google sheets id from the url"""
    return url.split("/")[5]



