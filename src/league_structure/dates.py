"""Defines the Dates class"""
from __future__ import annotations

from datetime import datetime, timedelta

from src.league_structure.date import Date


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
