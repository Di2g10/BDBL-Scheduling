from __future__ import print_function
import pickle as pickle
import sys


def main():
    league_management_url = "https://docs.google.com/spreadsheets/d/1il67Iw7e4w7QcA2Mf2w8DaZgV4qnOggOYHJIVfEV9Ew"
    predefined_fixtures_url = "https://docs.google.com/spreadsheets/d/1kcnj4X01u5wpCghAi1yDCEBR54bnGv69bx-hVXVljIk"

    league_2021 = reload_league_data_from_gsheet(_load_from_gsheets=True,
                                                 _league_management_url=league_management_url)
    # Print League data stats
    league_2021.check_league_data()

    # league_2021.write_teams_entered()

    # league_2021.write_output()

    schedule_2021 = Schedule(league_2021, predefined_fixtures_url)


def reload_league_data_from_gsheet(_load_from_gsheets: bool, _league_management_url):
    if _load_from_gsheets:
        sys.setrecursionlimit(100000)
        _league_2021 = League(_league_management_url)
        with open('league2021.pkl', 'ab'):
            pass
        with open('league2021.pkl', 'wb') as f:
            pickle.dump(_league_2021, f)
        print("Session Saved")
    else:
        with open('league2021.pkl', 'rb') as f:
            _league_2021 = pickle.load(f)
        print("Session loaded")

    if _league_2021:
        return _league_2021
    else:
        print("Load Error")


if __name__ == '__main__':
    main()
