import gspread
import re
import matplotlib
matplotlib.use('Agg')           # Render to backend
import matplotlib.pyplot as plt
import statistics
import os
from dotenv import load_dotenv
import scipy

# Columns on the LIST spreadsheet (list = 0 based, spreadsheet = 1 based)
STATUS_COL = 0
SCHOOL_COL = 1
PROGRAM_COL = 2
AVERAGE_COL = 3
APPLICANTTYPE_COL = 5
OTHER_COL = 7
MESSAGEID_COL = 8
TAGS_COL = 9


# Connect to Google Spreadsheets
load_dotenv()
gc = gspread.service_account(filename='service_account.json')
public_spreadsheet = gc.open_by_key(os.getenv('SPREADSHEET_KEY'))
private_spreadsheet = gc.open_by_key(os.getenv('STAFF_SPREADSHEET_KEY'))
worksheets = public_spreadsheet.worksheets()

"""
Returns a list of applicant years (names of the sheets on the spreadsheet)
"""
def get_applicant_years():
    applicant_years = [sheet.title for sheet in worksheets]
    applicant_years.remove("Home")

    # Note: The returned list must be less than 24 in length
    return applicant_years


"""
Returns the row number containing a specific message_id
"""
def get_sheet_and_row_by_message_id(message_id):
    sheets = get_applicant_years()

    row = None

    for sheet in sheets:
        current_sheet = public_spreadsheet.worksheet(sheet)

        cell = current_sheet.find(message_id)

        if cell is not None:
            row = int(cell.row)
            break

    return sheet, row


"""
Appends a new row to the spreadsheet with the given values
"""
async def add_to_spreadsheet(user, school, program, status, average, date, applicant_type, anonymous, other, tags, decision_id):
    current_sheet = public_spreadsheet.get_worksheet(1)     # Current year's spreadsheet
    private_current_sheet = private_spreadsheet.get_worksheet(1)

    username = user.name if not anonymous else "anonymous"          # Make username anonymous if anonymous is set
    other_info = other if other is not None else ""                 # Make other info a null string if its empty
    decision_id_string = str(decision_id) if not anonymous else ""  # Add decision ID if not anonymous
    tags_string = ', '.join(tags)

    # Add to public spreadsheet
    new_row_values = [status, school, program, average, date, applicant_type, username, other_info, decision_id_string, tags_string]
    current_sheet.append_row(new_row_values)

    # Add to private spreadsheet
    new_row_values[6] = user.name
    new_row_values[8] = str(decision_id)
    new_row_values.append("") if not anonymous else new_row_values.append(True)  # Anonymous mode
    private_current_sheet.append_row(new_row_values)


"""
Deletes the given row from the public spreadsheet
"""
async def delete_row_by_row_num(applicant_year, row):
    current_sheet = public_spreadsheet.worksheet(applicant_year)

    current_sheet.delete_rows(int(row))

"""
Updates the row on the private spreadsheet that contains the given user ID to show that it has been deleted
"""
async def delete_decision_private(decision_id):
    sheets = get_applicant_years()
    row_number = 1

    for sheet in sheets:
        current_sheet = private_spreadsheet.worksheet(sheet)
        sheet_values = current_sheet.get_all_values()

        for row in sheet_values:
            id = row[MESSAGEID_COL]

            if str(decision_id) == str(id):
                current_sheet.update(f"L{row_number}", True)    # Deleted

            row_number += 1
            

"""
Generates histogram in "hist.png"
Returns average, median, sample size, predicted label and classifcation status in form of a dictonary
Returns None if no data
"""
async def stats(school, program, applicant_year, tags):
    HISTOGRAM_FILENAME = "hist.png"

    if applicant_year == 'ALL':
        sheets = get_applicant_years()
        applicant_year = '-'.join([sheets[-1].split('-')[0], sheets[0].split('-')[1]])
    else:
        sheets = [applicant_year]

    marks = []

    for sheet in sheets:
        current_sheet = public_spreadsheet.worksheet(sheet)
        sheet_values = current_sheet.get_all_values()

        # Search for matching rows
        for row in sheet_values:
            # Get values from spreadsheet
            spreadsheet_status = row[STATUS_COL]
            spreadsheet_applicant_type = row[APPLICANTTYPE_COL]
            spreadsheet_tags = row[TAGS_COL]

            if spreadsheet_status == "Accepted" and spreadsheet_applicant_type == "101" and spreadsheet_tags.lower() == ', '.join(tags).lower():
                # Get the first float that appears
                if re.search(r"\d+\.\d+", row[AVERAGE_COL]):
                    marks.append(float(re.search(r"\d+\.\d+", row[AVERAGE_COL]).group()))
                
                # Else get the first integer that appears
                elif re.search(r'\d+', row[AVERAGE_COL]):
                    marks.append(float(re.search(r'\d+', row[AVERAGE_COL]).group()))

    num_of_applicants = len(marks)

    # Remove outliers if there are more than 5 data points (points not within 3 std deivs of the mean)
    if num_of_applicants > 30:
        zscores = map(abs, scipy.stats.zscore(marks))
        marks = [mark for mark, zscore in zip(marks, zscores) if zscore < 3]
        num_of_applicants = len(marks)

    # Calculate summary statistics
    if num_of_applicants != 0:
        average = round(sum(marks)/num_of_applicants, 2)
        median = round(statistics.median(marks), 2)

        # Generate histogram
        plt.hist(marks, bins=range(round(min(marks)-0.5), round(max(marks)+1)))
        plt.title(f"101 Admission averages for {school} {program} for {applicant_year}")
        plt.xlabel("Average")
        plt.ylabel("Number of applicants")
        plt.locator_params(axis='x', integer=True)
        plt.locator_params(axis='y', integer=True)
        plt.savefig(HISTOGRAM_FILENAME)
        plt.close()

        stat_info = {
            "average": average, 
            "median": median, 
            "sample size": num_of_applicants,
            "calculated applicant years": applicant_year,   # bandaid fix for ALL
            "filename": HISTOGRAM_FILENAME
        }
    else:
        stat_info = None    # No Data

    return stat_info