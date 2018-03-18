import argparse
from datetime import *
from icalendar import Calendar
from dateutil.rrule import *
from dateutil.parser import parse
from pprint import pprint


BYOPTIONS = ('BYSECOND', 'BYMINUTE', 'BYHOUR', 'BYWEEKNO', 'BYMONTHDAY',
             'BYYEARDAY', 'BYMONTH', 'BYSETPOS', 'BYDAY')


FUNCMAP = {'MO': MO, 'TU': TU, 'WE': WE, 'TH': TH, 'FR': FR, 'SA': SA,
           'SU': SU, 'MONTHLY': MONTHLY, 'WEEKLY': WEEKLY, 'YEARLY': YEARLY,
           'DAILY': DAILY}


def get_dict_value(d, v):
    val = d.get(v)
    if val:
        return val[0]
    else:
        if v == 'interval':
            return 1
        else:
            return None


def get_by_periode(rule):
    for byopt in BYOPTIONS:
        if byopt in rule:
            # dateutil uses non ical standard byweekday
            if byopt == 'BYDAY':
                return 'byweekday', rule[byopt]
            else:
                return byopt.lower(), rule[byopt]


def parse_by_periode(periode):
    parsed = []
    for i in periode:
        if isinstance(i, int):
            parsed.append(i)
        elif len(i) == 2:
            parsed.append(FUNCMAP[i])
        elif len(i) in (3, 4):
            parsed.append(FUNCMAP[i[-2:]](int(i[:-2])))

    return parsed


if __name__ == '__main__':
    BEGIN_DATE = None
    END_DATE = None
    cal = None

    parser = argparse.ArgumentParser(description='Process icalendar file and output csv')
    parser.add_argument('--startdate', dest='startdate', help='The date to start creating rows in csv file')
    parser.add_argument('--enddate', dest='enddate', help='The date to end creating rows in csv file')
    parser.add_argument('--icsfile', dest='icsfile', help='The ics file to parse')
    args = parser.parse_args()

    try:
        with open(args.icsfile, 'r', encoding='utf-8') as f:
            cal = Calendar.from_ical(f.read())
    except FileNotFoundError:
        print('Could not find ics file: %s' % args.icsfile)
        exit(1)

    rows = []

    try:
        BEGIN_DATE = parse(args.startdate)
    except ValueError:
        print('Invalid startdate: %s' % args.startdate)
        exit(1)

    try:
        END_DATE = parse(args.startdate)
    except ValueError:
        print('Invalid end date: %s' % args.enddate)
        exit(1)

    for event in cal.walk(name='VEVENT'):
        rec_rule = event.get('rrule')
        dtstart = event.get('DTSTART')
        dtend = event.get('DTEND')
        event_summary = str(event['summary'])

        starttime = dtstart.dt.strftime('%H:%M')
        endtime = dtend.dt.strftime('%H:%M')

        tzinfo = getattr(dtstart.dt, 'tzinfo', None)
        # print('********')
        if rec_rule:
            dtruleargs = {'dtstart': dtstart.dt, 'count': get_dict_value(rec_rule, 'count'),
                          'interval': get_dict_value(rec_rule, 'interval'),
                          'freq': FUNCMAP[get_dict_value(rec_rule, 'freq')], 'wkst': get_dict_value(rec_rule, 'wkst')}

            by_option, byperiode = get_by_periode(rec_rule)
            dtruleargs[by_option] = parse_by_periode(byperiode)

            # Avoid infinite sequence
            until = get_dict_value(rec_rule, 'until')
            count = get_dict_value(rec_rule, 'count')
            if until is None and count is None:
                dtruleargs['until'] = END_DATE.replace(tzinfo=tzinfo)
                dtruleargs['count'] = count
            else:
                dtruleargs['until'] = until
                dtruleargs['count'] = count

            dates = []
            for dt in rrule(**dtruleargs):
                if dt >= BEGIN_DATE.replace(tzinfo=tzinfo):
                    rows.append((event_summary, dt.strftime('%d-%m-%Y'), " - ".join((starttime, endtime))))
                else:
                    print(event_summary, dt.strftime('%d-%m-%Y'), starttime,
                          'out of range')
        else:
            startdate = dtstart.dt.strftime('%d-%m-%Y')
            enddate = dtend.dt.strftime('%d-%m-%Y')
            if startdate == enddate:
                rows.append((event_summary, startdate, " - ".join((starttime, endtime))))
            elif isinstance(dtstart.dt, date):
                rows.append((event_summary, startdate, enddate))
            else:
                rows.append((event_summary, startdate, starttime))
                rows.append((event_summary, enddate, endtime))

    pprint(rows)
