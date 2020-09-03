import os
import sys
from pprint import pprint
from flask import Flask, render_template, redirect, request, jsonify, session
from flask_session import Session
from tempfile import mkdtemp
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from webhook import send
import random
from copy import copy
from datetime import date, datetime

app = Flask(__name__)

scope = ["https://spreadsheets.google.com/feeds",'https://www.googleapis.com/auth/spreadsheets',"https://www.googleapis.com/auth/drive.file",'https://www.googleapis.com/auth/drive']

creds = ServiceAccountCredentials.from_json_keyfile_name('creds.json', scope)

client = gspread.authorize(creds)

sheet = client.open("Fireworks pre-order").sheet1



counts = []
mult = []
omit = {}

app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)



global user_count
user_count = 0
global summary
summary = {}
global allow
allow = True

@app.route("/", methods=['GET', 'POST'])
def index():
    global data
    data = sheet.get_all_records()
    totalCost = 0.00
    global user_count
    size = len(data)
    if selling(data[0]['Selling Dates'], data[0]['Selling Times']):
        if request.method == 'POST':
            if len(counts) > 0 or len(omit) > 0:
                del counts[:]
                del mult[:]
                omit.clear()
                totalCost = 0.00
            else:
                totalCost = 0.00
            for i in range(len(data)):
                bought = request.form.get(str(i))
                if not bought:
                    counts.append(-1)
                    mult.append(-1)
                    omit.update( {i : False} )
                else:
                    omit.update( {i : True } )
                    counts.append(bought)
                    tmp = float(data[i]['Firework price'][1:]) * float(counts[i])
                    mult.append('{:0.2f}'.format(tmp))
                    totalCost = ('{:0.2f}'.format(float(totalCost) + float(mult[i])))
                    
            global user_count
            global summary
            summary.update( {user_count: {'counts': copy(counts), 'mult': copy(mult),
                        'omit': copy(omit), 'totalCost': totalCost, 'name': request.form.get('name')}} )
            order = summary[user_count]['name']
            if order and summary[user_count]['totalCost'] != '0.00':
                user_count += 1
                return render_template('summary.html',table=counts, amount=size, fire=data, mult=mult, name=order, omit=omit, total=totalCost)

            else:
                return render_template('tmp.html')

        else:
            maxCount = []
            for i in range(len(data)):
                if data[i]['Inventory Count'] > 0:
                    maxCount.append(data[i]['Inventory Count'])
                else:
                    maxCount.append(0)
            return render_template('homepage.html', sheet=data, LENGTH=size, max=maxCount)
    else:
        return render_template('notSelling.html', dates=data[0]['Selling Dates'], times=data[0]['Selling Times'])


@app.route('/receipt')
def receipt():
    global data
    global user_count
    global summary
    global allow

    if user_count > 0:
        for i in range(len(summary)):
            name = summary[i]['name']
            costTotal = summary[i]['totalCost']
            fireCount = summary[i]['mult']
            if name and costTotal != '0.00':
                message = 'Order name: ' + name + '\n' + '\n'
                for j in range(len(data)):
                    if summary[i]['omit'][j] and fireCount[j] != '0.00':
                        message += data[j]['Firework name'] + ' X' + summary[i]['counts'][j] + ' for: $' + fireCount[j] + '\n'
                        sheet.update_cell(j + 2, 6, data[j]['Inventory Count'] - int(summary[i]['counts'][j]))
                    if j == len(data) - 1:
                        message += 'Total Purchase Price: $' + costTotal + '\n' + '--------------------------------' + '\n'
                send(message, data[0]['Webhook URL'])
        user_count = 0
        summary.clear()
        return render_template('sent.html')
    else:
        return render_template('tmp.html')




def selling(dates, times): 
    today = datetime.now()

    startDate = str(datetime.strptime(dates.replace('-', ' ').split()[0] + ' ' + dates.replace('-', ' ').split()[1], '%B %d'))[5:10]
    endDate = str(datetime.strptime(dates.replace('-', ' ').split()[2] + ' ' + dates.replace('-', ' ').split()[3], '%B %d'))[5:10]
    startTime = to24hr(str(datetime.strptime(times.replace('-', ' ').split()[0], '%I:%M').time()) + ' AM')
    endTime = to24hr(str(datetime.strptime(times.replace('-', ' ').split()[2], '%H:%M').time()) + ' PM')


    if today.strftime('%m-%d') < str(startDate) or today.strftime('%m-%d') > str(endDate):
        return False
    elif today.strftime('%H:%M:%S') < str(startTime) or today.strftime('%H:%M:%S') > str(endTime):
        return False
    else:
        return True

def to24hr(time):
    tmp = len(time)
    if tmp == 7:
        time = '0' + time[:4] + ':00' + time[-2:]
    elif tmp == 8:
        time = time[:5] + ':00' + time[-2:]
    elif tmp == 10:
        time = '0' + time[:5]
    else:
        time = time

    morning = time[-2:] == 'AM' or time[-2:] == 'am'
    afternoon = time[-2:] == 'PM' or time[-2:] == 'pm'
    if morning and time[:2] == '12':
        return '00' + time[2:-2]
    elif morning:
        return time[:-2]
    elif afternoon and time[:2] == '12':
        return time[:-2]
    else:
        return (str(int(time[:2]) + 12) + time[2:8])[:tmp - 3]

