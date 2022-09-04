from __future__ import print_function
import pickle as pickle
import sys
from Class_League import League
from Class_Schedule import Schedule


def main():
    league_management_url = "https://docs.google.com/spreadsheets/d/1oVsXCP48k_mLEKa0EgOdmHEAPgkPqMFh2tGQPSlqbW4"
    predefined_fixtures_url = "https://docs.google.com/spreadsheets/d/17LYXJaFKr7CiYkZI5yD_HyyY2_FAaw00AyqHrmvqMbE"

    league = reload_league_data_from_gsheet(_load_from_gsheets=True,
                                            _league_management_url=league_management_url)
    # Print League data stats
    league.check_league_data()

    league.write_teams_entered()

    # league.write_output()

    schedule_2021 = Schedule(league, predefined_fixtures_url)


def reload_league_data_from_gsheet(_load_from_gsheets: bool, _league_management_url: str) -> League:
    if _load_from_gsheets:
        sys.setrecursionlimit(100000)
        _league = League(_league_management_url)
        with open('league2022.pkl', 'ab'):
            pass
        with open('league2022.pkl', 'wb') as f:
            pickle.dump(_league, f)
        print("Session Saved")
    else:
        with open('league2022.pkl', 'rb') as f:
            _league = pickle.load(f)
        print("Session loaded")

    if _league:
        return _league
    else:
        print("Load Error")


if __name__ == '__main__':
    main()
