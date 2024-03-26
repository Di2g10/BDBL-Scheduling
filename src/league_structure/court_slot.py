"""Defines the court_slot class."""
from __future__ import annotations

from src.league_structure.date import Date
from src.league_structure.team import Team
import src.league_structure.club as club


class CourtSlot:
    """A court slot is a specific court at a specific club on a specific date."""

    def __init__(self, _date: Date, _club: club.Club, _concurrency_number: int, priority: bool):
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
