from __future__ import print_function
from typing import List, Tuple, Dict, Any, Union
from ortools.sat.python import cp_model
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from pathlib import Path
from datetime import datetime, timedelta, date

from ortools.sat.python.cp_model import IntVar, CpModel

import pandas as pd

# test savings

# Import class Objects
from Class_League import League, Club, Dates, Date, Team, CourtSlot


def main():
    league_url = "https://docs.google.com/spreadsheets/d/1il67Iw7e4w7QcA2Mf2w8DaZgV4qnOggOYHJIVfEV9Ew/edit#gid=310653139"
    test_league = League(league_url)
    run_schedule(test_league)


def run_schedule(_league: League):
    # Get League info from GoogleSheet OLD
    # teams2019: Union[List[Any], List[Dict[Any, Any]]] = get_gsheet_data('League Composition')
    # print("teams2019")
    # for team in teams2019:
    #     print(team)

    # Filter Some Teams for Test
    # teams2019 = teams2019[0:len(teams2019)]

    # home_dates = get_gsheet_data('Home Dates Available')
    # home_dates_sorted = sorted(home_dates, key=lambda k: (k['Club'], k['Week']))
    # home_dates_available = [date for date in home_dates_sorted if date['Available?'] == 1]
    # for date_id, date in enumerate(home_dates_available):
    #     str_date_value: str = date['Date']
    #     home_dates_available[date_id]["Date"] = datetime.strptime(str_date_value, "%d/%m/%Y")
    #     home_dates_available[date_id]["ID"] = date_id
    #
    # print("home_dates_available")
    # for home_date in home_dates_available:
    #     print(home_date)
    #
    # # Warning contains duplicated clubs where they play on multiple home nights
    # club_night_info = get_gsheet_data('Club Info')
    # print("club_info")
    # for club_night in club_night_info:
    #     print(club_night)
    #
    # league_dates = get_gsheet_data('League Dates')
    # print("League Dates")
    # for league_date in league_dates:
    #     print(league_date)
    #
    # for week_id, week_info in enumerate(league_dates):
    #     str_date_value = week_info['League Weeks']
    #     league_dates[week_id]['League Weeks'] = datetime.strptime(str_date_value, "%d/%m/%Y")
    #
    # dates = [home_date['Date'] for home_date in home_dates_available]
    # start_date: object = min(dates)
    # delta = timedelta(days=start_date.weekday())
    # start_date_week = start_date - delta
    # end_date = max(dates)
    #
    # for date_id, date_info in enumerate(home_dates_available):
    #     date_value = date_info['Date']
    #     home_dates_available[date_id]['Date Number'] = (date_value - start_date).days
    #
    # for week_id, week_info in enumerate(league_dates):
    #     date_value = week_info['League Weeks']
    #     league_dates[week_id]['Week Number'] = (date_value - start_date_week).days // 7
    #
    # max_concurrent_matches = max(club_night['Number of Concurrent Matches'] for club_night in club_night_info)
    # print(start_date_week, " (", start_date, ") to ", end_date)

    # This program tries to find an optimal assignment of nurses to matches
    # (3 matches per day, for 7 days), subject to some constraints (see below).
    # Each nurse can request to be assigned to specific matches.
    # The optimal assignment maximizes the number of fulfilled shift requests.

    season_start_day_num: int = 0
    season_end_day_num = (end_date - start_date).days
    season_start_week = season_start_day_num // 7
    season_end_week = season_end_day_num // 7
    season_midpoint_date = datetime(int(end_date.year), 1, 1)
    season_midpoint_num = (season_midpoint_date - start_date).days
    days_between_matches = 1  # Need to optimise to get this difference higher on average.
    allow_diff_hm_av_pre_xmas = 2

    # Creates the model.
    model: CpModel = cp_model.CpModel()

    # Creates match variables.
    # matches[(h, a)]: Home Team 'h' Plays against away team 'a'value is the day of the match
    # For team pairs that are different but in the same league and Division
    #   create a variable that is the day of match schedule
    matches_day: dict[Tuple[int, int], IntVar] = {}
    matches_week: dict[Tuple[int, int], IntVar] = {}
    matches_court: dict[Tuple[int, int], IntVar] = {}  # corresponds to the match night ID for the home dates available
    matches_correct_week: dict[Tuple[int, int], IntVar] = {}
    matches_is_pre_xmas: dict[Tuple[int, int], IntVar] = {}
    teams_diff_hm_aw_pre_xmas: dict[int, IntVar] = {}

    # Fix ID Values within team table to match list position
    for team_id, team in enumerate(teams2019):
        teams2019[team_id]['ID'] = team_id

    # Create the model Variables
    for home_team_id, team in enumerate(teams2019):
        for away_team_id, awteam in enumerate(teams2019):
            if team != awteam and team['League'] == awteam['League'] and team['Division'] == awteam['Division']:
                home_club = team["Club"]
                match_team_pair = (home_team_id, away_team_id)
                # Create the match day variable
                matches_day[match_team_pair] = model.NewIntVar(season_start_day_num,
                                                               season_end_day_num,
                                                               'Match_day_h%i_vs_a%i' % match_team_pair)

                # Create the match week variable
                matches_week[match_team_pair] = model.NewIntVar(season_start_week,
                                                                season_end_week,
                                                                'Match_week_h%i_vs_a%i' % match_team_pair)

                # For which court group the match should be played on.
                bounds = get_club_home_date_bound(home_club, home_dates_available)
                lower_bound = bounds[0]
                upper_bound = bounds[1]
                matches_court[match_team_pair] = model.NewIntVar(lower_bound, upper_bound,
                                                                 'Match_court_h%i_vs_a%i' % match_team_pair)

                matches_correct_week[match_team_pair] = model.NewBoolVar('Match_court_day_h%i_vs_a%i'
                                                                         % match_team_pair)
                matches_is_pre_xmas[match_team_pair] = model.NewIntVar(0, 1, 'Match_is_pre_xmas_h%i_vs_a%i'
                                                                       % match_team_pair)
        # Create variable for the allowed difference between no. home and no. away games before and after  christmas
        teams_diff_hm_aw_pre_xmas[home_team_id] = model.NewIntVar(- allow_diff_hm_av_pre_xmas,
                                                                  allow_diff_hm_av_pre_xmas,
                                                                  'Team_HmAw_Diff_PreXmas_t%i' % home_team_id)

    print("Matches to be scheduled:", len(matches_court))

    # Control the pre christmas Boolean variable
    create_condition_match_pre_xmas(model, matches_is_pre_xmas, teams2019,
                                    teams_diff_hm_aw_pre_xmas, season_midpoint_num)

    # Ensure Multiple matches can't be assigned to the same courts (replaced above rule)
    model.AddAllDifferent(matches_court.values())

    # Get all the matches for each team and ensure they are all scheduled to different weeks
    for team in teams2019:
        teams_matches_week = get_team_matches(team, matches_week, teams2019)
        model.AddAllDifferent(teams_matches_week.values())

    # ensure matches are on home nights for teams
    create_condition_team_match_weekday(model, club_night_info, teams2019, home_dates_available,
                                        matches_court, matches_day, matches_week, matches_is_pre_xmas,
                                        start_date_week, season_midpoint_num)

    # Ensure for teams likely to share players ensure they are have some separation
    create_condition_intersect_team_match_separation(
        model, matches_day, teams2019, season_start_day_num, season_end_day_num, days_between_matches)

    # Ensure within club matches are scheduled before between club matches
    create_condition_inter_club_match_first(model, matches_day, teams2019)

    # Support the matches correct week variable to be fixed dependant on the week of the scheduled match.
    create_objective_function_match_league_to_week(model, teams2019, matches_week, matches_correct_week, league_dates)

    # Attempts to schedule all matches in correct week where possible
    number_of_matches = len(matches_day)
    model.Minimize(number_of_matches - sum(matches_correct_week[match_key] for match_key in matches_day))

    # Checks that there are enough dates available to schedule matches for each team.
    check_feasibility(club_night_info, teams2019, matches_day, matches_week, matches_correct_week, home_dates_available)

    # Function to run current model and print the results locally and to Google sheets
    run_model(model, teams2019, matches_day, matches_week, matches_correct_week, matches_court, matches_is_pre_xmas,
              teams_diff_hm_aw_pre_xmas)

    print()
    print("Stats:")
    print(model.ModelStats())


