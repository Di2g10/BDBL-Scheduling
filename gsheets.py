import gspread
from oauth2client.service_account import ServiceAccountCredentials
from pathlib import Path
from datetime import datetime, timedelta, date
import time


def get_gsheet_data(_file_location, _sheet_name):
    """Downloads data from a google sheets spreadsheet"""

    print(datetime.now())
    time.sleep(3)
    _scope = Path("client_secret.json")
    _credentials = ServiceAccountCredentials.from_json_keyfile_name(_scope)
    _client = gspread.authorize(_credentials)
    _worksheet = _client.open_by_url(_file_location).worksheet(_sheet_name)
    _data = _worksheet.get_all_records()
    return _worksheet


def write_gsheet_output_data(_output_data, _sheet_name, _file_location):
    print(datetime.now())
    time.sleep(3)
    _scope = Path("client_secret.json")
    _credentials = ServiceAccountCredentials.from_json_keyfile_name(_scope)
    _client = gspread.authorize(_credentials)
    _spreadsheet = _client.open_by_url(_file_location)
    _worksheet_list = _spreadsheet.worksheets()
    _does_sheet_exists = False
    for _worksheet in _worksheet_list:
        if _worksheet.title == _sheet_name:
            _does_sheet_exists = True
            _output_worksheet = _worksheet

    if not _does_sheet_exists:
        _output_worksheet = _spreadsheet.add_worksheet(title=_sheet_name, rows="100", cols="20")
        print("sheet created Called ", _output_worksheet)

    _output_worksheet.clear()
    _output_worksheet.update([_output_data.columns.values.tolist()] + _output_data.values.tolist())

