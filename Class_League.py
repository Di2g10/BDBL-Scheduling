"""Contains the League class and its methods."""
from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from gsheets import get_gsheet_worksheet, write_gsheet_output_data


# League is the group of all clubs and teams entering for all Divisions for the year.
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

        Args:
        ----
        _league_management_url (str): URL of the league management sheet.

        Methods:
        -------
        None.

        Raises:
        ------
        None.

        Example:
        -------
        league = League("https://example.com/league_management")
        """
        self.name: str = "Something"
        self.league_management_URL = _league_management_url
        self.clubs: list[Club] = []
        self.dates: Dates = Dates()
        self.fixtures: list[Fixture] = []

        # Club Entry management
        _club_entry_management = pd.DataFrame(
            get_gsheet_worksheet(self.league_management_URL, "Club Entry Management").get_all_records()
        )
        for club_url in _club_entry_management["Entry URL"]:
            if club_url:
                c = Club(self, club_url)
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
        _raw_gsheet = get_gsheet_worksheet(self.league_management_URL, "Previous League organisation").get_all_records()
        _previous_league_position_df = pd.DataFrame(_raw_gsheet)
        _headings = [
            "League",
            "Club",
            "Team",
            "Previous League Position",
            "Teams Entered",
            "New Division",
        ]
        for _, row in _previous_league_position_df[_headings].iterrows():
            _club: Club = self.get_club(row["Club"])
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


class Club:
    """Club Class.

    Clubs are a group of teams entering that may share players
    and play at the same venue
    and share courts.
    """

    def __init__(self, _league: League, _file_location):
        """Initialise the Club Class."""
        self.fileLocation = _file_location
        self.league = _league
        self.court_slots = []

        # Club Info Sheet
        _club_info = pd.DataFrame(get_gsheet_worksheet(self.fileLocation, "0. Club Information").get_all_records())
        self.name = _club_info["Club Name"][0]

        # Teams Entering Sheet
        _teams_entering = pd.DataFrame(get_gsheet_worksheet(self.fileLocation, "1. Teams Entering").get_all_records())
        _teams_columns = [
            "League Name",
            "Team Rank",
            "Availability Group",
            "Comments",
            "Home Nights Required",
        ]
        self.teams = []

        for _, row in _teams_entering[_teams_columns].iterrows():
            if row["League Name"]:
                t = Team(
                        self,
                        row["League Name"],
                        row["Team Rank"],
                        row["Availability Group"],
                )
                self.teams.append(t)

        # Get Club Availability
        self._get_club_availability()

    def _get_club_availability(self):
        _club_availability = pd.DataFrame(get_gsheet_worksheet(self.fileLocation, "2. Availability").get("C11:L300"))
        _club_availability.columns = _club_availability.iloc[0]
        _club_availability = _club_availability[1:]
        print(self.name)
        for _, row in _club_availability.iterrows():
            if row["Available"] != "Unavailable":
                _date = self.league.dates.add_date(row["Date"], row["League Type"], row["Weekday"])
                priority = row.get("Priority", False)
                for _concurrent_matches in range(int(row["No. Concurrent Matches"])):
                    _court_slot = CourtSlot(_date, self, _concurrent_matches, priority)
                    self.court_slots.append(_court_slot)
                    for _team in self.teams:
                        if _team.availability_group == row["Available"]:
                            _court_slot.add_team(_team)

    def write_output(self):
        """Write output for the club."""
        print(self.name)
        # print(self.availability_weeks)
        # print(self.availability_detail)
        for t in self.teams:
            t.write_output()

    def get_team(self, _league, _team_rank):
        """Get the team object for the given league and team rank."""
        for t in self.teams:
            if t.league == _league and t.rank == _team_rank:
                return t
        return None

    def get_fixture_court_slots(self, _include_home=True, _include_away=True):
        """Get all fixture court slots for the club."""
        _fixtures = []
        for _team in self.teams:
            _fixtures.extend(_team.get_fixture_court_slots(_include_home, _include_away))
        return _fixtures

    def get_all_fixtures(
        self,
        _is_intra_club=True,
        _is_inter_club=True,
        _include_home=True,
        _include_away=True,
    ):
        """Get all fixtures for the club."""
        result = []
        for t in self.teams:
            result.extend(t.get_all_fixtures(_is_intra_club, _is_inter_club, _include_home, _include_away))
        return result

    def __repr__(self):
        """Return a string representation of the club."""
        return self.name


# dates are specific days in the league year. There should be at most one instance per day.
class Date:
    """Class to represent a date in the league."""

    def __init__(self, _date_str, _league_type, _weekday, _date_anchor):
        """Initialise an instance of the Date class."""
        self.date_str: str = _date_str
        self.date: datetime = datetime.strptime(_date_str, "%d-%b-%Y")
        self.league_type = _league_type
        self.weekday = _weekday
        self.court_slots = []
        # Anchor date could be wrong for early dates added if not added in order
        self.date_delta_from_start = self.date - _date_anchor

    def __repr__(self):
        """Return the date string."""
        return self.date_str

    def get_week_number(self) -> int:
        """Return the week number of the date from the start of the league year."""
        return self.date_delta_from_start.days // 7


# Collection of all dates available to the league. Handles the uniques of the Date object.
class Dates:
    """Collection of all dates available to the league. Handles the uniques of the Date object."""

    def __init__(self):
        """Initialise the collection of dates."""
        self.dates = []
        self.date_values = ()
        self.min_date = datetime(2021, 11, 1)

    def add_date(self, _date_str, _league_type, _weekday):
        """Add a date to the collection if it does not already exist. Returns the date object."""
        _date_tuple = (_date_str,)
        for d in self.dates:
            if d.date_str == _date_str:
                return d
        _date_obj = Date(_date_str, _league_type, _weekday, self.min_date)
        self.dates.append(_date_obj)
        # self._update_min_date(_date_obj)
        return _date_obj

    def _update_min_date(self, _date: Date):
        """Update the minimum date in the collection."""
        if _date.date < self.min_date:
            # round min date down to the start of the week
            self.min_date = _date.date - timedelta(days=_date.date.weekday())
            print(f"Min date updated to {self.min_date}")

    def calculate_dates_numbers(self):
        """Calculate the date numbers for each date in the collection."""
        for d in self.dates:
            d.calculate_date_numbers(self.min_date)

    def get_week_range(self) -> list[int]:
        """Return a list of all the week numbers."""
        min_week = min([d.get_week_number() for d in self.dates])
        max_week = max([d.get_week_number() for d in self.dates])
        return list(range(min_week, max_week))


# An entry into a specific division of a specific league type.
class Team:
    """A team is a club in a league in a division.

    It has a rank within the division and a home night.
    """

    def __init__(self, _club: Club, _league_name, _rank, _availability_group):
        """Initialise the team."""
        self.club = _club
        self.league = _league_name
        self.rank = _rank
        self.availability_group = _availability_group
        self.court_slots = []
        self.division: int = 0
        self.home_fixtures = []
        self.away_fixtures = []
        self.name = self.club.name + " " + self.league + " " + self.rank

    def write_output(self):
        """Write the team's fixtures to the console."""
        print(
            " ",
            self.league,
            self.rank,
            "Group:",
            self.availability_group,
            "Division:",
            self.division,
        )
        # print("Home_Dates")
        # for d in self.home_dates:
        #     print(d.date.date, d.date.weekday)
        print("Home_Fixtures")
        for f in self.home_fixtures:
            print("   ", f.print())
        print("Away_Fixtures")
        for f in self.away_fixtures:
            print("   ", f.print())

    def club_name(self):
        """Return the name of the club."""
        return self.club.name

    def get_all_fixtures(
        self,
        _is_intra_club=True,
        _is_inter_club=True,
        _include_home=True,
        _include_away=True,
    ):
        """Return a list of all fixtures for the team."""
        all_fixtures = []
        if _include_home:
            all_fixtures.extend(self.home_fixtures)
        if _include_away:
            all_fixtures.extend(self.away_fixtures)
        result = []
        for f in all_fixtures:
            if (f.is_intra_club and _is_intra_club) or (not f.is_intra_club and _is_inter_club):
                result.append(f)
        return result

    def get_fixture_court_slots(self, _include_home=True, _include_away=True) -> list[FixtureCourtSlot]:
        """Return a list of all court slots for the teams fixtures."""
        _fixtures_slots = []
        if _include_home:
            for _hf in self.home_fixtures:
                _fixtures_slots.extend(_hf.fixture_court_slots)
        if _include_away:
            for _af in self.away_fixtures:
                _fixtures_slots.extend(_af.fixture_court_slots)
        return _fixtures_slots

    def __repr__(self):
        """Return the name of the team."""
        return self.name


