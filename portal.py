#!/bin/env python
# -*- coding: utf-8 -*-

# Set default encoding to UTF-8
import sys
reload(sys)
sys.setdefaultencoding('utf8')

import json
from flask import Flask, render_template, request
app = Flask(__name__)


@app.route("/")
@app.route("/<key>/<path:value>")
def home(key=None, value=None):
	requests = []
	try:
		with open('pullrequests.json', 'r') as f:
			requests = json.loads(f.read())
	except:
		return {}

	# Sort by id
	requests.sort(key=lambda r: r.get('id'))

	# Additional, get data for release tickets
	releasetickets = []
	try:
		with open('releasetickets.json', 'r') as f:
			releasetickets = json.loads(f.read())
	except:
		return {}



	return render_template('home.html', requests=requests,
			releasetickets=releasetickets, key=key, value=value)


if __name__ == "__main__":
	app.run(debug=True)
