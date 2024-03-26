"""Define the Schedule class."""


import itertools
import re
from collections import defaultdict
from datetime import datetime, timedelta

import pandas as pd
from ortools.sat.python import cp_model
from ortools.sat.python.cp_model import CpModel

from src.league_structure.league import League
from gsheets import get_gsheet_worksheet, write_gsheet_output_data


def _check_teams_share_players(t1, t2) -> bool:
    """Check if two different teams share players."""
    teams_different = t1 != t2  # probably redundant but wanting to be sure.
    if not teams_different:
        return False

    same_league = t1.league == t2.league
    league_included_mixed = "Mixed" in [t1.league, t2.league]

    return not same_league and league_included_mixed


def _fix_team_name(_team_name_str):
    if re.fullmatch(r".* [A-G]", _team_name_str):
        return _team_name_str
    return _team_name_str + " A"


class Schedule:
    """A scheduling model to schedule fixtures for a given league.

    This model uses Google OR-Tools to optimize the scheduling of fixtures based on a set of constraints.

    league: The prepared league to be scheduled
    predefined_fixtures_url: Url of spreadsheet containing already commited match dates
    allowed_run_time: Seconds the model will be left to run for before a sub optimial result will be returned
    num_allowed_incorrect_fixture_week: Fix the number of matches that can be scheduled on the incorrect week
    """

    def __init__(
        self,
        league: League,
        allowed_run_time: int,
        predefined_fixtures_url: str = "",
        num_allowed_incorrect_fixture_week: int = 0,
        num_forced_prioritised_nights: int = 0,
        write_output: bool = True,
    ):
        """

        Create a new instance of the class.

        Parameters:
        - league: League: The league for which the fixtures will be generated.
        - allowed_run_time: int: The maximum allowed run time for the model in seconds.
        - predefined_fixtures_url: str (optional): The URL of a file containing predefined fixtures.
        - num_allowed_incorrect_fixture_week: int (optional): The number of allowed incorrect fixture weeks.
        - num_forced_prioritised_nights: int (optional): The number of forced prioritised nights.
        - write_output: bool (optional): Whether to write the output to a file.

        Returns:
        None

        """
        self.league = league
        self.model: CpModel = cp_model.CpModel()

        self.selected_fixture = {}

        self.create_model_variables()

        self.create_constraint_one_slot_per_fixture()
        self.create_constraint_one_fixture_per_slot()
        self.create_constraint_one_fixture_per_weeks_per_team(weeks_separated=2)
        self.create_constraint_inter_club_matches_first()
        self.create_constraint_fixture_correct_week(num_allowed_incorrect=num_allowed_incorrect_fixture_week)
        self.create_constraints_shared_players_diff_week()
        self.create_constraint_fixture_pair_separation(weeks_separated=6)
        self._create_constraint_prioritise_nights(num_forced=num_forced_prioritised_nights)
        self.create_constraint_balance_home_away_fixtures(allowed_imbalance=1)
        self.create_constraint_max_fixture_location_per_weeks_per_team(weeks_separated=6, max_per_period=2)
        self.create_constrain_limit_pre_christmas_matches()
        self.create_constraint_one_fixture_of_pair_pre_christmas()
        # self.create_constraint_more_fixtures_after_xmas() duplicated with above
        # self.create_constraint_mix_home_and_away_fixture(weeks_separated=2)

        # self.create_objective_fixture_correct_week()
        self.create_objective_function()

        if predefined_fixtures_url:
            self.input_predefined_fixtures(predefined_fixtures_url)

        self.model_result = self.run_model(allowed_run_time=allowed_run_time, write_output=write_output)

    def create_model_variables(self):
        """Create the model variables for each fixture court slot.

        For each fixture court slot in the league, this method creates a new Boolean variable
        to represent the selection of the fixture for that slot. The identifier of the court slot
        is used as the name of the variable.
        """
        for _fixture_slot in self.league.get_fixture_court_slots():
            self.selected_fixture[_fixture_slot.identifier] = self.model.NewBoolVar(_fixture_slot.identifier)

    def create_constraint_one_slot_per_fixture(self):
        """Create a constraint to ensure that each fixture is assigned to one and only one court slot.

        This method adds a constraint to the model such that the sum of the Boolean variables
        representing the selection of the fixture court slots for a given fixture is less than or equal to 1.
        This ensures that each fixture is scheduled to a single court slot.
        """
        for _fixture in self.league.fixtures:
            self.model.Add(
                sum(self.selected_fixture[_fixture_slot.identifier] for _fixture_slot in _fixture.fixture_court_slots)
                <= 1
            )

    def create_constraint_one_fixture_per_slot(self):
        """Create a constraint to ensure that each court slot is assigned to one and only one fixture.

        This method adds a constraint to the model such that the sum of the Boolean variables
        representing the selection of the fixture court slots for a given court slot
        is less than or equal to 1.
        This ensures that each court slot is occupied by a single fixture.
        """
        for _club in self.league.clubs:
            for _court_slot in _club.court_slots:
                self.model.Add(
                    sum(
                        self.selected_fixture[_fixture_slot.identifier]
                        for _fixture_slot in _court_slot.fixtures_court_slot
                    )
                    <= 1
                )

    def create_constraint_one_fixture_per_weeks_per_team(self, weeks_separated=1):
        """Constraint that enforces that each team is scheduled for only one fixture in each week.

        For each team, creates a list of all potential slots for that team either home or away.
        Finds the maximum week number for this set of court slots,
        Uses this to loop through each potential
        """
        for c in self.league.clubs:
            for t in c.teams:
                _team_court_slots = defaultdict(list)
                for fs in self.league.get_fixture_court_slots():
                    if fs.fixture.home_team == t or fs.fixture.away_team == t:
                        for i in range(weeks_separated):
                            week_group = str(fs.get_week_number() + i)
                            _team_court_slots[week_group].append(fs)

                for _team_slots_in_week in _team_court_slots.values():
                    self.model.Add(
                        sum(self.selected_fixture[_fixture_slot.identifier] for _fixture_slot in _team_slots_in_week)
                        <= 1
                    )

    def create_constraint_max_fixture_location_per_weeks_per_team(self, weeks_separated=6, max_per_period=2):
        """Constraint that enforces that each team is scheduled for only one home or away fixture in each week group.

        For each team, creates a list of all potential slots for that team either home or away.
        Finds the maximum week number for this set of court slots,
        Uses this to loop through each potential
        """
        for c in self.league.clubs:
            for t in c.teams:
                _team_court_slots = defaultdict(list)
                for fs in self.league.get_fixture_court_slots():
                    if fs.fixture.home_team == t or fs.fixture.away_team == t:
                        for i in range(weeks_separated):
                            week_group = str(fs.get_week_number() + i) + str(fs.fixture.home_team == t)
                            _team_court_slots[week_group].append(fs)

                for _team_slots_in_week in _team_court_slots.values():
                    self.model.Add(
                        sum(self.selected_fixture[_fixture_slot.identifier] for _fixture_slot in _team_slots_in_week)
                        <= max_per_period
                    )

    def create_constraint_inter_club_matches_first(self):
        """Constraint of inter-club fixtures to occur in the start of the season or post-Christmas.

        For each time, Finds the number of inter-club fixtures to be scheduled.
        Forces the number of inter-club fixtures in the same number of initial weeks to be equal.

        :return:
        """
        min_week_num = self.league.get_min_week_number()
        post_xmas_week_num = self.league.get_christmas_week_number()

        for t in self.league.get_teams():
            af = t.club.get_all_fixtures(
                _is_intra_club=True,
                _is_inter_club=False,
                _include_home=True,
                _include_away=False,
            )
            num_fixtures = len(af)
            if num_fixtures == 0:
                continue

            for f in t.get_all_fixtures(
                _is_intra_club=True,
                _is_inter_club=False,
                _include_home=True,
                _include_away=True,
            ):
                allow_fixture_slots = []
                disallowed_fixture_slots = []
                for fs in f.fixture_court_slots:
                    fs_weeks_after_start = fs.get_week_number() - min_week_num
                    is_start_of_seasons_slots: bool = 0 <= fs_weeks_after_start < num_fixtures

                    fs_weeks_after_xmas = fs.get_week_number() - post_xmas_week_num
                    is_post_christmas_slot: bool = 0 <= fs_weeks_after_xmas < num_fixtures

                    if is_start_of_seasons_slots or is_post_christmas_slot:
                        allow_fixture_slots.append(fs)
                    else:
                        disallowed_fixture_slots.append(fs)
                if len(allow_fixture_slots) > 0:
                    # print("Team =", t.name)
                    # print("Allowed_fixture_slots =", len(allow_fixture_slots))
                    # print("Weeks to be allocated in =", num_fixtures * 2)
                    self.model.Add(sum(self.selected_fixture[fs.identifier] for fs in disallowed_fixture_slots) <= 0)

    def create_constrain_limit_pre_christmas_matches(self):
        """Create constraint: At most Half of matches for each team can be before christmas."""
        post_xmas_week_num = self.league.get_christmas_week_number()
        for team in self.league.get_teams():
            fixtures = team.get_all_fixtures(
                _is_intra_club=True,
                _is_inter_club=True,
                _include_home=True,
                _include_away=True,
            )
            max_fixture_count = len(fixtures) // 2
            min_fixture_count = min(max_fixture_count, 3)

            pre_christmas_fixture_court_slots = []

            for fixture in fixtures:
                for fixture_court_slot in fixture.fixture_court_slots:
                    if fixture_court_slot.court_slot.date.get_week_number() <= post_xmas_week_num:
                        pre_christmas_fixture_court_slots.append(fixture_court_slot)

            fixture_vars = [self.selected_fixture[fs.identifier] for fs in pre_christmas_fixture_court_slots]
            self.model.Add(sum(fixture_vars) <= max_fixture_count)
            self.model.Add(sum(fixture_vars) >= min_fixture_count)

    def create_constraint_at_least_one_match_per_month(self):
        """Each team plays at least once each month for the duration of the season."""
        raise NotImplementedError
        # for team in self.league.get_teams():
        #     for month in range(1, 13):
        #         fixture_court_slots = [
        #             fs
        #             for fs in team.get_fixture_court_slots(_include_home=True, _include_away=True)
        #             # if fs.court_slot.date.date. == month # todo: fix this
        #         ]
        #         self.model.Add(sum(self.selected_fixture[fs.identifier] for fs in fixture_court_slots) >= 1)

    def create_constraint_balance_home_away_fixtures(self, allowed_imbalance=1):
        """Ensure same number of home and away fixtures before and after Christmas."""
        for team in self.league.get_teams():
            home_fcs = team.get_fixture_court_slots(_include_home=True, _include_away=False)
            away_fcs = team.get_fixture_court_slots(_include_home=False, _include_away=True)

            pre_xmas_home_match_vars = [
                self.selected_fixture[fcs.identifier]
                for fcs in home_fcs
                if fcs.get_week_number() < self.league.get_christmas_week_number()
            ]
            post_xmas_home_match_vars = [
                self.selected_fixture[fcs.identifier]
                for fcs in home_fcs
                if fcs.get_week_number() >= self.league.get_christmas_week_number()
            ]
            pre_xmas_away_match_vars = [
                self.selected_fixture[fcs.identifier]
                for fcs in away_fcs
                if fcs.get_week_number() < self.league.get_christmas_week_number()
            ]
            post_xmas_away_match_vars = [
                self.selected_fixture[fcs.identifier]
                for fcs in away_fcs
                if fcs.get_week_number() >= self.league.get_christmas_week_number()
            ]

            self.model.Add(sum(pre_xmas_home_match_vars) - sum(pre_xmas_away_match_vars) <= allowed_imbalance)
            self.model.Add(sum(post_xmas_home_match_vars) - sum(post_xmas_away_match_vars) <= allowed_imbalance)
            self.model.Add(sum(pre_xmas_away_match_vars) - sum(pre_xmas_home_match_vars) <= allowed_imbalance)
            self.model.Add(sum(post_xmas_away_match_vars) - sum(post_xmas_home_match_vars) <= allowed_imbalance)

            pre_xmas_match_vars = pre_xmas_home_match_vars + pre_xmas_away_match_vars
            post_xmas_match_vars = post_xmas_home_match_vars + post_xmas_away_match_vars
            self.model.Add(sum(pre_xmas_match_vars) <= sum(post_xmas_match_vars))

    def create_constraint_more_fixtures_after_xmas(self):
        """Ensure same number of home and away fixtures before and after Christmas."""
        for team in self.league.get_teams():
            fcs = team.get_fixture_court_slots(_include_home=True, _include_away=True)
            pre_xmas_match_vars = [
                self.selected_fixture[fcs.identifier]
                for fcs in fcs
                if fcs.get_week_number() < self.league.get_christmas_week_number()
            ]
            post_xmas_match_vars = [
                self.selected_fixture[fcs.identifier]
                for fcs in fcs
                if fcs.get_week_number() >= self.league.get_christmas_week_number()
            ]

            self.model.Add(sum(pre_xmas_match_vars) <= sum(post_xmas_match_vars))

    def create_constraint_fixture_pair_separation(self, weeks_separated=0):
        """Pairs of home and away matches should be separated by a number of weeks."""
        for t1, t2 in itertools.combinations(self.league.get_teams(), 2):
            if t1.league == t2.league and t1.division == t2.division and t1.club != t2.club:
                # print(t1,t2)
                all_t1_fixture_slot_list = t1.get_fixture_court_slots(_include_home=True, _include_away=True)
                between_team_fixture_slot_list = []
                for f in all_t1_fixture_slot_list:
                    if t2 in [f.fixture.home_team, f.fixture.away_team]:
                        between_team_fixture_slot_list.append(f)
                self._create_constraint_fixture_in_list_separated(between_team_fixture_slot_list, weeks_separated)

    def create_constraint_one_fixture_of_pair_pre_christmas(self):
        """Ensure at most fixture of a pair is before Christmas."""
        for t1, t2 in itertools.combinations(self.league.get_teams(), 2):
            t1_fcs = t1.get_fixture_court_slots(_include_home=True, _include_away=True)
            t2_fcs = t2.get_fixture_court_slots(_include_home=True, _include_away=True)
            # get intersection of fixture court slots
            t1_t2_fcs = [fcs for fcs in t1_fcs if fcs in t2_fcs]
            if t1_t2_fcs:
                pre_xmas_match_vars = [
                    self.selected_fixture[fcs.identifier]
                    for fcs in t1_t2_fcs
                    if fcs.get_week_number() < self.league.get_christmas_week_number()
                ]
                self.model.Add(sum(pre_xmas_match_vars) <= 1)

    def create_constraints_shared_players_diff_week(self):
        """Constraint to ensure the players don't play multiple fixtures on the same day."""
        for c in self.league.clubs:
            for t1, t2 in itertools.combinations(c.teams, 2):
                if _check_teams_share_players(t1, t2):
                    self._create_constraint_shared_players_diff_week(t1, t2)

    def _create_constraint_shared_players_diff_week(self, t1, t2):
        """Constraint to ensure the players don't play multiple fixtures on the same day."""
        for week in self.league.dates.get_week_range():
            fcs_list = self.league.get_fixture_court_slots_for_teams_in_week([t1, t2], week)
            if len(fcs_list) > 0:
                self.model.Add(sum(self.selected_fixture[fcs.identifier] for fcs in fcs_list) <= 1)

    def create_constraint_fixture_correct_week(self, num_allowed_incorrect=10):
        """Limit the number of fixtures scheduled in the wrong week for their league type."""
        incorrect_week_fixture_slots = []
        for _fixture_slot in self.league.get_fixture_court_slots():
            if not _fixture_slot.is_correct_week():
                incorrect_week_fixture_slots.append(_fixture_slot)

        self.model.Add(
            sum(self.selected_fixture[_fixture_slot.identifier] for _fixture_slot in incorrect_week_fixture_slots)
            <= num_allowed_incorrect
        )

    def create_constraint_mix_home_and_away_fixture(self, weeks_separated=0):
        """Create fixture week separation constraint for each team."""
        for t in self.league.get_teams():
            t_fcs_home = t.get_fixture_court_slots(_include_home=True, _include_away=False)
            t_fcs_away = t.get_fixture_court_slots(_include_home=False, _include_away=True)
            self._create_constraint_fixture_in_list_separated(t_fcs_home, weeks_separated)
            self._create_constraint_fixture_in_list_separated(t_fcs_away, weeks_separated)

    def _create_constraint_fixture_in_list_separated(self, fixture_list: list, weeks_separated):
        """For each pair of fixtures in the list, ensure they are separated by a number of weeks."""
        _rules_added = 0
        for fcs1, fcs2 in itertools.combinations(fixture_list, 2):
            date_diff = fcs1.court_slot.date.date - fcs2.court_slot.date.date
            fixtures_are_different = fcs1.fixture != fcs2.fixture
            fixtures_within_weeks_separated = abs(date_diff.days) // 7 <= weeks_separated
            if fixtures_are_different and fixtures_within_weeks_separated:
                self.model.Add(
                    sum(
                        [
                            self.selected_fixture[fcs1.identifier],
                            self.selected_fixture[fcs2.identifier],
                        ]
                    )
                    <= 1
                )
                _rules_added += 1
        # print("Rules Added:", _rules_added)

    def input_predefined_fixtures(self, _fixture_sheet_url):
        """Read in a Google sheet of predefined fixtures and adds them to the model."""
        predefined_fixtures = pd.DataFrame(get_gsheet_worksheet(_fixture_sheet_url, "Sheet1").get_all_records())
        _headings = [
            "Division",
            "Home Team",
            "Away Team",
            "Status",
            "Match Date",
            "Time",
            "Courts",
        ]
        _unfixed_fixtures = self.league.get_fixture_court_slots()
        if len(predefined_fixtures) == 0:
            return

        for _, row in predefined_fixtures[_headings].iterrows():
            _home_team = self.league.get_team_obj_from_str(_fix_team_name(row["Home Team"]))
            _away_team = self.league.get_team_obj_from_str(_fix_team_name(row["Away Team"]))
            _date = self.league.get_date_obj_from_str(row["Match Date"])

            _fixture_slots = self.league.get_specific_fixture_court_slot(_home_team, _away_team, _date)
            for fs in _fixture_slots:
                _unfixed_fixtures.remove(fs)

            if _fixture_slots:
                self.model.Add(
                    sum(self.selected_fixture[_fixture_slot.identifier] for _fixture_slot in _fixture_slots) == 1
                )

        _next_week = datetime.today() + timedelta(days=0)
        _unfixed_fixtures_before_date = [i for i in _unfixed_fixtures if i.court_slot.date.date <= _next_week]

        if _unfixed_fixtures_before_date:
            self.model.Add(
                sum(self.selected_fixture[_fixture_slot.identifier] for _fixture_slot in _unfixed_fixtures_before_date)
                == 0
            )

    def create_objective_fixture_correct_week(self):
        """Create the objective function to maximise the number of fixtures in the correct week."""
        correct_week_fixture_slots = []
        for _fixture_slot in self.league.get_fixture_court_slots():
            if _fixture_slot.is_correct_week():
                correct_week_fixture_slots.append(_fixture_slot)

        self.model.Maximize(
            sum(self.selected_fixture[_fixture_slot.identifier] for _fixture_slot in correct_week_fixture_slots)
        )

    def create_objective_function(self):
        """Create the objective function.

        - Maximise the number of fixtures scheduled
        - De prioritise matches at the end of the season
        - Attempt to schedule matches pre-Christmas. (limited to at most half the matches)
        """
        max_week_number = max(
            [_fixture_slot.court_slot.date.get_week_number() for _fixture_slot in self.league.get_fixture_court_slots()]
        )
        league_ideal_end_week = self.league.get_christmas_week_number() * 2 - self.league.get_min_week_number()

        self.model.Maximize(
            # Attempt to schedule all fixtures
            sum(
                self.selected_fixture[_fixture_slot.identifier] * 100_000_000
                for _fixture_slot in self.league.get_fixture_court_slots()
            )
            # De prioritise matches at the end of the season
            + sum(
                max_week_number
                - self.selected_fixture[_fixture_slot.identifier] * _fixture_slot.court_slot.date.get_week_number()
                for _fixture_slot in self.league.get_fixture_court_slots()
                if _fixture_slot.court_slot.date.get_week_number() > league_ideal_end_week
            )
            # attempt to schedule matches pre-Christmas. (limited to at most half the matches)
            + sum(
                self.selected_fixture[_fixture_slot.identifier] * 100_000
                for _fixture_slot in self.league.get_fixture_court_slots()
                if _fixture_slot.court_slot.date.get_week_number() < self.league.get_christmas_week_number()
            )
        )

    def _create_constraint_prioritise_nights(self, num_forced=0):
        """Constraint forces prioritised fixtures to be scheduled."""
        prioritised_fixture_slots = [
            self.selected_fixture[_fixture_slot.identifier]
            for _fixture_slot in self.league.get_fixture_court_slots()
            if _fixture_slot.court_slot.priority
        ]

        self.model.Add(sum(prioritised_fixture_slots) >= num_forced)

    def run_model(self, allowed_run_time=200, write_output: bool = True) -> str:
        """Run the model generated by the schedule.

        :param allowed_run_time: How long in seconds the model can run for
        :param write_output: Determin if the output should be written to gsheets
        :return: If the model was successful, INFEASIBLE
        """

        # Amends the OnSolution Callback Function in the solution class of the model
        class SolutionCallback(cp_model.CpSolverSolutionCallback):
            def __init__(self):
                cp_model.CpSolverSolutionCallback.__init__(self)

            def OnSolutionCallback(self):  # noqa N802
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
            for fixture in self.league.fixtures:
                fixture_has_been_scheduled = False
                for fixture_slot in fixture.fixture_court_slots:
                    is_scheduled = solver.Value(self.selected_fixture[fixture_slot.identifier])
                    fixture_slot.is_scheduled = is_scheduled
                    if is_scheduled:
                        fixture_has_been_scheduled = True
                        print(fixture_slot.friendly_name)
                if fixture_has_been_scheduled is not True:
                    print(f"Fixture not Scheduled {fixture.name}")
                    status_name = "INFEASIBLE"

            # for _fixture_slot in self.league.get_fixture_court_slots():
            #     _is_scheduled = solver.Value(self.selected_fixture[_fixture_slot.identifier])
            #     _fixture_slot.is_scheduled = _is_scheduled
            #     if _is_scheduled:
            #         print(_fixture_slot.friendly_name, _is_scheduled)
            # Print Results
            if write_output:
                self._write_schedule_to_gsheet(self.league.league_management_URL)

        print(f"Status Update: {status_name}")
        return status_name

    def _write_schedule_to_gsheet(self, _file_location):
        print("***Test.py***")
        result = [fcs.as_dict() for fcs in self.league.get_fixture_court_slots()]
        _data_dict = pd.DataFrame(result)
        write_gsheet_output_data(_data_dict, "Match Fixture slots", _file_location)
        result = []
        for t in self.league.get_teams():
            _get_home = True
            _get_away = True
            for fcs in t.get_fixture_court_slots(_get_home, _get_away):
                fcs_dict = fcs.as_dict()
                fcs_dict["Team"] = t.name
                result.append(fcs_dict)
        _data_dict = pd.DataFrame(result)
        write_gsheet_output_data(
            output_data=_data_dict, sheet_name="Match Fixture slots by team", file_location=_file_location
        )
