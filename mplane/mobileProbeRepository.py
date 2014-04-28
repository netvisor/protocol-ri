
# mPlane Protocol Reference Implementation
# TID mplane mobile probe access
#
# (c) 2013-2014 mPlane Consortium (http://www.ict-mplane.eu)
#               Author: Ilias Leontiadis <ilias@tid.es>
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
Implements functionality to read data from TIDs mobile probe repository

"""

import re
import ipaddress
import threading
import subprocess
import collections
from datetime import datetime, timedelta
from ipaddress import ip_address
import mplane.model
import mplane.scheduler
import mplane.httpsrv
import tornado.web
import tornado.ioloop
import argparse
from pymongo import MongoClient


def getAvailableDevicesFromDB():
    client = MongoClient()
    db = client.mPlaneClient
    devices = db.cellInfo.distinct("properties.deviceID")
    devices.remove(None)
    parsed = ",".join(devices)
    print (parsed)
    return parsed


def getMeasurementFromDB(from, to, device, collection, parameter):
    client = MongoClient()
    db = client.mPlaneClient
    devices = db.cellInfo.distinct("properties.deviceID")
    devices.remove(None)
    parsed = ",".join(devices)
    print (parsed)
    return parsed


def rssi_singleton_capability(devices):
    cap = mplane.model.Capability(label="connected-sector", when = "past ... now")
    cap.add_parameter("source.device", devices)
    cap.add_result_column("time")
    cap.add_result_column("intermediate.link")
    return cap

class MobileProbeService(mplane.scheduler.Service):
    def __init__(self, cap):
        # verify the capability is acceptable
        if not ( cap.has_parameter("source.device"))  and  (cap.has_result_column("time") and cap.has_result_column("intermediate.link")):
            raise ValueError("capability not acceptable")
        super(MobileProbeService, self).__init__(cap)

    def run(self, spec, check_interrupt):
        # unpack parameters
        period = spec.when().period().total_seconds()
        duration = spec.when().duration().total_seconds()

        '''
        if duration is not None and duration > 0:
            count = int(duration / period)
        else:
            count = None

        if spec.has_parameter("destination.ip4"):
            sipaddr = spec.get_parameter_value("source.ip4")
            dipaddr = spec.get_parameter_value("destination.ip4")
            ping_process = _ping4_process(sipaddr, dipaddr, period, count)
        elif spec.has_parameter("destination.ip6"):
            sipaddr = spec.get_parameter_value("source.ip6")
            dipaddr = spec.get_parameter_value("destination.ip6")
            ping_process = _ping6_process(sipaddr, dipaddr, period, count)
        else:
            raise ValueError("Missing destination")

        # read output from ping
        pings = []
        for line in ping_process.stdout:
            if check_interrupt():
                break
            oneping = _parse_ping_line(line.decode("utf-8"))
            if oneping is not None:
                print("ping "+repr(oneping))
                pings.append(oneping)
 

        # shut down and reap
        try:
            ping_process.kill()
        except OSError:
            pass
        ping_process.wait()

        '''
        # derive a result from the specification
        res = mplane.model.Result(specification=spec)

        # put actual start and end time into result
        #res.set_when(mplane.model.When(a = pings_start_time(pings), b = pings_end_time(pings)))

        '''
        # are we returning aggregates or raw numbers?
        if res.has_result_column("delay.twoway.icmp.us"):
            # raw numbers
            for i, oneping in enumerate(pings):
                res.set_result_value("delay.twoway.icmp.us", oneping.usec, i)
            if res.has_result_column("time"):
                for i, oneping in enumerate(pings):
                    res.set_result_value("time", oneping.time, i)
        else:
            # aggregates. single row.
            if res.has_result_column("delay.twoway.icmp.us.min"):
                res.set_result_value("delay.twoway.icmp.us.min", pings_min_delay(pings))
            if res.has_result_column("delay.twoway.icmp.us.mean"):
                res.set_result_value("delay.twoway.icmp.us.mean", pings_mean_delay(pings))
            if res.has_result_column("delay.twoway.icmp.us.median"):
                res.set_result_value("delay.twoway.icmp.us.median", pings_median_delay(pings))
            if res.has_result_column("delay.twoway.icmp.us.max"):
                res.set_result_value("delay.twoway.icmp.us.max", pings_max_delay(pings))
            if res.has_result_column("delay.twoway.icmp.us.count"):
                res.set_result_value("delay.twoway.icmp.us.count", len(pings))
        '''

        return res



# For right now, start a Tornado-based ping server
if __name__ == "__main__":
    global args

    #initialize the registry
    mplane.model.initialize_registry()
    #create the scheduler 
    scheduler = mplane.scheduler.Scheduler()
    #get devices 
    devices = getAvailableDevicesFromDB()
    #add all the capabilities
    scheduler.add_service(MobileProbeService(rssi_singleton_capability(devices)))
    #run the scheduler 
    mplane.httpsrv.runloop(scheduler)
