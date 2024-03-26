"""Defines the team class"""

from __future__ import annotations

import src.league_structure.fixture_court_slot as fixture_court_slot
import src.league_structure.club as club


class Team:
    """A team is a club in a league in a division.

    It has a rank within the division and a home night.
    """

    def __init__(self, club: club.Club, league_name, rank, availability_group):
        """Initialise the team."""
        self.club = club
        self.league = league_name
        self.rank = rank
        self.availability_group = availability_group
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

    def get_fixture_court_slots(
        self, _include_home=True, _include_away=True
    ) -> list[fixture_court_slot.FixtureCourtSlot]:
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
