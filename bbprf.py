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


last_updated = {}


def get_reviewer(id):
	url = 'https://bitbucket.org/api/2.0/repositories/opencast-community/matterhorn/pullrequests/%s/comments' % id

	u = urllib2.urlopen(urllib2.Request(url))
	try:
		data = json.loads(u.read())
	finally:
		u.close()

	for c in data.get('values') or []:
		if '//review//' in c['content']['raw']:
			reviewer = c['user']['display_name']
			print 'Found reviewer for %s: %s' % (id, reviewer)
			with open('reviewers', 'a') as f:
				f.write('%s=%s\n' % (id, reviewer))
			return reviewer

	print 'No reviewer found for %s', id
	return None


@app.route("/")
def home():
	global last_updated

	reviewers = {}
	try:
		with open('reviewers', 'r') as f:
			for line in f.read().split('\n'):
				try:
					issue, reviewer = line.split('=', 1)
					reviewers[int(issue)] = reviewer
				except:
					pass
	except IOError:
		pass

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
		if reviewers.get(req['id']):
			req[u'reviewer'] = reviewers.get(req['id'])
		else:
			if req.get('updated_on') != last_updated.get(req['id']):
				req[u'reviewer'] = get_reviewer(req['id']) or ''
			if not req.get(u'reviewer'):
				req[u'reviewer'] = ''
				last_updated[req['id']] = req.get('updated_on')

	# Sort by id
	requests.sort(key=lambda r: r.get('id'))

	return render_template('home.html', requests=requests)

if __name__ == "__main__":
	app.run(debug=True)
