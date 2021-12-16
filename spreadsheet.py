import discord
import gspread
from dotenv import load_dotenv
import os
import asyncio

load_dotenv('.env.sheet')

SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')


sheets = gspread.service_account(f"{os.getcwd()}/service_account.json")
sheet = sheets.open_by_key(SPREADSHEET_ID)
worksheet = sheet.get_worksheet(1)

print(sheet)

async def pull_channel(client, id):
    id = int(id)
    channel = client.get_channel(id)

    count = 0
    async for message in channel.history(limit=999999):
        msg = message.content
        msg = msg.split('\n')

        info = {"school": None, "program": None, "date": None, "average": None, "app_type": None, "user": None, 'status': 'Accepted'}

        info['user'] = message.author.name + '#' + message.author.discriminator

        for item in msg:
            if 'School:' in item:
                info['school'] = item.split('School:')[1]
                info['school'] = remove_first_space(info['school'])
            if 'Program:' in item:
                print(item)
                info['program'] = item.split('Program:')[1]
                info['program'] = remove_first_space(info['program'])
            if 'Accepted Date:' in item:
                info['date'] = item.split('Accepted Date: ')[1]
                info['date'] = remove_first_space(info['date'])
            elif 'Date:' in item:
                info['date'] = item.split('Date: ')[1]
                info['date'] = remove_first_space(info['date'])
            if 'Average:' in item:
                info['average'] = item.split('Average: ')[1]
                info['average'] = remove_first_space(info['average'])
            if 'Applicant Type:' in item:
                info['app_type'] = item.split('Applicant Type: ')[1]
                info['app_type'] = remove_first_space(info['app_type'])
        print(info)
        final_message = [info['status'], info['school'], info['program'], info['average'], info['date'], info['app_type'], info['user']]

        worksheet.append_rows(values=[final_message])

        count += 1
        if count == 50:
            count = 0
            await asyncio.sleep(120)

def remove_first_space(item):
    print(item)
    if item[0] == ' ':
        print(item[1::])
        return item[1::]
    else:
        return item
