"""Defines the fixture Class"""
from __future__ import annotations

import src.league_structure.fixture_court_slot as fixture_court_slot
from src.league_structure.team import Team


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

    def print(self):  # noqa A003
        """Print the fixture and its fixture court slots."""
        print(self.name)
        for fcs in self.fixture_court_slots:
            print("    ", fcs.friendly_name)

    def _generate_dates(self):
        for home_court_slot in self.home_team.court_slots:
            fd = fixture_court_slot.FixtureCourtSlot(self, home_court_slot)
            self.fixture_court_slots.append(fd)

    def __repr__(self):
        """Return the string representation of the fixture."""
        return self.name