# courts available to a specific club on a specific date for a teams home fixture.
class CourtSlot:
    """A court slot is a specific court at a specific club on a specific date."""

    def __init__(self, _date: Date, _club: Club, _concurrency_number: int, priority: bool):
        """Create a court slot for a specific date and club."""
        self.date = _date
        self.teams = []
        self.club = _club
        self.date.court_slots.append(self)
        self.concurrency_number = _concurrency_number
        self.name = self.club.name + " " + self.date.date_str + " " + str(self.concurrency_number)
        self.fixtures_court_slot = []
        self.priority = priority

    def add_team(self, _team: Team):
        """Add a team to the court slot."""
        if _team not in self.teams:
            if _team.club == self.club:
                self.teams.append(_team)
                _team.court_slots.append(self)
            else:
                raise ValueError("Attempted to append team from different club")
        else:
            raise ValueError("Team already linked with court slot")

    # def is_week_team_type_match(self):
    #     """Return true if the court slot is for the correct team type for the date."""
    #     if self.date.league_type == "Open/Ladies":
    #         return self.team.league in ["Open", "Ladies 4"]
    #     return self.team.league == "Mixed"

    def write_output(self):
        """Print the court slot name."""
        print(self.name)

    def __repr__(self):
        """Return the string representation of the court slot."""
        return self.name


