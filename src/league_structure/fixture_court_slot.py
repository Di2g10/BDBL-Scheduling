"""Defines the FixtureCourtSlot Class"""
from __future__ import annotations

from src.league_structure.court_slot import CourtSlot
from src.league_structure.fixture import Fixture


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