def check_feasibility(_club_nights, _teams, _matches_day, _matches_week, _matches_correct_week, _home_dates):
    print("---------------------------Feasibility Check---------------------------")
    for _club_night in _club_nights:
        _club_night_teams = get_teams_in_club_night(_teams, _club_night)
        _club_night_matches = {}
        _num_club_level_matches = 0
        _num_club_mixed_matches = 0
        for _team in _club_night_teams:
            _club_night_team_matches = get_team_matches(_team, _matches_day, _teams,
                                                        _get_home_matches=True, _get_away_matches=False)
            if _team["League"] == "Mixed":
                _num_club_mixed_matches += len(_club_night_team_matches)
            else:
                _num_club_level_matches += len(_club_night_team_matches)
            _club_night_matches.update(_club_night_team_matches)
        _num_club_matches = len(_club_night_matches)

        _club_night_dates_available = get_home_dates_for_club_night(_club_night, _home_dates)

        _num_club_home_dates_available = len(_club_night_dates_available)
        club_night_info_list = ["Club night:", _club_night['Club Name'], "-", _club_night['Match Night'],
                                "Matches to schedule: ", _num_club_matches,
                                "Home Night Available: ", _num_club_home_dates_available]
        print(club_night_info_list)
        print("Level Matches: ", _num_club_level_matches, "Mixed Matches: ",_num_club_mixed_matches)
        print()


