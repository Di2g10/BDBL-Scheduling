"""Test the end to end process works correctly."""
from main import reload_league_data_from_gsheet
from scheduling import Schedule


def test_main():
    """
    This method is the entry point of the program.
    """
    league_management_url = "https://docs.google.com/spreadsheets/d/1cN1hr5q8is1uMnm6_hI7YusYKAEfD6o5SVSGpodTyzw"  # V3
    predefined_fixtures_url = "https://docs.google.com/spreadsheets/d/1GHFVMuVi2NaAu7W9gqy7eSxZmJsxfbTkh33S1nWbT8Q"

    league = reload_league_data_from_gsheet(_load_from_gsheets=False, _league_management_url=league_management_url)
    # Print League data stats
    league.check_league_data()

    league.write_teams_entered()

    # league.write_output()

    # min_incorrect_weeks = _get_min_incorrect_weeks(league, predefined_fixtures_url)
    # max_prioritised_slots = _get_max_prioritised_slots(league, predefined_fixtures_url, min_incorrect_weeks)

    min_incorrect_weeks = 1
    max_prioritised_slots = 6

    print(f"Min Incorrect Weeks = {min_incorrect_weeks}")
    print(f"max prioritised Slots = {max_prioritised_slots}")

    Schedule(
        league=league,
        predefined_fixtures_url=predefined_fixtures_url,
        allowed_run_time=60,
        num_allowed_incorrect_fixture_week=min_incorrect_weeks,
        num_forced_prioritised_nights=max_prioritised_slots,
        write_output=True,
    )

    assert True