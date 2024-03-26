"""Defines the League Class"""
from __future__ import annotations

from datetime import datetime

import pandas as pd

from src.league_structure.fixture_court_slot import FixtureCourtSlot
from src.league_structure.fixture import Fixture
from src.league_structure.team import Team
from src.league_structure.dates import Dates
from src.league_structure.date import Date
from gsheets import get_gsheet_worksheet, write_gsheet_output_data
from src.league_structure import club as club


class League:
    """Represents a league and initializes its instance with the given _league_management_url."""

    def __init__(self, _league_management_url):
        """Initialize the class the given _league_management_url.
        4
                Attributes:
                ----------
                name (str): Name of the league, initialized to "Something".
                league_management_URL (str): URL of the league management sheet.
                clubs (list): A list of all the clubs in the league.
                dates (Dates): An instance of the Dates class that contains the dates of the league.
                fixtures (list): A list of all the fixtures of the league.

                league = League("https://example.com/league_management")
        """
        self.name: str = "Something"
        self.league_management_URL = _league_management_url
        self.clubs: list[club.Club] = []
        self.dates: Dates = Dates()
        self.fixtures: list[Fixture] = []

        # Club Entry management
        _club_entry_management = pd.DataFrame(
            get_gsheet_worksheet(self.league_management_URL, "Club Entry Management").get_all_records()
        )
        for club_url in _club_entry_management["Entry URL"]:
            if club_url:
                c = club.Club(self, club_url)
                self.clubs.append(c)

        self._get_previous_league_position()

        self._generate_fixtures()

        # self.dates.calculate_dates_numbers()

    def _get_previous_league_position(self):
        """Retrieve the previous league position data for all the clubs and sets their division.

        Args:
        ----
        self (League): An instance of the League class.

        Returns:
        -------
        None.

        Raises:
        ------
        ValueError: If a team doesn't have a specific rank from the previous season
        and is missing from the spreadsheet.

        Example:
        -------
        league = League("https://example.com/league_management")
        league._get_previous_league_position()
        """
        headings = [
            "League",
            "Club",
            "Team",
            "Previous League Position",
            "Teams Entered",
            "New Division",
        ]

        raw_gsheet = get_gsheet_worksheet(self.league_management_URL, "Previous League organisation")
        previous_league_position_df = raw_gsheet.get_all_records(expected_headers=headings)

        for row in previous_league_position_df:
            _club: club.Club = self.get_club(row["Club"])
            if _club:
                _team: Team = _club.get_team(row["League"], row["Team"])
                if _team:
                    try:
                        _team.division = int(row["New Division"])
                    except ValueError as err:
                        print(f"Error Cause by {row.to_markdown()}")
                        raise ValueError(f"Error Cause by {row}") from err

                else:
                    print("Missing Team:", row["Club"], row["League"], row["Team"])
            else:
                print("Missing Club", row["Club"])

        for t in self.get_teams():
            if t.division == 0:
                raise ValueError(
                    f"Team {t.name} doesn't have specific rank from previous season. Missing from spreadsheet"
                )

    def get_club(self, club_name_str):
        """Get the club with the given _club_name_str.

        :param club_name_str: Name of the club to be returned
        :return: the selected Club Instance
        """
        for c in self.clubs:
            if c.name == club_name_str:
                return c
        return None

    def write_output(self) -> None:
        """Write the output of the league to the console.

        :return: None.
        """
        print("Dates:")
        for d in self.dates.dates:
            print(d.date)
        for c in self.clubs:
            c.write_output()

    def get_teams(self) -> list[Team]:
        """Return a list of all the teams in this league.

        :return: List of Teams
        """
        return [team for c in self.clubs for team in c.teams]

    def write_teams_entered(self) -> None:
        """Write the teams entered to the league management sheet.

        :return: none
        """
        _league_list = []
        _club_list = []
        _rank_list = []
        for t in self.get_teams():
            _league_list.append(t.league)
            _club_list.append(t.club.name)
            _rank_list.append(t.rank)
        _data = {"League": _league_list, "Club": _club_list, "Rank": _rank_list}
        _data_dict = pd.DataFrame(_data)
        write_gsheet_output_data(_data_dict, "Teams Entered", self.league_management_URL)

    def _generate_fixtures(self) -> None:
        """Generate the fixtures for the league.

        :return: None
        """
        for hm_team in self.get_teams():
            for aw_team in self.get_teams():
                if hm_team != aw_team and hm_team.league == aw_team.league and hm_team.division == aw_team.division:
                    fixture_i = Fixture(hm_team, aw_team)
                    self.fixtures.append(fixture_i)

    def get_fixture_court_slots(self) -> list[FixtureCourtSlot]:
        """Return a list of all the fixture court slots in the league.

        :return: List of FixtureCourtSlot
        """
        _fixtures_dates = []
        for _fixture in self.fixtures:
            _fixtures_dates.extend(_fixture.fixture_court_slots)
        return _fixtures_dates

    def get_fixture_court_slots_for_teams_on_date(self, _teams: list[Team], _date: Date) -> list[FixtureCourtSlot]:
        """Return all the fixture court slots in the league for the given teams on the given date.

        :param _teams: list of teams to get fixture court slots for
        :param _date:  date to get fixture court slots for
        :return: List of fixture court slots for teams on date.
        """
        result = []
        for _fixture in self.fixtures:
            fixture_team_match_a = _fixture.home_team in _teams
            fixture_team_match_h = _fixture.away_team in _teams
            if fixture_team_match_a or fixture_team_match_h:
                for fcs in _fixture.fixture_court_slots:
                    if fcs.court_slot.date == _date:
                        result.append(fcs)
        return result

    def get_fixture_court_slots_for_teams_in_week(self, _teams: list[Team], week: int) -> list[FixtureCourtSlot]:
        """Return all the fixture court slots in the league for the given teams on the given date.

        :param _teams: list of teams to get fixture court slots for
        :param _date:  date to get fixture court slots for
        :return: List of fixture court slots for teams on date.
        """
        result = []
        for _fixture in self.fixtures:
            fixture_team_match_a = _fixture.home_team in _teams
            fixture_team_match_h = _fixture.away_team in _teams
            if fixture_team_match_a or fixture_team_match_h:
                for fcs in _fixture.fixture_court_slots:
                    if fcs.court_slot.date.get_week_number() == week:
                        result.append(fcs)
        return result

    def get_specific_fixture_court_slot(
        self, _home_team: Team, _away_team: Team, _date: Date
    ) -> list[FixtureCourtSlot]:
        """Return a specific fixture court slot for the given home team, away team and date.

        :param _home_team: selected home team
        :param _away_team: selected away team
        :param _date: selected date
        :return: List of fixture court slots for between teams on date.
        """
        result = []
        for _fixture in self.fixtures:
            if _fixture.home_team == _home_team and _fixture.away_team == _away_team:
                for fcs in _fixture.fixture_court_slots:
                    if fcs.court_slot.date == _date:
                        result.append(fcs)
        return result

    def get_date_obj_from_str(self, _date_str: str) -> Date:
        """Return the date object for the given date string.

        :param _date_str: date string to get date object for
        :return: Date Class for given date string
        """
        _date = datetime.strptime(_date_str, "%d/%m/%Y")
        for d in self.dates.dates:
            if d.date == _date:
                return d
        raise ValueError("Date not Found: " + _date_str)

    def get_team_obj_from_str(self, _team_name_str: str) -> Team:
        """Return the team object for the given team name string.

        :param _team_name_str: team name string to get team object for
        :return: Team Class for given team name string
        """
        for t in self.get_teams():
            if t.name == _team_name_str:
                return t
        raise ValueError("Team Not Found: " + _team_name_str)

    def check_league_data(self) -> None:
        """Print key league data.

        :return:  None
        """
        print("League name", self.name)
        print("URL", self.league_management_URL)
        print("No. Clubs", len(self.clubs))
        print("No. fixtures", len(self.fixtures))
        print()
        print("Date Weeks")

        for d in sorted(self.dates.dates, key=lambda _d: _d.date_delta_from_start):
            print(
                "Date:",
                d.date,
                "Delta:",
                d.date_delta_from_start.days,
                "Delta Weeks",
                d.date_delta_from_start.days // 7,
            )
        print()

    def get_min_week_number(self) -> int:
        """Get the minimum week number in the league.

        :return:
        """
        week_numbers = (d.get_week_number() for d in self.dates.dates)
        return min(week_numbers)

    def get_christmas_week_number(self) -> int:
        """Get the first schedulable week number after Christmas.

        :return: the week number of the first date after Christmas.
        """
        dates = (d.date for d in self.dates.dates)
        min_date = min(dates)
        second_year = min_date.year + 1
        dates_in_second_year = (d.get_week_number() for d in self.dates.dates if d.date.year == second_year)
        return min(dates_in_second_year)

    def __repr__(self):
        """Return a string representation of the League Class."""
        return self.name