def run_model(_model, _teams, _matches_day, _matches_week, _matches_correct_week, _matches_court, _matches_is_pre_xmas,
              _teams_diff_hm_aw_pre_xmas):
    # Amends the OnSolution Callback Function in the solution class of the model
    class SolutionCallback(cp_model.CpSolverSolutionCallback):

        def __init__(self):
            cp_model.CpSolverSolutionCallback.__init__(self)

        def OnSolutionCallback(self):
            print("Objective Value: ", self.ObjectiveValue())
            print("Objective Bound: ", self.BestObjectiveBound())
            print("Timestamp: ", self.UserTime())
            print()
            return True

    # Creates the solver and solve.
    print("Started Model Run")
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 2000.0
    sc = SolutionCallback()
    status_num = solver.SolveWithSolutionCallback(_model, sc)

    status_name = solver.StatusName(status_num)
    print("Status:")
    print(status_name)
    objective_value = solver.ObjectiveValue()
    print("Objective Value: ", objective_value)
    if status_name in ["FEASIBLE", "OPTIMAL"]:
        # Print Results
        match_schedule_results = {}
        for team_id, team in enumerate(_teams):
            team_matches = get_team_matches(team, _matches_day, _teams)
            teams_matches_weeks = get_team_matches(team, _matches_week, _teams)
            _teams_matches_court = get_team_matches(team, _matches_court, _teams)
            num_scheduled_matches = 0
            for match in team_matches:
                match_day = solver.Value(team_matches[match])
                match_week = solver.Value(teams_matches_weeks[match])
                match_night = solver.Value(_teams_matches_court[match])
                match_correct_week = solver.Value(_matches_correct_week[match])
                match_is_pre_xmas = solver.Value(_matches_is_pre_xmas[match])
                home_team_id = match[0]
                home_team = _teams[home_team_id]
                home_team_name = home_team['Team Name']
                away_team_id = match[1]
                away_team = _teams[away_team_id]
                away_team_name = away_team['Team Name']
                num_scheduled_matches += 1
                match_schedule_result = {'Home Team ID': home_team_id,
                                         'Away Team ID': away_team_id,
                                         'Home Team': home_team_name,
                                         'Away Team': away_team_name,
                                         'Match Day': match_day,
                                         'Match Week': match_week,
                                         'Match Night': match_night,
                                         'Match Correct week': match_correct_week,
                                         'Match is Pre Christmas': match_is_pre_xmas}
                match_schedule_results[match] = match_schedule_result
            _teams[team_id]['Scheduled Matches'] = num_scheduled_matches
            _teams[team_id]['Diff_in_Hm_vsAw'] =  solver.Value(_teams_diff_hm_aw_pre_xmas[home_team_id])

        df_teams2019 = pd.DataFrame(_teams)
        write_gsheet_output_data(df_teams2019, 'Teams2019_Output')

        df_match_schedule_results = pd.DataFrame(match_schedule_results)
        df_match_schedule_results = df_match_schedule_results.T
        write_gsheet_output_data(df_match_schedule_results, 'match_schedule_results')

        # Last Match Day
        print("last Match Day:")
        last_match_day = max(solver.Value(_matches_day[match_key]) for match_key in _matches_day)
        print(last_match_day)


