"""Main script to run the analysis."""

from __future__ import print_function

import pickle
import sys

from Class_League import League
from scheduling import Schedule


def main():
    """Run the analysis."""
    league_management_url = "https://docs.google.com/spreadsheets/d/1YhcIdtG2mSWujD7ZOJEqE7TyNL9FbCx58rP7NQTKfBg"
    predefined_fixtures_url = "https://docs.google.com/spreadsheets/d/1oZ2tPoIKX5V9Mvm70LplUPrivn8rW50wa5QmNBX2dwM"

    league = reload_league_data_from_gsheet(_load_from_gsheets=False, _league_management_url=league_management_url)
    # Print League data stats
    league.check_league_data()

    league.write_teams_entered()

    # league.write_output()

    min_incorrect_weeks = _get_min_incorrect_weeks(league, predefined_fixtures_url)
    max_prioritised_slots = _get_max_prioritised_slots(league, predefined_fixtures_url, min_incorrect_weeks)

    print(f"Min Incorrect Weeks = {min_incorrect_weeks}")
    print(f"max prioritised Slots = {max_prioritised_slots}")

    Schedule(
        league=league,
        predefined_fixtures_url=predefined_fixtures_url,
        allowed_run_time=1000,
        num_allowed_incorrect_fixture_week=min_incorrect_weeks,
        num_forced_prioritised_nights=max_prioritised_slots,
        write_output=True,
    )


def _get_min_incorrect_weeks(league, predefined_fixtures_url):
    for i in range(0, 30):
        print(f"Number Allowed incorrect week fixture = {i}")
        schedule = Schedule(
            league=league,
            predefined_fixtures_url=predefined_fixtures_url,
            allowed_run_time=1000,
            num_allowed_incorrect_fixture_week=i,
            write_output=False,
        )
        if schedule.model_result != "INFEASIBLE":
            return i
    return None


def _get_max_prioritised_slots(league, predefined_fixtures_url, min_incorrect_weeks):
    for i in range(0, 30):
        print(f"Number Prioritised Slots = {i}")
        schedule_2023 = Schedule(
            league=league,
            predefined_fixtures_url=predefined_fixtures_url,
            allowed_run_time=1000,
            num_allowed_incorrect_fixture_week=min_incorrect_weeks,
            num_forced_prioritised_nights=i,
            write_output=False,
        )
        if schedule_2023.model_result == "INFEASIBLE":
            return i - 1
    return None


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


if __name__ == "__main__":
    main()