# A match to be played between 2 teams.
class Fixture:
    """A match to be played between 2 teams."""

    def __init__(self, _home_team: Team, _away_team: Team):
        """Create a fixture between 2 teams."""
        self.home_team: Team = _home_team
        self.away_team: Team = _away_team

        self.name = self.home_team.name + " vs " + self.away_team.name
        self.is_intra_club = self.home_team.club == self.away_team.club
        self.fixture_court_slots = []

        # return self.is_new_fixture()
        if self.is_new_fixture():
            self.home_team.home_fixtures.append(self)
            self.away_team.away_fixtures.append(self)

        self._generate_dates()

    def is_new_fixture(self):
        """Check if the fixture is new."""
        result: bool = self.home_team in [hf.away_team for hf in self.home_team.home_fixtures]
        return not result

    def print(self):
        """Print the fixture and its fixture court slots."""
        print(self.name)
        for fcs in self.fixture_court_slots:
            print("    ", fcs.friendly_name)

    def _generate_dates(self):
        for home_court_slot in self.home_team.court_slots:
            fd = FixtureCourtSlot(self, home_court_slot)
            self.fixture_court_slots.append(fd)

    def __repr__(self):
        """Return the string representation of the fixture."""
        return self.name


# A possible slot available for a fixture
class FixtureCourtSlot:
    """A possible slot available for a fixture."""

    def __init__(self, _fixture: Fixture, _court_slot: CourtSlot):
        """Create a fixture court slot."""
        self.fixture = _fixture
        self.court_slot = _court_slot
        self.is_scheduled = 0

        self.friendly_name = (
            self.fixture.name
            + " - "
            + self.court_slot.date.date_str
            + " - No:"
            + str(self.court_slot.concurrency_number)
        )

        self.identifier = (
            self.fixture.name + self.court_slot.date.date_str + str(self.court_slot.concurrency_number)
        ).replace(" ", "_")

        self.court_slot.fixtures_court_slot.append(self)

    def is_correct_week(self):
        """Return true if the fixture is in the correct week for the court slot."""
        date_is_mixed = self.court_slot.date.league_type == "Mixed"
        match_is_mixed = self.fixture.home_team.league == "Mixed"
        return date_is_mixed == match_is_mixed

        # print("Fixture Date Name")
        # print(self.name)

    def get_week_number(self) -> int:
        """Return the week number of the fixture."""
        return self.court_slot.date.get_week_number()

    def as_dict(self):
        """Return a dictionary representation of the fixture."""
        return {
            "Home Team": self.fixture.home_team.name,
            "Away Team": self.fixture.away_team.name,
            "Date": self.court_slot.date.date_str,
            "Court No.": self.court_slot.concurrency_number,
            "is_scheduled": self.is_scheduled,
            "league": self.fixture.home_team.league,
            "Division": self.fixture.home_team.division,
            "Home Club": self.fixture.home_team.club.name,
            "Away Club": self.fixture.away_team.club.name,
            "Is Correct Week": self.is_correct_week(),
        }

    def __repr__(self):
        """Return a string representation of the fixture."""
        return self.identifier


def main():
    """Run to test the league class."""
    test1 = League("https://docs.google.com/spreadsheets/d/1Mi-fWF63mw8Sdcb_lzHHTTvPqCp0VcJyZaqD5cm6D8U")
    test1.write_teams_entered()

    test1.write_output()


if __name__ == "__main__":
    main()