def remove_duplicates(x):
    return list(dict.fromkeys(x))


def get_gsheet_data(_sheet_name):
    _scope = Path(
         "C:/Users/David Irvine/Google Drive/Basingstoke Badminton Scheduling/2020-2021_Python/client_secret.json")
        # "C:/Users/annan/Google Drive/Basingstoke Badminton Scheduling/2020-2021_Python/client_secret.json")
    _credentials = ServiceAccountCredentials.from_json_keyfile_name(_scope)
    _client = gspread.authorize(_credentials)
    _worksheet = _client.open_by_url(
        'https://docs.google.com/spreadsheets/d/1Zvzt_GJ-wYF6WQnlGI3PjzZWM9sL83Q_dn6WFH7nwjQ').worksheet(_sheet_name)
    # 'https://docs.google.com/spreadsheets/d/1Zvzt_GJ-wYF6WQnlGI3PjzZWM9sL83Q_dn6WFH7nwjQ' #2019
    # 'https://docs.google.com/spreadsheets/d/1PEM2XDwO6bWcjlLaTLd5TyYY6UcUVmwqeoW6EmgwLUg' #2019 Ladies only
    # 'https://docs.google.com/spreadsheets/d/1VF2Vdbq396Oh9uVpz271h9-KqGAMHakUcpagzTw_toU' #2019 Ladies & Mixed
    # 'https://docs.google.com/spreadsheets/d/11srwFZsE5wlfp_c_PKk7RLQEjc4CXiGuWwCFXKT0mBU' #2019 Mens
    # 'https://docs.google.com/spreadsheets/d/10siV240nRv5O0XsblrdNTjJ2huK8WxM5V2hVrahP16Q' #2019 Mens & Mixed
    _data = _worksheet.get_all_records()
    return _data


def write_gsheet_output_data(_output_data, _sheet_name):
    _scope = Path(
        "C:/Users/David Irvine/Google Drive/Basingstoke Badminton Scheduling/2020-2021_Python/client_secret.json")
    _credentials = ServiceAccountCredentials.from_json_keyfile_name(_scope)
    _client = gspread.authorize(_credentials)
    _spreadsheet = _client.open_by_url(
        'https://docs.google.com/spreadsheets/d/1Zvzt_GJ-wYF6WQnlGI3PjzZWM9sL83Q_dn6WFH7nwjQ')
    _worksheet_list = _spreadsheet.worksheets()
    _does_sheet_exists = False
    for _worksheet in _worksheet_list:
        if _worksheet.title == _sheet_name:
            _does_sheet_exists = True
            _output_worksheet = _worksheet

    if not _does_sheet_exists:
        _output_worksheet = _spreadsheet.add_worksheet(title=_sheet_name, rows="100", cols="20")
        print("sheet created Called ", _output_worksheet)

    _output_worksheet.clear()
    _output_worksheet.update([_output_data.columns.values.tolist()] + _output_data.values.tolist())


