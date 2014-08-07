#!/bin/env python
# -*- coding: utf-8 -*-

# Set default encoding to UTF-8
import sys
reload(sys)
sys.setdefaultencoding('utf8')

import config

import json
from flask import Flask, render_template, request, Response
app = Flask(__name__)

import redis
from data import PullRequest, ReleaseTicket
r = redis.StrictRedis(host='localhost', db=0)


@app.route("/")
@app.route("/<key>/<path:value>")
def home(key=None, value=None):

	requests = [ PullRequest(r.get(k)) for k in r.keys('pr_*') ]
	requests.sort(key=lambda pr: pr.id)

	# Additional, get data for release tickets
	releasetickets = [ ReleaseTicket(r.get(k)) for k in r.keys('ticket_*') ]

	return render_template('home.html', requests=requests,
			releasetickets=releasetickets, key=key, value=value)


@app.route('/stats')
def stats():
	auth = (request.authorization.username, request.authorization.password) \
			if request.authorization else None
	if auth != ('admin', 'opencast'):
		return Response('', 401,
				{'WWW-Authenticate': 'Basic realm="Login Required"'})
	stats = {}
	user = {}
	for k in r.keys('*pr_*'):
		pr = PullRequest(r.get(k))
		if not pr.reviewer_user:
			continue
		if pr.reviewer_name:
			user[pr.reviewer_user] = pr.reviewer_name
		stats[pr.reviewer_user] = stats.get(pr.reviewer_user, []) + [pr.id]

	stats = [ (k, user.get(k,k), len(v), [int(x) for x in v]) for k,v in stats.iteritems() ]

	# Sort by number of reviews
	stats.sort(key=lambda r: r[2])

	return render_template('stats.html', stats=stats)


if __name__ == "__main__":
	app.run(debug=True)
