from __future__ import print_function
from typing import List, Tuple, Dict, Any, Union
from datetime import datetime, timedelta, date
import pandas as pd
from gsheets import get_gsheet_data, write_gsheet_output_data


class Team:
    pass


class Date:
    pass


# League is the group of all clubs and teams entering for all Divisions for the year.
class League:

    def __init__(self, _league_management_url):
        self.name: str = "Something"
        self.league_management_URL = _league_management_url
        self.clubs = []
        self.dates = Dates()
        self.fixtures = []

        # Club Entry management
        _club_entry_management = pd.DataFrame(get_gsheet_data(self.league_management_URL,
                                                              "Club Entry Management").get_all_records())
        for club_url in _club_entry_management["Entry URL"]:
            if club_url:
                c = Club(self, club_url)
                self.clubs.append(c)

        self._get_previous_league_position()

        self._generate_fixtures()

        # self.dates.calculate_dates_numbers()

    def _get_previous_league_position(self):
        _raw_gsheet = get_gsheet_data(self.league_management_URL, "Previous League organisation").get_all_records()
        _previous_league_position_df = pd.DataFrame(_raw_gsheet)
        _headings = ["League", "Club", "Team", "Previous League Position", "Teams Entered", "New Division"]
        for index, row in _previous_league_position_df[_headings].iterrows():
            _club: Club = self.get_club(row["Club"])
            if _club:
                _team: Team = _club.get_team(row["League"], row["Team"])
                if _team:
                    try:
                        _team.division = int(row["New Division"])
                    except ValueError as err:
                        print(f'Error Cause by {row.to_markdown()}')
                        raise ValueError(f'Error Cause by {row}')

                else:
                    print("Missing Team:", row["Club"], row["League"], row["Team"])
            else:
                print("Missing Club", row["Club"])

        for t in self.get_teams():
            if t.division == 0:
                raise ValueError(f"Team {t.name} doesn't have specific rank from previous season. "
                                 f"Missing from spreadsheet")

    def get_club(self, _club_name_str):
        for c in self.clubs:
            if c.name == _club_name_str:
                return c

    def write_output(self):
        print("Dates:")
        for d in self.dates.dates:
            print(d.date)
        for c in self.clubs:
            c.write_output()

    def get_teams(self):
        _team_list = []
        for c in self.clubs:
            _team_list.extend(c.teams)
        return _team_list

    def write_teams_entered(self):
        _league_list = []
        _club_list = []
        _rank_list = []
        for t in self.get_teams():
            _league_list.append(t.league)
            _club_list.append(t.club.name)
            _rank_list.append(t.rank)
        _data = {"League": _league_list,
                 "Club": _club_list,
                 "Rank": _rank_list}
        _data_dict = pd.DataFrame(_data)
        write_gsheet_output_data(_data_dict, "Teams Entered", self.league_management_URL)

    def _generate_fixtures(self):
        for hm_team in self.get_teams():
            for aw_team in self.get_teams():
                if hm_team != aw_team \
                   and hm_team.league == aw_team.league \
                   and hm_team.division == aw_team.division:
                    fixture_i = Fixture(hm_team, aw_team)
                    self.fixtures.append(fixture_i)

    def get_fixture_court_slots(self):
        _fixtures_dates = []
        for _fixture in self.fixtures:
            _fixtures_dates.extend(_fixture.fixture_court_slots)
        return _fixtures_dates

    def get_fixture_court_slots_for_teams_on_date(self, _teams: List, _date: Date):
        result = []
        for _fixture in self.fixtures:
            fixture_team_match_a = _fixture.home_team in _teams
            fixture_team_match_h = _fixture.away_team in _teams
            if fixture_team_match_a or fixture_team_match_h:
                for fcs in _fixture.fixture_court_slots:
                    if fcs.court_slot.date == _date:
                        result.append(fcs)
        return result

    def get_specific_fixture_court_slot(self, _home_team, _away_team, _date: Date):
        result = []
        for _fixture in self.fixtures:
            if _fixture.home_team == _home_team and \
                    _fixture.away_team == _away_team:
                for fcs in _fixture.fixture_court_slots:
                    if fcs.court_slot.date == _date:
                        result.append(fcs)
        return result

    def get_date_obj_from_str(self, _date_str):
        _date = datetime.strptime(_date_str, '%d/%m/%Y')
        for d in self.dates.dates:
            if d.date == _date:
                return d
        raise ValueError("Date not Found: " + _date_str)

    def get_team_obj_from_str(self, _team_name_str):
        for t in self.get_teams():
            if t.name == _team_name_str:
                return t
        raise ValueError("Team Not Found: " + _team_name_str)

    def check_league_data(self):
        print("League name", self.name)
        print("URL", self.league_management_URL)
        print("No. Clubs", len(self.clubs))
        print("No. fixtures", len(self.fixtures))
        print()
        print("Date Weeks")

        def d_sort(_date: Date):
            return _date.date_delta_from_start

        for d in sorted(self.dates.dates, key=lambda _d: _d.date_delta_from_start):
            print("Date:", d.date, "Delta:", d.date_delta_from_start.days, "Delta Weeks", d.date_delta_from_start.days // 7)
        print()

    def get_min_week_number(self):
        _list = (d.get_week_number() for d in self.dates.dates)
        result = min(_list)
        return result

    def get_christmas_week_number(self) -> int:
        """
        Function to get the first schedulable week number after christmas
        :return: 'the week number of the first date after christmas
        """
        dates = (d.date for d in self.dates.dates)
        min_date = min(dates)
        second_year = min_date.year + 1
        dates_in_second_year = (d.get_week_number() for d in self.dates.dates if d.date.year == second_year)
        result = min(dates_in_second_year)
        return result

    def __repr__(self):
        return self.name


# Clubs are a group of teams entering that may share players and play at the same venue and share courts.
class Club:
    def __init__(self, _league: League, _file_location):
        self.fileLocation = _file_location
        self.league = _league
        self.court_slots = []

        # Club Info Sheet
        _club_info = pd.DataFrame(get_gsheet_data(self.fileLocation, "0. Club Information").get_all_records())
        self.name = _club_info["Club Name"][0]
        if self.name == "BH Pegasus":
            print("BH Pegagsus")

        # Teams Entering Sheet
        _teams_entering = pd.DataFrame(get_gsheet_data(self.fileLocation, "1. Teams Entering").get_all_records())
        _teams_columns = ["League Name", "Team Rank", "Availability Group", "Comments", "Home Nights Required"]
        self.teams = []

        for index, row in _teams_entering[_teams_columns].iterrows():
            if row["League Name"]:
                t = Team(self, row["League Name"], row["Team Rank"], row["Availability Group"])
                self.teams.append(t)

        # Get Club Availability
        self._get_club_availability()

    def _get_club_availability(self):
        _club_availability = pd.DataFrame(get_gsheet_data(self.fileLocation, "2. Availability").get("C11:K223"))
        _club_availability.columns = _club_availability.iloc[0]
        _club_availability = _club_availability[1:]
        _date_columns = ["Date", "League Type", "Weekday", "Available", "No. Concurrent Matches"]
        print(self.name)
        for index, row in _club_availability[_date_columns].iterrows():
            if row["Available"] != "Unavailable":
                _date = self.league.dates.add_date(row["Date"], row["League Type"], row["Weekday"])
                for _concurrent_matches in range(int(row["No. Concurrent Matches"])):
                    _court_slot = CourtSlot(_date, self, _concurrent_matches)
                    self.court_slots.append(_court_slot)
                    for _team in self.teams:
                        if _team.availability_group == row["Available"]:
                            _court_slot.add_team(_team)

    def write_output(self):
        print(self.name)
        # print(self.availability_weeks)
        # print(self.availability_detail)
        for t in self.teams:
            t.write_output()

    def get_team(self, _league, _team_rank):
        for t in self.teams:
            if t.league == _league and t.rank == _team_rank:
                return t

    def get_fixture_court_slots(self, _include_home=True, _include_away=True):
        _fixtures = []
        for _team in self.teams:
            _fixtures.extend(_team.get_fixture_court_slots(_include_home, _include_away))
        return _fixtures

    def get_all_fixtures(self, _is_intra_club=True, _is_inter_club=True, _include_home=True, _include_away=True):
        result = []
        for t in self.teams:
            result.extend(t.get_all_fixtures(_is_intra_club, _is_inter_club,_include_home,_include_away))
        return result

    def __repr__(self):
        return self.name


# dates are specific days in the league year. There should be at most one instance per day.
class Date:
    def __init__(self, _date_str, _league_type, _weekday, _date_anchor):
        self.date_str: str = _date_str
        self.date: datetime = datetime.strptime(_date_str, '%d-%b-%Y')
        self.league_type = _league_type
        self.weekday = _weekday
        self.court_slots = []
        # Anchor date could be wrong for early dates added if not added in order
        self.date_delta_from_start = self.date - _date_anchor

    # def calculate_date_numbers(self, min_date: datetime):
    #     self.date_delta_from_start = self.date - min_date
    def __repr__(self):
        return self.date_str

    def get_week_number(self):
        return self.date_delta_from_start.days // 7


# Collection of all dates available to the league. Handles the uniques of the Date object.
class Dates:
    def __init__(self):
        self.dates = []
        self.date_values = ()
        self.min_date = datetime(2021, 11, 1)

    def add_date(self, _date_str, _league_type, _weekday):
        _date_tuple = (_date_str, )
        for d in self.dates:
            if d.date_str == _date_str:
                return d
        _date_obj = Date(_date_str, _league_type, _weekday, self.min_date)
        self.dates.append(_date_obj)
        # self._update_min_date(_date_obj)
        return _date_obj

    def _update_min_date(self, _date: Date):
        if _date.date < self.min_date:
            self.min_date = _date.date

    def calculate_dates_numbers(self):
        for d in self.dates:
            d.calculate_date_numbers(self.min_date)


# An entry into a specific division of a specific league type.
class Team:
    def __init__(self, _club: Club, _league_name, _rank, _availability_group):
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
        print(" ", self.league, self.rank, "Group:", self.availability_group, "Division:", self.division)
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
        return self.club.name

    def get_all_fixtures(self, _is_intra_club=True, _is_inter_club=True, _include_home = True, _include_away = True):
        all_fixtures = []
        if _include_home:
            all_fixtures.extend(self.home_fixtures)
        if _include_away:
            all_fixtures.extend(self.away_fixtures)
        result = []
        for f in all_fixtures:
            if (f.is_intra_club and _is_intra_club)\
                    or (not f.is_intra_club and _is_inter_club):
                result.append(f)
        return result

    def get_fixture_court_slots(self, _include_home=True, _include_away=True):
        _fixtures_slots = []
        if _include_home:
            for _hf in self.home_fixtures:
                _fixtures_slots.extend(_hf.fixture_court_slots)
        if _include_away:
            for _af in self.away_fixtures:
                _fixtures_slots.extend(_af.fixture_court_slots)
        return _fixtures_slots

    def __repr__(self):
        return self.name


# courts available to a specific club on a specific date for a teams home fixture.
class CourtSlot:
    def __init__(self, _date: Date, _club: Club, _concurrency_number):
        self.date = _date
        self.teams = []
        self.club = _club
        self.date.court_slots.append(self)
        self.concurrency_number = _concurrency_number
        self.name = self.club.name + " " + self.date.date_str + " " + str(self.concurrency_number)
        self.fixtures_court_slot = []

    def add_team(self, _team: Team):
        if _team not in self.teams:
            if _team.club == self.club:
                self.teams.append(_team)
                _team.court_slots.append(self)
            else:
                raise ValueError('Attempted to append team from different club')
        else:
            raise ValueError('Team already linked with court slot')

    def is_week_team_type_match(self):
        if self.date.league_type == "Open/Ladies":
            return self.team.league in ["Open", "Ladies 4"]
        else:
            return self.team.league == "Mixed"

    def write_output(self):
        print(self.name)

    def __repr__(self):
        return self.name


# A match to be played between 2 teams.
class Fixture:
    def __init__(self, _home_team: Team, _away_team: Team):
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
        result: bool = self.home_team in [hf.away_team for hf in self.home_team.home_fixtures]
        return not result

    def print(self):
        print(self.name)
        for fcs in self.fixture_court_slots:
            print("    ", fcs.friendly_name)

    def _generate_dates(self):
        for home_court_slot in self.home_team.court_slots:
            fd = FixtureCourtSlot(self, home_court_slot)
            self.fixture_court_slots.append(fd)

    def __repr__(self):
        return self.name


# A possible slot available for a fixture
class FixtureCourtSlot:
    def __init__(self, _fixture: Fixture, _court_slot: CourtSlot):
        self.fixture = _fixture
        self.court_slot = _court_slot
        self.is_scheduled = 0

        self.friendly_name = self.fixture.name + " - " \
                             + self.court_slot.date.date_str \
                             + " - No:" + str(self.court_slot.concurrency_number)

        self.identifier = (self.fixture.name +\
                           self.court_slot.date.date_str +\
                           str(self.court_slot.concurrency_number)).replace(' ','_')

        self.court_slot.fixtures_court_slot.append(self)

    def is_correct_week(self):
        date_is_mixed = self.court_slot.date.league_type == "Mixed"
        match_is_mixed = self.fixture.home_team.league == "Mixed"
        result = date_is_mixed == match_is_mixed
        return result

        # print("Fixture Date Name")
        # print(self.name)

    def get_week_number(self):
        return self.court_slot.date.get_week_number()

    def as_dict(self):
        result = {'Home Team': self.fixture.home_team.name,
                  'Away Team': self.fixture.away_team.name,
                  'Date': self.court_slot.date.date_str,
                  'Court No.': self.court_slot.concurrency_number,
                  'is_scheduled': self.is_scheduled,
                  'league': self.fixture.home_team.league,
                  'Division': self.fixture.home_team.division,
                  'Home Club': self.fixture.home_team.club.name,
                  'Away Club': self.fixture.away_team.club.name,
                  'Is Correct Week': self.is_correct_week()
                  }
        return result

    def __repr__(self):
        return self.identifier


def main():
    test1 = League("https://docs.google.com/spreadsheets/d/1Mi-fWF63mw8Sdcb_lzHHTTvPqCp0VcJyZaqD5cm6D8U")
    test1.write_teams_entered()

    test1.write_output()


if __name__ == '__main__':
    main()
