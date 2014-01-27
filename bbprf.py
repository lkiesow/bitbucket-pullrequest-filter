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

@app.route("/")
def home():

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
		req[u'reviewer'] = reviewers.get(req['id'])

	return render_template('home.html', requests=requests)
	#return '%s' % [ pr.get('title') + '\n' for pr in requests ]

if __name__ == "__main__":
	app.run(debug=True)
