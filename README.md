# BDBL-Scheduling Project

## Introduction
This project handles the scheduling and operation of the BDBL league. Taking input for Gsheet template for each team
along with some league configuration. It produces a schedule for the season matching the chosen requirements. 

## Features
_Coming Soon_

## First Time Set-Up
This project uses google sheets to take the league structure and club availability inputs. 
To get the data from google sheets requires some setup
### How to get your secret
1. Login to https://console.cloud.google.com/welcome
2. Setup a Service Account.
3. Create a project
4. Create a key under service account, Save the json string as client_secret.josn
5. Share all the necessary sheets with the API user as Editor. 
### Sheets
- [Club entry template](https://docs.google.com/spreadsheets/d/1eftYZbRXSH1wP_ocnDws7KhLqCdlDXpDypOlOMH20Hg/edit?usp=drive_link) 
This is the spreadsheet to share with each club.
- [League Management Template](https://docs.google.com/spreadsheets/d/1eyk5vBiaWu91fqs5jhaS4sJYS6Frm4Z23z8ZQdZbR5o/edit?usp=sharing)
This links all the entry spreadsheets and recieves the output schedule

### Prepare Spreadsheets
1. Check the league entry template spreadsheet to ensure it includes the necessary tabs:
  - '0. Club Information'
  - '1. Teams Entering'
  - '2. Availability'
  - '3. Check Provided Enough Dates'
  - 'Lookup Lists'
2. Add any new teams to the lookup list. checking the dropdown references include these new values
3. Update the availability sheet with league dates and bank holidays.
   1. Check the availability table contains all the appropriate dates resizing if neccessary.
4. Ensure all necessary sheets are shared with the API user.
5. Update the API to link to the current years files.
6. Assign teams to an appropriate division.
7. Create a copy for each club and send the sheet, or collect details another way and populate the sheet.



## Roadmap (TODO)
1. Expand the comprehensiveness of the current league entry template spreadsheet.
2. Continually update the API to link to the most recent files.
3. Further optimize the division allocation algorithm for the teams.

## Feedback and Contributions
Feedback and contributions are always welcome. Feel free to open an issue or submit a pull request as needed.

## License
_Coming Soon_

Please note: This README will be continually updated as the project progresses.