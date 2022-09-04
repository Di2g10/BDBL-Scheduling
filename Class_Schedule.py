from __future__ import print_function
from typing import List, Tuple, Dict, Any, Union
from ortools.sat.python import cp_model
from datetime import datetime, timedelta, date
import itertools
from ortools.sat.python.cp_model import IntVar, CpModel
import pandas as pd
import re
from Class_League import League
from gsheets import get_gsheet_data, write_gsheet_output_data


def main():
    pass


class Schedule:
    def __init__(self, _league: League, _predefined_fixtures_url):
        self.league = _league
        self.model: CpModel = cp_model.CpModel()

        self.selected_fixture = {}

        self.create_model_variables()

        self.create_constraint_one_slot_per_fixture()
        self.create_constraint_one_fixture_per_slot()
        self.create_constraint_one_fixture_per_week_per_team()
        # self.create_constraint_inter_club_matches_first()
        self.create_constraint_fixture_correct_week(num_allowed_incorrect=4)
        self.create_constraint_shared_players_diff_day()
        # self.create_constraint_fixture_pair_separation(weeks_separated=8)
        # self.create_constraint_mix_home_and_away_fixture(weeks_separated=2)

        # self.create_objective_fixture_correct_week()

        self.input_predefined_fixtures(_predefined_fixtures_url)

        self.run_model(allowed_run_time=2000)

    def create_model_variables(self):
        for _fixture_slot in self.league.get_fixture_court_slots():
            self.selected_fixture[_fixture_slot.identifier] = self.model.NewBoolVar(_fixture_slot.identifier)

    def create_constraint_one_slot_per_fixture(self):
        for _fixture in self.league.fixtures:
            self.model.Add(sum(self.selected_fixture[_fixture_slot.identifier]\
                               for _fixture_slot in _fixture.fixture_court_slots)
                           == 1)

    def create_constraint_one_fixture_per_slot(self):
        for _club in self.league.clubs:
            for _court_slot in _club.court_slots:
                self.model.Add(sum(self.selected_fixture[_fixture_slot.identifier]\
                                   for _fixture_slot in _court_slot.fixtures_court_slot)
                               <= 1)
        pass

    def create_constraint_one_fixture_per_week_per_team(self):
        for c in self.league.clubs:
            for t in c.teams:
                _team_court_slots = []
                for fs in self.league.get_fixture_court_slots():
                    if fs.fixture.home_team == t or fs.fixture.away_team == t:
                        _team_court_slots.append(fs)

                _max_week_num = 0
                for tcs in _team_court_slots:
                    _week_number = tcs.get_week_number()
                    if _week_number > _max_week_num:
                        _max_week_num = _week_number

                for i in range(_max_week_num):
                    _team_slots_in_week = []
                    for tcs in _team_court_slots:
                        if i == tcs.get_week_number():
                            _team_slots_in_week.append(tcs)
                    self.model.Add(sum(self.selected_fixture[_fixture_slot.identifier]
                                       for _fixture_slot in _team_slots_in_week)
                                   <= 1)

    def create_constraint_inter_club_matches_first(self):
        _min_week_num = self.league.get_min_week_number()
        for t in self.league.get_teams():
            af = t.club.get_all_fixtures(_is_intra_club=True, _is_inter_club=False,
                                         _include_home=True, _include_away=False)
            num_intra_club_fixtures = len(af)
            if num_intra_club_fixtures > 0:
                for f in t.get_all_fixtures(_is_intra_club=True, _is_inter_club=False,
                                            _include_home=True, _include_away=True):
                    allow_fixture_slots = []
                    disallowed_fixture_slots = []
                    for fs in f.fixture_court_slots:
                        if fs.get_week_number() - _min_week_num < num_intra_club_fixtures * 2:
                            allow_fixture_slots.append(fs)
                        else:
                            disallowed_fixture_slots.append(fs)
                    if len(allow_fixture_slots) > 0:
                        print("Team =", t.name)
                        print("Allowed_fixture_slots =", len(allow_fixture_slots))
                        print("Weeks to be allocated in =", num_intra_club_fixtures * 2)
                        self.model.Add(sum(self.selected_fixture[fs.identifier]
                                           for fs in disallowed_fixture_slots)
                                       <= 0)

    def create_constraint_fixture_pair_separation(self, weeks_separated=0):
        # for each pair of home and away matches they should be in separate by a number of weeks
        for t1, t2 in itertools.combinations(self.league.get_teams(), 2):
            if t1.league == t2.league and t1.division == t2.division and t1.club != t2.club:
                # print(t1,t2)
                all_t1_fixture_slot_list = t1.get_fixture_court_slots(_include_home=True, _include_away=True)
                between_team_fixture_slot_list = []
                for f in all_t1_fixture_slot_list:
                    if t2 in [f.fixture.home_team, f.fixture.away_team]:
                        between_team_fixture_slot_list.append(f)
                self._create_constraint_fixture_in_list_separated(between_team_fixture_slot_list, weeks_separated)

    def create_constraint_shared_players_diff_day(self):
        # for teams that share players their matches shouldn't be scheduled on the same day.
        for c in self.league.clubs:
            for t1, t2 in itertools.combinations(c.teams, 2):
                teams_different = t1 != t2  # probably redundant but wanting to be sure.
                teams_adj_rank_same_league = t1.league == t2.league and abs(ord(t1.rank) - ord(t2.rank)) <= 1
                teams_same_rank_dif_league = t1.league != t2.league and t1.rank == t2.rank
                at_least_one_mixed_team = t1.league == "Mixed" or t2.league == "Mixed"
                teams_share_players = teams_different \
                                          and (teams_adj_rank_same_league
                                               or (teams_same_rank_dif_league
                                                   and at_least_one_mixed_team)
                                               )
                if teams_share_players:
                    for d in self.league.dates.dates:
                        fcs_list = self.league.get_fixture_court_slots_for_teams_on_date([t1, t2], d)
                        if len(fcs_list) > 0:
                            self.model.Add(sum(self.selected_fixture[fcs.identifier]
                                               for fcs in fcs_list)
                                           <= 1)

    def create_constraint_fixture_correct_week(self, num_allowed_incorrect=10):
        incorrect_week_fixture_slots = []
        for _fixture_slot in self.league.get_fixture_court_slots():
            if not _fixture_slot.is_correct_week():
                incorrect_week_fixture_slots.append(_fixture_slot)

        self.model.Add(sum(self.selected_fixture[_fixture_slot.identifier]
                           for _fixture_slot in incorrect_week_fixture_slots)
                       <= num_allowed_incorrect)

    def create_constraint_mix_home_and_away_fixture(self, weeks_separated=0):
        for t in self.league.get_teams():
            t_fcs_home = t.get_fixture_court_slots(_include_home=True, _include_away=False)
            t_fcs_away = t.get_fixture_court_slots(_include_home=False, _include_away=True)
            self._create_constraint_fixture_in_list_separated(t_fcs_home, weeks_separated)
            self._create_constraint_fixture_in_list_separated(t_fcs_away, weeks_separated)

    def _create_constraint_fixture_in_list_separated(self, fixture_list: List, weeks_separated):
        _rules_added = 0
        for fcs1, fcs2 in itertools.combinations(fixture_list, 2):
            date_diff = fcs1.court_slot.date.date - fcs2.court_slot.date.date
            if abs(date_diff.days) // 7 <= weeks_separated:
                if fcs1.fixture != fcs2.fixture:
                    # print("\t", fcs1, fcs2)
                    self.model.Add(sum([self.selected_fixture[fcs1.identifier],
                                        self.selected_fixture[fcs2.identifier]])
                                   <= 1)
                    _rules_added += 1
        print("Rules Added:", _rules_added)

    def input_predefined_fixtures(self, _fixture_sheet_url):
        predefined_fixtures = pd.DataFrame(get_gsheet_data(_fixture_sheet_url,
                                                           "Sheet1").get_all_records())
        _headings = ["Division", "Home Team", "Away Team", "Status", "Match Date", "Time", "Courts"]
        _unfixed_fixtures = self.league.get_fixture_court_slots()
        if len(predefined_fixtures) == 0:
            return
        
        for index, row in predefined_fixtures[_headings].iterrows():
            _home_team = self.league.get_team_obj_from_str(self._fix_team_name(row["Home Team"]))
            _away_team = self.league.get_team_obj_from_str(self._fix_team_name(row["Away Team"]))
            _date = self.league.get_date_obj_from_str(row["Match Date"])

            _fixture_slots = self.league.get_specific_fixture_court_slot(_home_team, _away_team, _date)
            for fs in _fixture_slots:
                _unfixed_fixtures.remove(fs)

            if _fixture_slots:
                self.model.Add(sum(self.selected_fixture[_fixture_slot.identifier]
                                   for _fixture_slot in _fixture_slots)
                               == 1)

        _next_week = datetime.today() + timedelta(days=0)
        _unfixed_fixtures_before_date = [i for i in _unfixed_fixtures if i.court_slot.date.date <= _next_week]

        if _unfixed_fixtures_before_date:
            self.model.Add(sum(self.selected_fixture[_fixture_slot.identifier]
                               for _fixture_slot in _unfixed_fixtures_before_date)
                           == 0)

    def _fix_team_name(self, _team_name_str):
        if re.fullmatch(r".* [A-G]", _team_name_str):
            return _team_name_str
        return _team_name_str + " A"

    def create_objective_fixture_correct_week(self):
        correct_week_fixture_slots = []
        for _fixture_slot in self.league.get_fixture_court_slots():
            if _fixture_slot.is_correct_week():
                correct_week_fixture_slots.append(_fixture_slot)

        self.model.Maximize(sum(self.selected_fixture[_fixture_slot.identifier]\
                                for _fixture_slot in correct_week_fixture_slots))

    def run_model(self, allowed_run_time=200):
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
        solver.parameters.max_time_in_seconds = allowed_run_time
        sc = SolutionCallback()
        status_num = solver.SolveWithSolutionCallback(self.model, sc)

        status_name = solver.StatusName(status_num)
        print("Status:")
        print(status_name)
        objective_value = solver.ObjectiveValue()
        print("Objective Value: ", objective_value)
        if status_name in ["FEASIBLE", "OPTIMAL"]:
            for _fixture_slot in self.league.get_fixture_court_slots():
                _is_scheduled = solver.Value(self.selected_fixture[_fixture_slot.identifier])
                _fixture_slot.is_scheduled = _is_scheduled
                if _is_scheduled:
                    print(_fixture_slot.friendly_name, _is_scheduled)
            # Print Results
            self._write_schedule_to_gsheet(self.league.league_management_URL)

    def _write_schedule_to_gsheet(self, _file_location):
        print("***Test***")
        result = [fcs.as_dict() for fcs in self.league.get_fixture_court_slots()]
        _data_dict = pd.DataFrame(result)
        write_gsheet_output_data(_data_dict, "Match Fixture slots", _file_location)
        result = []
        for t in self.league.get_teams():
            _get_home = True
            _get_away = True
            for fcs in t.get_fixture_court_slots(_get_home, _get_away):
                fcs_dict = fcs.as_dict()
                fcs_dict['Team'] = t.name
                result.append(fcs_dict)
        _data_dict = pd.DataFrame(result)
        write_gsheet_output_data(_data_dict, "Match Fixture slots by team", _file_location)


if __name__ == '__main__':
    main()
