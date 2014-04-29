
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


def getMeasurementFromDB(fromTs, toTs, device, collection="cellInfo", parameter="currentCellLocation"):
    #debug (todo:delete)
    print ("QUERING MONGO DB FOR MEASUREMENTS")
    print ("DATES  : ", fromTs, " --> ", toTs)
    print ("DEVICE : ", device)
    print ("Coll   : ", collection,".", parameter)
    #init
    results = []
    client = MongoClient()
    db = client.mPlaneClient
    #query to run
    query = {}
    query["properties.deviceID"] = device
    query["properties."+parameter] =  {"$exists": True}
    query["properties.date"] = {"$gte": fromTs, "$lte": toTs};
    #data projection (columns to return)
    projection =  {"properties.date": 1, "properties."+parameter: 1 } 
    #perform the query
    cursor = db[collection].find(query, projection).sort("properties.timeStamp" , 1 )
    print ("FOUND ", cursor.count(), " measurements")
    return cursor


   


def rssi_singleton_capability(devices):
    cap = mplane.model.Capability(label="connected-sector", when = "past ... now", verb = "query")
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
        print ("INIT SERIVICE")

#fixme: what happens when there are no data. 
    def run(self, spec, check_interrupt):
        # Got a request to retreive measurements. 
        # Get the request parameters
        period = spec.when().datetimes()
        fromTs = period[0]
        toTs = period[1]
        device = spec.get_parameter_value("source.device")
        
        # Get the data
        results = getMeasurementFromDB(fromTs, toTs, device)
        # Put the results into the specification reply msg
        res = mplane.model.Result(specification=spec)

        # put actual start and end time into result
        #fixme: null/empty results.
        numberOfMeasurements = results.count()
        startTime = results[0]["properties"]["date"]
        endTime = results[numberOfMeasurements - 1 ]["properties"]["date"]
        res.set_when(mplane.model.When(a = startTime, b = endTime))
        
        #put the data
        if res.has_result_column("time") and res.has_result_column("intermediate.link"):
            for i in range(0,  results.count()):
                result = results[i]
                date = result["properties"]["date"]
                value = result["properties"]["currentCellLocation"]
                res.set_result_value("time", date, i)
                res.set_result_value("intermediate.link", value, i)
        return res


def manually_test_capability():
    devices = getAvailableDevicesFromDB()
    svc = MobileProbeService(rssi_singleton_capability("353918050540026,358848043406974,358848047597893,358848043407105,352605059221267,351565050903399,354793051533265,355251056874894,866173010394946,351565054469835,866173010396297,358848047599451,866173010392577,358848047597935,352605059221028,352605059223594"))
    spec = mplane.model.Specification(capability=svc.capability())
    spec.set_parameter_value("source.device", "353918050540026")
    spec.set_when("2013-09-20 ... 2013-10-5")
    res = svc.run(spec, lambda: False)
    print(repr(res))
    print(mplane.model.unparse_yaml(res))


# For right now, start a Tornado-based ping server
if __name__ == "__main__":
    global args

    #initialize the registry
    mplane.model.initialize_registry()

    ###MANUAL CHECK SHOULD BE NORMALY DISABLED
    ## manually_test_capability()
    ## exit()
    ######
    #create the scheduler 
    scheduler = mplane.scheduler.Scheduler()
    #get devices 
    devices = getAvailableDevicesFromDB()
    #add all the capabilities
    scheduler.add_service(MobileProbeService(rssi_singleton_capability(devices)))
    #run the scheduler 
    mplane.httpsrv.runloop(scheduler)
