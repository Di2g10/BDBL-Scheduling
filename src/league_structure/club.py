"""Defines the Club class."""

from __future__ import annotations


import src.league_structure.court_slot as court_slot
from src.league_structure.date import Date
from src.league_structure.dates import Dates
import src.league_structure.team as team

from gsheets import get_gsheet_worksheet


class Club:
    """Club Class.

    Clubs are a group of teams entering that may share players
    and play at the same venue
    and share courts.
    """

    def __init__(self, dates: Dates, file_location):
        """Initialise the Club Class."""
        self.name = _get_club_names_from_gsheet(file_location)
        self.teams: list[team.Team] = self._create_teams_from_gsheet(file_location)
        self.court_slots: list[court_slot.CourtSlot] = self._create_court_slots(dates, file_location)

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

    def _create_teams_from_gsheet(self, file_location: str) -> list[team.Team]:
        team_info = _get_teams_from_gsheet(file_location)
        teams: list[team.Team] = []

        for row in team_info:
            if row["Club Name"]:
                t = self._create_team_from_dict(row)
                teams.append(t)

        return teams

    def _create_team_from_dict(self, team_dict: dict[str, int | float | str]):
        return team.Team(
            club=self,
            league_name=team_dict["League Name"],
            rank=team_dict["Team Rank"],
            availability_group=team_dict["Availability Group"],
            division=team_dict["Division"],
        )

    def _create_court_slots(self, dates: Dates, file_location: str) -> list[court_slot.CourtSlot]:
        availability = _get_club_availability_from_gsheet(file_location)
        court_slots: list[court_slot.CourtSlot] = []
        for row in availability:
            if row["Available"] == "Unavailable":
                continue
            date = dates.add_date(row["Date"], row["League Type"], row["Weekday"])
            court_slots.extend(self._create_court_slot_for_date(date, row))
        return court_slots

    def _create_court_slot_for_date(self, date: Date, row: dict[str, int | float | str]) -> list[court_slot.CourtSlot]:
        priority = bool(row.get("Priority", False))
        court_slots: list[court_slot.CourtSlot] = []
        for concurrent_matches in range(int(row["No. Concurrent Matches"])):
            _court_slot = court_slot.CourtSlot(date, self, concurrent_matches, priority)
            court_slots.append(_court_slot)
            for t in self.teams:
                if t.availability_group == row["Available"]:
                    _court_slot.add_team(t)
        return court_slots


def _get_teams_from_gsheet(file_location: str) -> list[dict[str, int | float | str]]:
    teams_sheet = get_gsheet_worksheet(file_location, "1. Teams Entering")
    teams_columns = ["League Name", "Team Rank", "Availability Group", "Division", "Comments", "Home Nights Required"]
    return teams_sheet.get_all_records(expected_headers=teams_columns)


def _get_club_names_from_gsheet(file_location: str) -> str:
    club_info_sheet = get_gsheet_worksheet(file_location, "0. Club Information")
    return club_info_sheet.get_all_records(expected_headers=["Club Name"])[0]["Club Name"]


def _get_club_availability_from_gsheet(file_location: str) -> list[dict[str, int | float | str]]:
    data = get_gsheet_worksheet(file_location, "2. Availability").get("C11:L300")
    headers = data.pop(0)
    return [dict(zip(headers, row, strict=True)) for row in data]
