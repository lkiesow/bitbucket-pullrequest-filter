#!/bin/env python
# -*- coding: utf-8 -*-

# Set default encoding to UTF-8
import sys
reload(sys)
sys.setdefaultencoding('utf8')

import json
import time, datetime, pytz
from dateutil.parser import parse


class Base:

	def __init__(self, *args, **kwargs):
		if args and args[0]:
			kwargs = json.loads(args[0])
		for k,v in (kwargs or {}).iteritems():
			getattr(self, k)
			setattr(self, k, v)


	def data(self):
		data = {}
		for a in dir(self):
			if not a.startswith('_') and not callable(getattr(self, a)):
				data[a] = getattr(self, a)
		return data


	def json(self):
		return json.dumps(self.data())



class PullRequest(Base):

	author_name          = None
	author_user          = None
	created              = None
	created_date         = None
	destination          = None
	id                   = None
	on_hold              = None
	active               = None
	review_start         = None
	reviewer_name        = None
	reviewer_user        = None
	source_branch        = None
	source_repo          = None
	title                = None
	last_updated         = None
	approved_by_reviewer = None
	approved_by          = None
	url                  = None
	state                = None


	def review_duration(self, default=None):
		if self.review_start:
			return (datetime.datetime.now(pytz.utc) - parse(self.review_start)).days
		return default



class ReleaseTicket(Base):

	url          = None
	version      = None
	assignee     = None