# Function to return all matches for a specified team from a list of matches
def get_team_matches(_team, _matches, _teams, _get_home_matches=True, _get_away_matches=True):
    _teams_matches: Dict[Tuple[int, int], IntVar] = {}
    _home_match_count = 0
    _away_match_count = 0
    for _match in _matches:
        _team_home_id = _match[0]
        _team_away_id = _match[1]
        _is_home_team = _team_home_id == _team["ID"]
        _is_away_team = _team_away_id == _team["ID"]

        if _get_home_matches and _is_home_team:
            _teams_matches[_match] = _matches[_match]
            _home_match_count += 1
        elif _get_away_matches and _is_away_team:
            _teams_matches[_match] = _matches[_match]
            _away_match_count += 1

    if ((_get_home_matches is False and _home_match_count > 0)
        or (_get_away_matches is False and _away_match_count > 0)):
        print("error on get team matches, returned invalid matches for configuration")
    else:
        return _teams_matches


# Function to return all teams that need to avoid scheduling conflicts due to potential overlap of players
def get_intersecting_teams(_selected_team, _teams):
    _intersecting_teams = []
    for _Potential_intersect_team in _teams:
        # Define conditions for team to intersect
        _is_team_same_club = _selected_team['Club'] == _Potential_intersect_team['Club']
        _is_team_different = _selected_team != _Potential_intersect_team
        _is_team_consecutive_rank = abs(_selected_team['Team Rank'] - _Potential_intersect_team['Team Rank']) <= 1
        _is_league_gender_overlap = _selected_team['League'] == "Mixed" or \
                                    _Potential_intersect_team['League'] == "Mixed" or \
                                    _selected_team['League'] == _Potential_intersect_team['League']
        _is_league_different = _selected_team['League'] != _Potential_intersect_team['League']
        if _is_team_same_club \
                and _is_team_different \
                and _is_team_consecutive_rank \
                and _is_league_gender_overlap \
                and _is_league_different:
            _intersecting_teams.append(_Potential_intersect_team)
    return _intersecting_teams


# Number of days between 2 dates
def days_between(d1, d2):
    d1 = datetime.strptime(d1, "%d/%m/%Y")
    d2 = datetime.strptime(d2, "%d/%m/%Y")
    return abs((d2 - d1).days)


# Ensure for teams likely to share players ensure they are have some separation
def create_condition_intersect_team_match_separation(
        _model: CpModel,
        _matches: Dict[Tuple[int, int], IntVar],
        _teams: Union[List[Any], List[Dict[Any, Any]]],
        _season_start_day,
        _season_end_day,
        _match_separation_distance):
    _matches_intervals: Dict[Tuple[int, int], IntVar] = {}
    _matches_interval_end: Dict[Tuple[int, int], IntVar] = {}
    for _match in _matches:
        _matches_interval_end[_match] = _model.NewIntVar(_season_start_day + _match_separation_distance,
                                                         _season_end_day + _match_separation_distance,
                                                         'Match_day_end_h%i_vs_a%i' % _match)

        _matches_intervals[_match] = _model.NewIntervalVar(_matches[_match],
                                                           _match_separation_distance,
                                                           _matches_interval_end[_match],
                                                           'Match_day_interval_h%i_vs_a%i' % _match)
    for _team in _teams:
        _team_matches_interval = get_team_matches(_team, _matches_intervals, _teams)
        _intersecting_teams = get_intersecting_teams(_team, _teams)

        # get set of all the matches for intersecting teams
        _intersect_team_week_matches = []
        for _intersect_team in _intersecting_teams:
            for _match_week in get_team_matches(_intersect_team, _matches_intervals, _teams):
                _home_club = _teams[_match_week[0]]['Club']
                _away_club = _teams[_match_week[1]]['Club']
                if _home_club != _away_club:
                    _intersect_team_week_matches.append(_match_week)
        # Remove Duplicates from list of matches (not implemented yet), May not be Necessary

        # Define rule
        for _team_match_week_id in _team_matches_interval:
            _team_match_week = _matches_intervals[_team_match_week_id]
            for _intersect_team_match_week_id in _intersect_team_week_matches:
                _intersect_team_match_week = _matches_intervals[_intersect_team_match_week_id]
                _model.AddNoOverlap((_team_match_week, _intersect_team_match_week))


