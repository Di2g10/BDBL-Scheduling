"""Module contains functions to read and write data to google sheets."""

import time
from datetime import datetime
from pathlib import Path

import gspread
from oauth2client.service_account import ServiceAccountCredentials


def get_gsheet_data(file_location, sheet_name):
    """Download data from a Google sheets spreadsheet."""
    print(datetime.now())
    time.sleep(3)
    scope = Path("client_secret.json")
    credentials = ServiceAccountCredentials.from_json_keyfile_name(scope)
    client = gspread.authorize(credentials)
    worksheet = client.open_by_url(file_location).worksheet(sheet_name)
    data = worksheet.get_all_records()
    return worksheet


def write_gsheet_output_data(output_data, sheet_name, file_location):
    """Write data to a Google sheets spreadsheet."""
    print(datetime.now())
    time.sleep(3)
    scope = Path("client_secret.json")
    credentials = ServiceAccountCredentials.from_json_keyfile_name(scope)
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_url(file_location)
    worksheet_list = spreadsheet.worksheets()
    does_sheet_exists = False
    for worksheet in worksheet_list:
        if worksheet.title == sheet_name:
            does_sheet_exists = True
            output_worksheet = worksheet

    if not does_sheet_exists:
        output_worksheet = spreadsheet.add_worksheet(title=sheet_name, rows="100", cols="20")
        print("sheet created Called ", output_worksheet)
    if output_worksheet:
        output_worksheet.clear()
        output_worksheet.update([output_data.columns.values.tolist(), *output_data.values.tolist()])
