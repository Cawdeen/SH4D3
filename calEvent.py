
class Cal_Event:
    def __init__(self, type, startdatetime, enddatetime, startdatemonth, startdateday, enddatemonth, enddateday, duration, weekday, monthday, name, location, hosttype, host, description):
        self.type = type
        self.startdatetime = startdatetime
        self.enddatetime = enddatetime
        self.startdatemonth = startdatemonth
        self.startdateday = startdateday
        self.enddatemonth = enddatemonth
        self.enddateday = enddateday
        self.duration = duration
        self.weekday = weekday
        self.monthday = monthday
        self.name = name
        self.location = location
        self.hosttype = hosttype
        self.host = host
        self.description = description