# Create Rule for Inter Club Matches to happen first
def create_condition_inter_club_match_first(
        _model: CpModel,
        _match_days,
        _teams,):
    for _team in _teams:
        # Get other teams in the same club as selected team.
        _team_id = _team["ID"]
        _team_match_days = get_team_matches(_team, _match_days, _teams,
                                            _get_home_matches=True, _get_away_matches=True)
        _teams_in_club = get_teams_in_club(_teams, _team["Club"])
        _club_alt_team_ids = [_alt_team["ID"] for _alt_team in _teams_in_club
                              if _alt_team["ID"] != _team_id]

        # Get categories all team matches into those against same team & those against different team.
        _within_club_matches: Dict[Tuple[int, int], IntVar] = {}
        _between_club_matches: Dict[Tuple[int, int], IntVar] = {}
        for _match in _team_match_days:
            _team_home_id = _match[0]
            _team_away_id = _match[1]
            if _team_home_id in _club_alt_team_ids or _team_away_id in _club_alt_team_ids:
                _within_club_matches[_match] = _team_match_days[_match]
            else:
                _between_club_matches[_match] = _team_match_days[_match]

        # Create Rules to schedule within club matches before between club matches
        for _w in _within_club_matches:
            for _b in _between_club_matches:
                _model.Add(_within_club_matches[_w] < _between_club_matches[_b])


def create_condition_team_match_weekday(
        _model: CpModel,
        _clubs,
        _teams,
        _home_dates_available,
        _match_courts,
        _match_days,
        _match_weeks,
        _match_is_pre_xmas,
        _start_date_week,
        _midpoint_day):
    # create_condition_team_match_weekday(model, club_night_info, teams2019,
    #                                     matches_court, matches_day, matches_week,home_dates_available)

    # User modular equality to ensure each team can only be scheduled on correct day.
    _weekday_numbers = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')
    _match_court_day_week_assignments = []
    for _home_date in _home_dates_available:
        _match_court_number = _home_date["ID"]
        _match_day_number = (_home_date["Date"] - _start_date_week).days
        _match_week_number = _match_day_number // 7
        _match_is_pre_xmas_bool = _match_day_number < _midpoint_day
        _match_court_day_week_assignment = (_match_court_number,
                                            _match_day_number,
                                            _match_week_number,
                                            _match_is_pre_xmas_bool)
        _match_court_day_week_assignments.append(_match_court_day_week_assignment)

    for _team in _teams:
        _home_matches = get_team_matches(_team, _match_days, _teams, _get_home_matches=True, _get_away_matches=False)
        for _match in _home_matches:
            _model.AddAllowedAssignments([_match_courts[_match],
                                          _match_days[_match],
                                          _match_weeks[_match],
                                          _match_is_pre_xmas[_match]],
                                         _match_court_day_week_assignments)


