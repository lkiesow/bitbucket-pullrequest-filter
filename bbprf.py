#!/bin/env python
# -*- coding: utf-8 -*-

# Set default encoding to UTF-8
import sys
reload(sys)
sys.setdefaultencoding('utf8')

import urllib2
import json
from pprint import pprint
from flask import Flask, render_template
app = Flask(__name__)


reviewers = None


def get_reviewer(req):
	global reviewers

	id = str(req['id'])
	url = 'https://bitbucket.org/api/2.0/repositories/opencast-community/matterhorn/pullrequests/%s/comments' % id

	u = urllib2.urlopen(urllib2.Request(url))
	try:
		data = json.loads(u.read())
	finally:
		u.close()

	reviewers[id] = {}

	for c in data.get('values') or []:
		if '//review//' in c['content']['raw']:
			r = c['user']['display_name']
			print 'Found reviewer for %s: %s' % (id, r)
			if reviewers[id].get('last_updated'):
				del reviewers[id]['last_updated']
			reviewers[id]['name'] = r
			return r

	reviewers[id]['last_updated'] = req.get('updated_on')
	print 'No reviewer found for %s' % id
	return ''


def load_reviewer():
	global reviewers
	try:
		with open('reviewers', 'r') as f:
			reviewers = json.loads(f.read())
	except:
		reviewers = {}


def save_reviewer():
	global reviewers
	try:
		with open('reviewers', 'w') as f:
			f.write(json.dumps(reviewers, sort_keys=True))
	except:
		pass


@app.route("/")
def home():
	global reviewers
	if not reviewers:
		load_reviewer()

	requests = []

	nexturl = 'https://bitbucket.org/api/2.0/repositories/opencast-community/matterhorn/pullrequests?pagelen=25'

	while nexturl:
		print 'Requesting data from %s' % nexturl
		u = urllib2.urlopen(urllib2.Request(nexturl))
		try:
			data = json.loads(u.read())
			requests += data.get('values') or []
			nexturl = data.get('next')
		finally:
			u.close()

	# Add reviewer
	for req in requests:
		reviewer = reviewers.get(str(req['id'])) or {}
		if reviewer.get('name'):
			req[u'reviewer'] = reviewer['name']

		elif req.get('updated_on') != reviewer.get('last_updated'):
			req[u'reviewer'] = get_reviewer(req)
	save_reviewer()

	# Sort by id
	requests.sort(key=lambda r: r.get('id'))

	return render_template('home.html', requests=requests)


if __name__ == "__main__":
	app.run(debug=True)
