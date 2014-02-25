#
# mPlane Protocol Reference Implementation
# Time and Schedule Specification
#
# (c) 2013-2014 mPlane Consortium (http://www.ict-mplane.eu)
#               Author: Brian Trammell <brian@trammell.ch>
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.
#

"""
Temporal scoping -- when a measurement can be, should be, or was run -- is handled
by two sections of mPlane messages.

The "when" section defines when a capability, specification, or result is
valid. The "schedule" section defines, for specifications, when a specified
measurement should be repeated.

This file holds the classes implementing this during development and experimentation;
this code will be integrated into model.py.

"""

import re
from datetime import datetime, timedelta


TIME_PAST = "past"
TIME_NOW = "now"
TIME_FUTURE = "future"

RANGE_SEP = " ... "
DURATION_SEP = " + "
PERIOD_SEP = " / "
SET_SEP = ","

KEY_WHEN = "when"
KEY_MONTHS = "months"
KEY_DAYS = "days"
KEY_WEEKDAYS = "weekdays"
KEY_HOURS = "hours"
KEY_MINUTES = "minutes"
KEY_SECONDS = "seconds"

_iso8601_pat = '(\d+-\d+-\d+)(\s+\d+:\d+(:\d+)?)?(\.\d+)?'
_iso8601_re = re.compile(_iso8601_pat)
_iso8601_fmt = { 'us': '%Y-%m-%d %H:%M:%S.%f',
                  's': '%Y-%m-%d %H:%M:%S',
                  'm': '%Y-%m-%d %H:%M',
                  'd': '%Y-%m-%d'}

_dur_pat = '((\d+)d)?((\d+)h)?((\d+)m)?((\d+)s)?'
_dur_re = re.compile(_dur_pat)
_dur_seclabel = ( (86400, 'd'),
                  ( 3600, 'h'),
                  (   60, 'm'),
                  (    1, 's') )

_dow_label = ('mo', 'tu', 'we', 'th', 'fr', 'sa', 'so')
_dow_number = { k: v for (v, k) in enumerate(_dow_label) }

class PastTime:
    """
    Class representing the indeterminate past. 
    Do not instantiate; use the time_past instance of this class.

    """
    def __str__(self):
        return TIME_PAST

    def __repr__(self):
        return "mplane.tscope.time_past"

    def strftime(self, ign):
        return str(self)


time_past = PastTime()

class NowTime:
    """
    Class representing the present.
    Do not instantiate; use the time_now instance of this class.
    
    """
    def __str__(self):
        return TIME_NOW

    def __repr__(self):
        return "mplane.tscope.time_now"

    def strftime(self, ign):
        return str(self)

time_now = NowTime()

class FutureTime:
    """
    Class representing the indeterminate future.
    Do not instantiate; use the time_future instance of this class.

    """
    def __str__(self):
        return TIME_FUTURE

    def __repr__(self):
        return "mplane.tscope.time_future"

    def strftime(self, ign):
        return str(self)

time_future = FutureTime()

def parse_time(valstr):
    if valstr is None:
        return None
    elif valstr == TIME_PAST:
        return time_past
    elif valstr == TIME_FUTURE:
        return time_future
    elif valstr == TIME_NOW:
        return time_now
    else:
        m = _iso8601_re.match(valstr)
        if m:
            mstr = m.group(0)
            mg = m.groups()
            if mg[3]:
                # FIXME handle fractional seconds correctly
                dt = datetime.strptime(mstr, "%Y-%m-%d %H:%M:%S.%f")
            elif mg[2]:
                dt = datetime.strptime(mstr, "%Y-%m-%d %H:%M:%S")
            elif mg[1]:
                dt = datetime.strptime(mstr, "%Y-%m-%d %H:%M")
            else:
                dt = datetime.strptime(mstr, "%Y-%m-%d")
            return dt
        else:
            raise ValueError(repr(valstr)+" does not appear to be an mPlane timestamp")
    
def unparse_time(valts, precision="us"):    
    return valts.strftime(_iso8601_fmt[precision])

def parse_dur(valstr):
    if valstr is None:
        return None
    else:
        m = _dur_re.match(valstr)
        if m:
            mg = m.groups()
            valsec = 0
            for i in range(4):
                if mg[2*i + 1]:
                    valsec += _dur_seclabel[i][0] * int(mg[2*i + 1])
            return timedelta(seconds=valsec)
        else:
            raise ValueError(repr(valstr)+" does not appear to be an mPlane duration")