def create_condition_match_pre_xmas(
        _model: CpModel,
        _matches_is_pre_xmas,
        _teams,
        _teams_diff_hm_aw_pre_xmas,
        _season_midpoint_num):
    for _team_id, _team in enumerate(_teams):
        # XOr is true only if strictly one value is true so either match is after midpoint or match pre midpoint is true
        _team_home_matches = get_team_matches(_team, _matches_is_pre_xmas, _teams,
                                              _get_home_matches=True, _get_away_matches=False)
        _team_away_matches = get_team_matches(_team, _matches_is_pre_xmas, _teams,
                                              _get_home_matches=False, _get_away_matches=True)
        _no_pre_xmas_home_matches = sum(_matches_is_pre_xmas[_match] for _match in _team_home_matches)
        _no_pre_xmas_away_matches = sum(_matches_is_pre_xmas[_match] for _match in _team_away_matches)
        _bound = _teams_diff_hm_aw_pre_xmas[_team_id]
        _model.Add(_no_pre_xmas_home_matches - _no_pre_xmas_away_matches == _bound)


def get_teams_in_club_night(
        _teams,
        _club_night):
    _club_teams = []
    for _team in _teams:
        if _team['Club'] == _club_night['Club Name']\
                and _team['Match Night'] == _club_night['Match Night']:
            _club_teams.append(_team)
    return _club_teams


def get_teams_in_club(
        _teams,
        _club: str):
    _club_teams = []
    for _team in _teams:
        if _team['Club'] == _club:
            _club_teams.append(_team)
    return _club_teams


def get_club_home_date_bound(_club, _home_dates_available):
    _home_dates_sorted = sorted(_home_dates_available, key=lambda k: (k['Club'], k['Week']))
    home_dates_sort_check = [date for date in _home_dates_sorted if date['Available?'] == 1]
    if home_dates_sort_check != _home_dates_available:
        print("Home Dates Not Sorted Correctly")
    _club_home_night_ids = [_home_date["ID"] for _home_date in _home_dates_available if _home_date["Club"] == _club]
    _lower_bound = min(_club_home_night_ids)
    _upper_bound = max(_club_home_night_ids)
    return [_lower_bound, _upper_bound]


def get_home_dates_for_club_night(_club_night: str, _home_dates):
    _club_night_home_dates = []
    for _home_date in _home_dates:
        if _home_date["Club"] == _club_night["Club Name"] \
                and _home_date["Night"] == _club_night["Match Night"]\
                and _home_date["Available?"] == 1:
            _club_night_home_dates.append(_home_date)
    return _club_night_home_dates


def create_objective_function_match_league_to_week(
        _model: CpModel,
        _teams,
        _match_weeks,
        _matches_correct_week,
        _league_dates):
    _level_weeks_acceptable_assignment = []
    _mixed_weeks_acceptable_assignment = []

    for _week in _league_dates:
        _week_number = _week["Week Number"]
        if _week["League Type"] == "Level":
            _level_weeks_acceptable_assignment.append((_week_number, 1))
            _mixed_weeks_acceptable_assignment.append((_week_number, 0))
        elif _week["League Type"] == "Mixed":
            _level_weeks_acceptable_assignment.append((_week_number, 0))
            _mixed_weeks_acceptable_assignment.append((_week_number, 1))

    _match_count = 0
    for _team in _teams:
        _team_matches = get_team_matches(_team, _match_weeks, _teams, _get_home_matches=True, _get_away_matches=False)
        for _match in _team_matches:
            _match_count += 1
            if _team['League'] == "Mixed":
                _model.AddAllowedAssignments([_match_weeks[_match], _matches_correct_week[_match]],
                                             _mixed_weeks_acceptable_assignment)
            else:
                _model.AddAllowedAssignments([_match_weeks[_match], _matches_correct_week[_match]],
                                             _level_weeks_acceptable_assignment)
    print("Matches assigned correct week array:", _match_count)


if __name__ == '__main__':
    main()
