#!/bin/env python
import urllib2
import json
from pprint import pprint
from flask import Flask, render_template
app = Flask(__name__)

@app.route("/")
def hello():

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

	pprint(requests[0])
	return render_template('home.html', requests=requests)
	#return '%s' % [ pr.get('title') + '\n' for pr in requests ]

if __name__ == "__main__":
	app.run(debug=True)
