import json

from pytz import timezone
from calEvent import Cal_Event
from datetime import datetime, date, time, timedelta

class CalendarEvents:
    def __init__(self):
        f = open('rp/Calendar.json')
        self.events_json = json.load(f) # list with json objects (dicts)
        self.cal_events = []
        for i in self.events_json['events']:
            type = i['type'] #str
            startdate = i['annualstartdate']
            enddate = i['annualenddate']
            startdatetime = datetime.strptime(startdate, '%Y-%m-%dT%H:%M:%S.%fZ')
            enddatetime = datetime.strptime(enddate, '%Y-%m-%dT%H:%M:%S.%fZ')
            startdatetime = startdatetime.astimezone(timezone('US/Eastern'))
            enddatetime = enddatetime.astimezone(timezone('US/Eastern'))
            startdatemonth = datetime.now()
            startdateday = datetime.now()
            enddatemonth = datetime.now()
            enddateday = datetime.now()
            if type == "annual":
                startdatemonth = startdatetime.month
                startdateday = startdatetime.day
                enddatemonth = enddatetime.month
                enddateday = enddatetime.day
            duration = i['duration']
            weekday = i['weekday']
            monthday = i['monthday']
            name = i['name']
            location = i['location']
            hosttype = i['hosttype']
            host = i['host']
            description = i['description']
            #create the event
            event = Cal_Event(type,startdatetime,enddatetime,startdatemonth,startdateday,enddatemonth,enddateday,duration,weekday,monthday,name,location,hosttype,host,description)
            #store the event in the list
            self.cal_events.append(event)
        f.close()
           
    def get_events(self):
        return self.cal_events
    
    #returns a list of active events
    def get_active_events(self):
        today = datetime.now()
        today = today.astimezone(timezone('US/Eastern'))
        events = []
        for i in self.cal_events:
            if i.type == 'annual' and i.duration == 'month':
                month = today.month
                day = today.day
                if i.enddatetime.month == i.startdatetime.month: #doesnt transition a month
                    if month >= i.startdatetime.month and month <= i.enddatetime.month: #just check the month. Are we in the same month as the annual event
                        print(i.name)
                        print(day)
                        print(i.startdateday)
                        print(i.enddateday)
                        if day >= i.startdateday and day <= i.enddateday:
                            events.append(i)
                    elif i.enddatetime.month > i.startdatetime.month: #transitions a month
                        if month == i.startdatetime.month and month < i.enddatetime.month: #we're in the first month
                            if day >= i.startdateday:
                                events.append(i)
                        elif month > i.startdatetime.month and month == i.enddatetime.month: #we're in the next month
                            if day <= i.enddateday:
                                events.append(i)
        print(len(events))
        return events
    
    #checks the length of event and tells us if we're at a signifigant time for reminders (such as half way through a month long event)
    #milestones right now are at quarterly increments of the month
    def event_milestone(self):
        active_events = self.get_active_events()
        today = datetime.now()
        today = today.astimezone(timezone('US/Eastern'))
        notice_string = ''
        for i in active_events:
            name = ''
            description = ''
            host = ''
            duration = ''
            reminderFlag = False
            if i.type == 'annual' and i.duration == 'month':
                event_quarter = (i.startdatetime + timedelta(days=7)).day
                event_half = (i.startdatetime + timedelta(days=15)).day
                event_threeQuarter = (i.startdatetime + timedelta(days=20)).day
                event_almostEnd = (i.startdatetime + timedelta(days=28)).day
                month = today.month
                day = today.day
                #only include the duration if its month long event
                if month == i.startdatetime.month: #Are we in the same month as the annual event
                    if i.startdatetime.day <= 1 and i.startdatetime.day < today.day: #starts beginning of month
                        if day == event_quarter: #quarter
                            notice_string = 'Remind everyone to take advantage of this event: '
                            reminderFlag = True
                        elif day == event_half: #halfway
                            notice_string = 'Remind everyone to take advantage of this event since we are about half way through: '
                            reminderFlag = True
                        elif day == event_threeQuarter: #3/4 through
                            notice_string = 'Remind everyone to take advantage of this before its over: '
                            reminderFlag = True
                        elif day == event_almostEnd: #amost over
                            notice_string = 'Remind everyone to take advantage of this event since its going to end very soon: '
                            reminderFlag = True
                    # for events that start later in the month
                    elif i.startdatetime.day > 1 and i.startdatetime.day < today: #same month as startmonth, and we're after start day
                        if day == event_quarter: #quarter
                            notice_string = 'Remind everyone to take advantage of this event: '
                            reminderFlag = True
                        elif day == event_half: #halfway
                            notice_string = 'Remind everyone to take advantage of this event since we are about half way through: '
                            reminderFlag = True
                        elif day == event_threeQuarter: #3/4 through
                            notice_string = 'Remind everyone to take advantage of this before its over: '
                            reminderFlag = True
                        elif day == event_almostEnd: #amost over
                            notice_string = 'Remind everyone to take advantage of this event since its going to end very soon: '
                            reminderFlag = True
                elif month == i.enddatetime.month: #Are we in the same month as the end annual event (for later month start times)
                    if i.enddatetime.day > today.day: #havent ended yet
                        if day == event_quarter: #quarter
                            notice_string = 'Remind everyone to take advantage of this event: '
                            reminderFlag = True
                        elif day == event_half: #halfway
                            notice_string = 'Remind everyone to take advantage of this event since we are about half way through: '
                            reminderFlag = True
                        elif day == event_threeQuarter: #3/4 through
                            notice_string = 'Remind everyone to take advantage of this before its over: '
                            reminderFlag = True
                        elif day == event_almostEnd: #amost over
                            notice_string = 'Remind everyone to take advantage of this event since its going to end very soon: '
                            reminderFlag = True
                #only include duration info if a monthlong event
                if reminderFlag == True:
                    duration = 'Duration: '+i.duration + '\n'
                
            elif i.type == 'weekly':
                notice_string = 'Include a short 1 sentence reminder about this weekly event: '
                reminderFlag = True

            elif i.type == 'monthly':
                notice_string = 'Include a short 1-2 sentence reminder about this monthly event: '
                reminderFlag = True
            
            if reminderFlag == True:
                name = 'Name: '+i.name + '\n'
                description = 'Description: '+i.description + '\n'
                host = 'Calendar event host: '+i.host + '\n\n'
            
            act_events_str = name + description + duration + host #create the event string
            notice_string = notice_string + act_events_str #add to the total string
            print(notice_string)
        return notice_string

                    
        
    

    