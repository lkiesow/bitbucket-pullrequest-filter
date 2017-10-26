#!/bin/env python
# -*- coding: utf-8 -*-

# Set default encoding to UTF-8
import sys
reload(sys)
sys.setdefaultencoding('utf8')

import config

import json
from dateutil.parser import parse
from datetime import date
from dateutil.relativedelta import relativedelta
from flask import Flask, render_template, request, Response
app = Flask(__name__)

import redis
from data import PullRequest, ReleaseTicket
try:
	r = redis.StrictRedis(host='localhost', db=0)
except AttributeError:
	r = redis.Redis(host='localhost', db=0)


def filters(filterval):
	filters = {}
	filterval = filterval.replace('//', '~~~~~~~~~~~~~~~~~~~~~~~').split('/')
	if len(filterval) % 2 == 0:
		filterval = [ c.replace('~~~~~~~~~~~~~~~~~~~~~~~', '/') for c in filterval ]
		while filterval:
			filters[filterval[0]] = filterval[1]
			filterval = filterval[2:]
	return filters


@app.route("/")
@app.route("/<path:filterval>")
def home(filterval=''):

	requests = [ PullRequest(r.get(k)) for k in r.keys('pr_*') ]
	requests.sort(key=lambda pr: pr.id)

	# Additional, get data for release tickets
	releasetickets = [ ReleaseTicket(r.get(k)) for k in r.keys('ticket_*') ]
	releasetickets.sort(key=lambda rt: rt.version, reverse=True)

	return render_template('home.html', requests=requests,
			releasetickets=releasetickets, filters=filters(filterval))


@app.route("/pr.json")
def api_pr():
	requests = [ PullRequest(r.get(k)).data() for k in r.keys('pr_*') ]
	requests.sort(key=lambda pr: pr['id'])
	return json.dumps(requests)


@app.route("/release.json")
def api_tickets():
	releasetickets = [ ReleaseTicket(r.get(k)).data() for k in r.keys('ticket_*') ]
	releasetickets.sort(key=lambda rt: rt['version'], reverse=True)
	return json.dumps(releasetickets)


@app.route("/all-pr.json")
def api_all_pr():
	requests = [ PullRequest(r.get(k)).data() for k in r.keys('*pr_*') ]
	requests.sort(key=lambda pr: pr['id'])
	return json.dumps(requests)


@app.route("/all/")
@app.route("/all/<path:filterval>")
def all(filterval=''):

	requests = [ PullRequest(r.get(k)) for k in r.keys('*pr_*') ]
	requests.sort(key=lambda pr: -pr.id)

	# Additional, get data for release tickets
	releasetickets = [ ReleaseTicket(r.get(k)) for k in r.keys('ticket_*') ]
	releasetickets.sort(key=lambda rt: rt.version, reverse=True)

	return render_template('home.html', requests=requests,
			releasetickets=releasetickets, filters=filters(filterval))


@app.route('/stats/')
@app.route('/stats/<int:month>')
def stats(month=0):
	auth = (request.authorization.username, request.authorization.password) \
			if request.authorization else None
	if auth != ('admin', 'opencast'):
		return Response('', 401,
				{'WWW-Authenticate': 'Basic realm="Login Required"'})
	# Get time barrier
	timebarrier = date.today() + relativedelta( months = -month )
	review_stats = {}
	pr_stats = {}
	user = {}
	for k in r.keys('*pr_*'):
		pr = PullRequest(r.get(k))
		if month and timebarrier > parse(pr.last_updated).date():
			continue
		if pr.reviewer_user:
			if pr.reviewer_name:
				user[pr.reviewer_user] = pr.reviewer_name
			review_stats[pr.reviewer_user] = review_stats.get(pr.reviewer_user, []) + [pr.id]
		if pr.author_user:
			if pr.author_name:
				user[pr.author_user] = pr.author_name
			pr_stats[pr.author_user] = pr_stats.get(pr.author_user, []) + [pr.id]

	# review_stats = [(reviewer, reviewer_name, n_reviews, [pr_id, ...]),...]
	review_stats = [ (k, user.get(k,k), len(v), [int(x) for x in v]) for k,v in review_stats.iteritems() ]
	pr_stats = [ (k, user.get(k,k), len(v), [int(x) for x in v]) for k,v in pr_stats.iteritems() ]

	# Sort by number of reviews
	review_stats.sort(key=lambda r: r[2])
	pr_stats.sort(key=lambda r: r[2])

	return render_template('stats.html', review_stats=review_stats, pr_stats=pr_stats)


if __name__ == "__main__":
	app.run(debug=True, port=5555)
