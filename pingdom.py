#!/usr/bin/env python

# Copyright 2009 Dan Udey
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#   http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import time
import SOAPpy

PINGDOM_WSDL = 'https://ws.pingdom.com/soap/PingdomAPI.wsdl'

STATUS_CODES = {
0: "OK",
1: "Reserved",
2: "Reserved",
3: "Invalid Argument",
4: "Internal Error",
5: "Wrong Identification",
6: "Wrong Authorization",
7: "Wrong Authentication"
}

CHECK_RESULTS = {
'CHECK_UP': 'Up',
'CHECK_DOWN': 'Down',
'CHECK_UNKNOWN': 'Unknown'
}

REPORT_RESOLUTIONS = {
'DAILY': 'Daily',
'WEEKLY': 'Weekly',
'MONTHLY': 'Montly'
}

class PingdomException(Exception):
	def __init__(self,status):
		self.status = status
		self._message = "Error %s: %s" % (self.status, STATUS_CODES[self.status])

	@property
	def message(self):
		return self._message
	
	def __str__(self):
		return self._message

class Pingdom(object):
	def __init__(self, username, password, apikey):
		self._credentials = {'username':username, 'password':password}
		self._apikey = apikey
		self._server = SOAPpy.WSDL.Proxy(PINGDOM_WSDL)
		self._sessionid = None
		self._checks = None
		self._locations = None
		
		self._login()

	# Properties
	@property
	def loggedin(self):
		return self._sessionid is not None

	@property
	def username(self):
		return self.credentials['username']

	@property
	def apikey(self):
		return self._apikey

	# Internal methods

	def _callWithParams(self, *args):
		method = self._server.__getattr__(args[0])
		if args[0] == 'Auth_login':
			param = self._credentials
		else:
			param = self._sessionid
		return method(self.apikey, param, *args[1:])

	def _login(self):
		"""Logs into the Pingdom server"""
		status,sessionid = self._callWithParams('Auth_login')
#		status,sessionid = self._server.Auth_login(self.apikey, self._credentials)
		if status == 0:
			self._sessionid = sessionid
			return True
		else:
			raise PingdomException(status)
	
	def _logout(self):
		if self._sessionid == None:
			return True
		logoutResponse = self._callWithParams('Auth_logout')
		status = logoutResponse['status']
		if status == 0:
			self._sessionid = None		# Our session ID is no longer valid
			return True
		else:
			raise PingdomException(status)

	def _check_getList(self):
		status, checklist = self._callWithParams('Check_getList')
		if status == 0:
			self._checks = checklist['item']
			return True
		else:
			raise PingdomException(status)

	def _location_getList(self):
		status, locationlist = self._callWithParams('Location_getList')
		if status == 0:
			self._locations = locationlist['item']
			return True
		else:
			raise PingdomException(status)

	def _report_getCurrentStates(self):
		status, states = self._callWithParams('Report_getCurrentStates')
		if status == 0:
			states = states['item']
			states = map(lambda x: x._asdict(), states)
			return states
		else:
			raise PingdomException(status)

	def _report_getDowntimes(self,check,starttime,endtime,resolution):
		params = {
			'checkName':'Communicate',
			'from': self._convertTime(starttime),
			'to': self._convertTime(endtime),
			'resolution': 'DAILY'
		}
		status, states = self._callWithParams('Report_getDowntimes', params)
		if status == 0:
			states = states['item']
			states = map(lambda x: x._asdict(), states)
			return states
		else:
			raise PingdomException(status)

	def _convertTime(self, time):
		return SOAPpy.dateTimeType(time[:6])

	# Common properties and methods
	
	@property
	def checks(self):
		if self._checks is None:
			self._check_getList()
		return self._checks
	
	@property
	def locations(self):
		if self._locations is None:
			self._location_getList()
		return self._locations

	@property
	def states(self):
		return self._report_getCurrentStates()
	
	def downtimes(self):
		return self._report_getDowntimes()
	
	def downtimesFor(self,check,starttime,endtime,resolution='DAILY'):
		if starttime == endtime:
			raise ValueError("Start time and end time must be different")
		elif resolution not in REPORT_RESOLUTIONS:
			raise ValueError("Invalid report resolution")
		elif not check in self.checks:
			raise PingdomException("No such check available")
		elif None in (check,starttime,endtime,resolution):
			raise TypeError("Invalid type: NoneType")
		else:
			return self._report_getDowntimes(check,starttime,endtime,resolution)
			

	def echo(self,inString):
		status,result = self._server.Test_echo(inString)
		if status == 0:
			return result
		else:
			raise PingdomException(status)

	# Special methods

	def __del__(self):
		self._logout()

	def __repr__(self):
		return "<Pingdom Instance (user:%s, sessionid: %s)>" % (self._credentials['username'],self.sessionid)

if __name__ == '__main__':
	pass