def unparse_dur(valtd):
    valsec = int(valtd.total_seconds())
    valstr = ""
    for i in range(4):
        if valsec > _dur_seclabel[i][0]:
            valunit = int(valsec / _dur_seclabel[i][0])
            valstr += str(valunit) + _dur_seclabel[i][1]
            valsec -= valunit * _dur_seclabel[i][0]
    if len(valstr) == 0:
        valstr = "0s"
    return valstr

def parse_numset(valstr):
    return set(map(int, valstr.split(SET_SEP)))

def unparse_numset(valset):
    return SET_SEP.join(map(str, sorted(list(valset))))

def parse_wdayset(valstr):
    return set(map(lambda x:_dow_number[x], valstr.split(SET_SEP)))

def unparse_wdayset(valset):
    return SET_SEP.join(map(lambda x: _dow_label[x], sorted(list(valset))))


class When(object):
    """
    Defines the temporal scopes for capabilities, results, or 
    single measurement specifications.

    """
    def __init__(self, valstr=None, a=None, b=None, d=None, p=None):
        super(When, self).__init__()
        self._a = a
        self._b = b
        self._d = d
        self._p = p

        if valstr is not None:
            self._parse(valstr)

    def _parse(self, valstr):
        # First separate the period from the value and parse it
        valsplit = valstr.split(PERIOD_SEP)
        if len(valsplit) > 1:
            (valstr, perstr) = valsplit
            self._p = parse_dur(perstr)
        else:
            self._p = None

        # then try to split duration or range
        valsplit = valstr.split(DURATION_SEP)
        if len(valsplit) > 1:
            (valstr, durstr) = valsplit
            self._d = parse_dur(durstr)
            valsplit = [valstr]
        else:
            self._d = None
            valsplit = valstr.split(RANGE_SEP)
        
        self._a = parse_time(valsplit[0])
        if len(valsplit) > 1:
            self._b = parse_time(valsplit[1])
        else:
            self._b = None

    def __str__(self):
        valstr = unparse_time(self._a)

        if self._b is not None:
            valstr = "".join((valstr, RANGE_SEP, unparse_time(self._b)))
        elif self._d is not None:
            valstr = "".join((valstr, DURATION_SEP, unparse_dur(self._d)))

        if (self._p) is not None:
            valstr = "".join((valstr, PERIOD_SEP, unparse_dur(self._p)))
        return valstr

    def __repr__(self):
        return "<When: "+str(self)+">"

    def is_immediate(self):
        return self._a is time_now

    def is_singleton(self):
        """
        Return True if this temporal scope refers to a
        singleton measurement. Used in scheduling an enclosing
        Specification; has no meaning for Capabilities 
        or Results.

        """
        return self._a is not None and self._b is None and self._d is None

    def _datetimes(self, tzero=None):
        if tzero is None:
            tzero = datetime.utcnow()

        if self._a is time_now:
            start = tzero
        else:
            start = self._a

        if self._b is time_future:
            end = None
        elif self._b is None:
            if self._d is not None:
                end = start + self._d
            else:
                end = start
        else:
            end = self._b

        return (start, end)

    def duration(self, tzero=None):
        if self._d is not None:
            return self._d
        elif self._b is None:
            return timedelta()
        elif self._b is time_future:
            return None
        else:
            return self._b - self._datetimes(tzero)

    def period(self):
        return self._p

    def timer_delays(self, tzero=None):
        """
        Returns a tuple with delays for timers to signal the start and end of
        a temporal scope, given a specified time zero, which defaults to the
        current system time. 

        The start delay is defined to be zero if the scheduled start time has
        already passed or the temporal scope is immediate (i.e., starts now).
        The start delay is None if the temporal scope has expired (that is,
        the current time is after the calculated end time)

        The end delay is defined to be None if the temporal scope has already
        expired, or if the temporal scope has no scheduled end (is infinite or
        a singleton). End delays are calculated to give priority to duration 
        when a temporal scope is expressed in terms of duration, and to 
        prioritize end time otherwise.
 
        Used in scheduling an enclosing Specification for execution. 
        Has no meaning for Capabilities or Results.

        """
        # default to current time
        if tzero is None:
            tzero = datetime.utcnow()
        
        # get datetimes
        (start, end) = self._datetimes(tzero=tzero)

        # determine start delay, account for late start
        sd = (start - tzero).total_seconds()
        if sd < 0:
            sd = 0

        # determine end delay
        if self._b is not None and self._b is not time_future:
            ed = (end - tzero).total_seconds()
        elif self._d is not None:
            ed = sd + self._d.total_seconds();
        else:
            ed = None

        # detect expired temporal scope
        if ed is not None and ed < 0:
            sd = None
            ed = None

        return (sd, ed)

    def sort_scope(self, t, tzero=None):
        """
        Return < 0 if time t falls before this scope,
        0 if time t falls within the scope, 
        or > 0 if time t falls after this scope. 

        """
        (start, end) = self._datetimes(tzero=tzero)

        if start and t < start:
            return (t - start).total_seconds()
        elif end and t > end:
            return (t - end).total_seconds()
        else:
            return 0

    def in_scope(self, t, tzero=None):
        """
        Return True if time t falls within this scope.

        """
        return self.sort_scope(t, tzero) == 0

