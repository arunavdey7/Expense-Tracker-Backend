from __future__ import print_function
from unittest import result
from flask.json import jsonify
from flask import Flask
from flask import request
import hashlib,jwt
from itsdangerous import json
from flask import Flask
from flask_cors import CORS, cross_origin
from datetime import datetime, date
import datetime as dt
import time as t
from apscheduler.schedulers.background import BackgroundScheduler
import os, sys
import base64
from email.mime.text import MIMEText
import google.auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dateutil.relativedelta import relativedelta, MO

app = Flask(__name__)
CORS(app)

@app.route('/expenses', methods=['GET'])
@cross_origin()
def get_info():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    service = build('gmail', 'v1', credentials=creds)
    args = request.args
    on_date = args.get("date")
    result = {
        'transactions':[],
        'total_expenditure':0,
        'date':[],
        'success':False
    }
    if(on_date == '' or on_date == None):
        return jsonify(
            {
                'success':False
            }
        )
    expenses = cron(service,on_date)
    for expense in expenses:
        result['transactions'].append({
            'Amount':expense[0],
            'Type':expense[1],
        })
    result['date'] = on_date
    result['total_expenditure'] = get_todays_expenditure(expenses)
    result['success'] = True
    return jsonify(result)

@cross_origin()
@app.route('/login', methods=['POST'])
def login():
    request_data = request.get_json()
    if(request_data):
        username = request_data['username']
        password = request_data['password']
        if(username == '*****' and password == '*****'):
            return jsonify(
                {
                    'success':True
                }
            )
        return jsonify(
                {
                    'success':False
                }
            )
    return jsonify({
        'success':False
    })


SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


def txn_type(string):
    str_ls = string.split(' ')
    if('credited' in str_ls):
        return 'credit'
    elif('debited' in str_ls):
        return 'debit'
    return 'undefined'


def txn_amount(string):
    str_ls = string.split(' ')
    amount = 0
    for amt in str_ls:
        if(amt.find('Rs.') != -1):
            amount = amt.split('.')[1]
            break
    if(amount == 0):
        amount = str_ls[str_ls.index('INR')+1]
    return amount


def process_datetime(inp):
    date = inp[1]
    month = inp[2]
    year = inp[3][2:]
    time = inp[4]
    calendar_months = ['January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November', 'December']
    month_number = calendar_months.index(month) + 1
    date_string = date+'/'+str(month_number)+'/'+year+' '+time
    date_obj = datetime.strptime(date_string, '%d/%m/%y %H:%M:%S')
    return date_obj


def cron(service,on_date):
    d = on_date
    d = datetime.strptime(d,'%Y-%m-%d').date()

    one_plus_date = d+dt.timedelta(days=1)
    
    result = service.users().messages().list(
        #userId='me', q='from:(alerts@hdfcbank.net) after:'+str(date.today())).execute()
        userId='me', q='from:(alerts@hdfcbank.net) after:'+str(d)+' before:'+str(one_plus_date)).execute()
    messages = result.get('messages')
    data = []
    if(messages):
        for msg in messages:
            txt = service.users().messages().get(
                userId='me', id=msg['id']).execute()
            t_type = txn_type(txt['snippet'])
            if(t_type != 'undefined'):
                t_amt = txn_amount(txt['snippet'])
                data.append((t_amt, t_type, d))
        return data
    return []


def parse_msg(msg):
    if msg.get("payload").get("body").get("data"):
        return base64.urlsafe_b64decode(msg.get("payload").get("body").get("data").encode("ASCII")).decode("utf-8")
    return msg.get("snippet")



def get_todays_expenditure(daily_data):
    total_exp = 0
    for i in daily_data:
        if(i[1] != 'credit'):
            total_exp += float(i[0])
    return total_exp


def get_todays_statement(daily_data):
    for i in daily_data:
        print('Rs.'+str(i[0]), i[1], str(i[2]))
    print('Total Rs.', get_todays_expenditure(daily_data))


# data = cron(service)
# get_todays_statement(data)
# end = t.time()
# print('Total time taken: ', end-start)


if __name__ == "__main__":
    app.run(debug=False, port=6000)