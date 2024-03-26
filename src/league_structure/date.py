"""Defines the date class"""

from __future__ import annotations

from datetime import datetime


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