class Schedule(object):
    """
    Defines a schedule for repeated operations based on crontab-like
    sets of months, days, days of weeks, hours, minutes, and seconds.
    Used to specify repetitions of single measurements in a Specification.
    Designed to be broadly compatible with LMAP calendar-based scheduling.
    """
    def __init__(self, dictval=None, when=None):
        super(Schedule, self).__init__()
        self._when = when
        self._months = set()
        self._days = set()
        self._weekdays = set()
        self._hours = set()
        self._minutes = set()
        self._seconds = set()

        if dictval is not None:
            self._from_dict(dictval)

    def __repr__(self):
        rs = "<Schedule "
        if self._when is not None:
            rs += repr(self._when) + " "
        rs += "cron "
        rs += "/".join(map(str, [len(self._months),
                                 len(self._days),
                                 len(self._weekdays),
                                 len(self._hours),
                                 len(self._minutes),
                                 len(self._seconds)]))
        rs += ">"
        return rs

    def to_dict(self):
        d = {}
        if self._when:
            d[KEY_WHEN] = str(self._when)
        if len(self._months):
            d[KEY_MONTHS] = unparse_numset(self._months)
        if len(self._days):
            d[KEY_DAYS] = unparse_numset(self._days)
        if len(self._weekdays):
            d[KEY_WEEKDAYS] = unparse_wdayset(self._weekdays)
        if len(self._hours):
            d[KEY_HOURS] = unparse_numset(self._hours)
        if len(self._minutes):
            d[KEY_MINUTES] = unparse_numset(self._minutes)
        if len(self._seconds):
            d[KEY_SECONDS] = unparse_numset(self._seconds)
        return d

    def _from_dict(self, d):
        if KEY_WHEN in d:
            self._when = When(valstr=d[KEY_WHEN])
        if KEY_MONTHS in d:
            self._months = parse_numset(d[KEY_MONTHS])
        if KEY_DAYS in d:
            self._days = parse_numset(d[KEY_DAYS])
        if KEY_WEEKDAYS in d:
            self._weekdays = parse_wdayset(d[KEY_WEEKDAYS])
        if KEY_HOURS in d:
            self._hours = parse_numset(d[KEY_HOURS])
        if KEY_MINUTES in d:
            self._minutes = parse_numset(d[KEY_MINUTES])
        if KEY_SECONDS in d:
            self._seconds = parse_numset(d[KEY_SECONDS])

    def _datetime_iterator(self, t=None):
        """
        Returns an iterator over datetimes generated by the schedule 
        and period. 

        """
        # default to now, zero microseconds, initialize minus one second
        if t is None:
            t = datetime.utcnow().replace(microsecond=0)

        # get base period (default 1s) and
        period = None
        if self._when is not None:
            period = self._when.period()
        if period is None:
            period = timedelta(seconds=1)

        # fast forward if necessary
        lag = self._when.sort_scope(t)
        if lag < 0:
            t += timedelta(seconds=-lag)

        # loop through time by period and check for match
        t -= period
        while True:
            t += period
            if self._when is not None and not self._when.in_scope(t):
                break
            if len(self._seconds) and (t.second not in self._seconds):
                continue
            if len(self._minutes) and (t.minute not in self._minutes):
                continue
            if len(self._hours) and (t.hour not in self._hours):
                continue
            if len(self._days) and (t.day not in self._days):
                continue
            if len(self._weekdays) and (t.weekday() not in self._weekdays):
                continue
            if len(self._months) and (t.month not in self._months):
                continue
            yield t