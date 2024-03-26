"""Defines the Club class."""

from __future__ import annotations

import pandas as pd

import src.league_structure.court_slot as court_slot
import src.league_structure.team as team
import src.league_structure.league as league

from gsheets import get_gsheet_worksheet


class Club:
    """Club Class.

    Clubs are a group of teams entering that may share players
    and play at the same venue
    and share courts.
    """

    def __init__(self, _league: league.League, _file_location):
        """Initialise the Club Class."""
        self.fileLocation = _file_location
        self.league = _league
        self.court_slots = []

        # Club Info Sheet
        club_info_sheet = get_gsheet_worksheet(self.fileLocation, "0. Club Information")
        self.name = club_info_sheet.get_all_records(expected_headers=["Club Name"])[0]["Club Name"]

        # Teams Entering Sheet
        teams_sheet = get_gsheet_worksheet(self.fileLocation, "1. Teams Entering")
        teams_columns = ["League Name", "Team Rank", "Availability Group", "Comments", "Home Nights Required"]
        teams = teams_sheet.get_all_records(expected_headers=teams_columns)

        self.teams = []

        for row in teams:
            if row["League Name"]:
                t = team.Team(
                    club=self,
                    league_name=row["League Name"],
                    rank=row["Team Rank"],
                    availability_group=row["Availability Group"],
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
                    _court_slot = court_slot.CourtSlot(_date, self, _concurrent_matches, priority)
                    self.court_slots.append(_court_slot)
                    for t in self.teams:
                        if t.availability_group == row["Available"]:
                            _court_slot.add_team(t)

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
