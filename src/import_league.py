"""Contains functions for loading the league data from google sheets."""

import pickle


from src.league_structure.league import League


def load_league_data(league_management_url: str, use_cache: bool = False) -> League:
    """Load League Data

    Load data for a specific league from the league management URL.

    :param league_management_url: The URL of the league management system.
    :type league_management_url: str
    :param use_cache: Whether to use cached data if available. Default is False.
    :type use_cache: bool
    :return: The league data.
    :rtype: League

    """
    sheet_id = _get_id_from_url(league_management_url)
    if use_cache:
        return _load_from_pickle(sheet_id)
    league = _load_from_gsheet(league_management_url)
    _save_to_pickle(league, sheet_id)
    return league


def _load_from_gsheet(league_management_url: str) -> League:
    """Load the league data from Google sheets"""
    return League(league_management_url)


def _load_from_pickle(sheet_id: str) -> League:
    """Load the League Data from Pickle file"""
    with open(f"{sheet_id}.pkl", "rb") as f:
        return pickle.load(f)


def _save_to_pickle(league: League, sheet_id: str) -> None:
    """Save the league to pickle file"""
    with open(f"{sheet_id}.pkl", "wb") as file:
        pickle.dump(league, file)


def _get_id_from_url(url: str) -> str:
    """returns the google sheets id from the url"""
    return url.split("/")[5]
