from src.import_league import _get_id_from_url


def test_get_id_from_url():
    url = "https://docs.google.com/spreadsheets/d/1cN1hr5q8is1uMnm6_hI7YusYKAEfD6o5SVSGpodTyzw/edit?usp=sharing"
    id = "1cN1hr5q8is1uMnm6_hI7YusYKAEfD6o5SVSGpodTyzw"
    assert _get_id_from_url(url) == id