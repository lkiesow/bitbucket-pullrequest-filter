#!/bin/env python
# -*- coding: utf-8 -*-

# Set default encoding to UTF-8
import sys
reload(sys)
sys.setdefaultencoding('utf8')

import time, datetime, pytz
import daemon
import signal, errno
from daemon import runner
import urllib2
import json
import os
from pprint import pprint
from dateutil.parser import parse
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


#############################################################################
## Worker to regularly update the list
#############################################################################


def start_worker():
	sys.argv = [ sys.argv[0], 'start' ]
	try:
		daemon_runner = runner.DaemonRunner(Worker())
		daemon_runner.do_action()
	except daemon.runner.DaemonRunnerStartFailureError:
		pass


class Worker():

	path = os.path.dirname(os.path.realpath(__file__))

	def __init__(self):
		self.stdin_path = '/dev/null'
		self.stdout_path = '/dev/null'
		self.stderr_path = '/dev/null'
		self.pidfile_path =  '%s/bbprf-worker.pid' % self.path
		self.pidfile_timeout = 0


	def get_reviewer(self, req, rev):

		id = str(req['id'])
		url = 'https://bitbucket.org/api/2.0/repositories/opencast-community/matterhorn/pullrequests/%s/comments' % id
		comments = []

		while url:
			u = urllib2.urlopen(urllib2.Request(url))
			try:
				data = json.loads(u.read())
				comments += data.get('values') or []
				url = data.get('next')
			finally:
				u.close()

		# Make sure revies are sorted by date
		comments = data.get('values') or []
		comments.sort(key=lambda r: r.get('created_on'))

		# Start with last comment to get the last person taking up the job as
		# reviewer
		for c in comments[::-1]:
			if '//review//' in c['content']['raw']:
				n = c['user']['display_name']
				u = c['user']['username']
				#print 'Found reviewer for %s: %s' % (id, n)
				rev['name'] = n
				rev['user'] = u
				req[u'reviewer'] = n
				req[u'reviewer_user'] = u
				return


	def get_approved(self, req, rev):
		id = str(req['id'])
		url = 'https://bitbucket.org/api/2.0/repositories/opencast-community/matterhorn/pullrequests/%s' % id

		u = urllib2.urlopen(urllib2.Request(url))
		try:
			data = json.loads(u.read())
		finally:
			u.close()

		req[u'approved'] = [ p['user']['username'] for p in data['participants'] if p['approved'] ]
		rev['approved']  = req[u'approved']
		req[u'approved_by_reviewer'] = req.get('reviewer_user') in rev['approved']
		rev[u'approved_by_reviewer'] = req[u'approved_by_reviewer']


	def load_reviewer(self):
		try:
			with open('%s/reviewers.json' % self.path, 'r') as f:
				reviewers = json.loads(f.read())
		except:
			return {}
		return reviewers


	def save_reviewer(self, reviewers):
		try:
			with open('%s/reviewers.json' % self.path, 'w') as f:
				f.write(json.dumps(reviewers, sort_keys=True))
		except:
			pass


	def worker(self):
		requests = []
		reviewers = self.load_reviewer()

		nexturl = 'https://bitbucket.org/api/2.0/repositories/opencast-community/matterhorn/pullrequests?pagelen=25'

		while nexturl:
			#print 'Requesting data from %s' % nexturl
			u = urllib2.urlopen(urllib2.Request(nexturl))
			try:
				data = json.loads(u.read())
				requests += data.get('values') or []
				nexturl = data.get('next')
			finally:
				u.close()

		# Add reviewer
		for req in requests:
			rev = reviewers.get(str(req['id'])) or {}

			if req.get('updated_on') != rev.get('last_updated'):
				reviewers[str(req['id'])] = rev
				rev['last_updated'] = req.get('updated_on')
				self.get_reviewer(req, rev)
				self.get_approved(req, rev)
				print req['id'], req['approved']

			elif rev.get('name'):
				req[u'reviewer']             = rev['name']
				req[u'reviewer_user']        = rev['user']
				req['approved']              = rev[u'approved']
				req[u'approved_by_reviewer'] = rev[u'approved_by_reviewer']

			req['created_on_fmt'] = parse(req['created_on']).strftime('%Y-%m-%d')
		self.save_reviewer(reviewers)


		# Sort by id
		requests.sort(key=lambda r: r.get('id'))

		try:
			with open('%s/pullrequests.tmp' % self.path, 'w') as f:
				f.write(json.dumps(requests, sort_keys=True))
			os.rename('%s/pullrequests.tmp' % self.path, '%s/pullrequests.json' % self.path)
		except:
			pass

		# Finally try to get the release tickets:
		releasetickets = [10049, 10125]
		ticketdata = []
		for t in releasetickets:
			nexturl = 'https://opencast.jira.com/rest/api/2/issue/MH-%i?expand=changelog' % t
			u = urllib2.urlopen(urllib2.Request(nexturl))
			try:
				data = json.loads(u.read())
				# try to find out when the last person was assigned:
				lastchanges = data['fields']['updated']
				for h in data['changelog']['histories'][::-1]:
					if [ True for i in h['items'] if i['field'] == 'assignee' ]:
						lastchanged = h['created']
						break
				data = data['fields']
				ticketdata.append({
					'version'           : data['fixVersions'][0]['name'] if data['fixVersions'] else '',
					'last-changed'      : parse(lastchanged).strftime('%Y-%m-%d %H:%M:%S'),
					'since-last-change' : (datetime.datetime.now(pytz.utc) - parse(lastchanged)).days,
					'assignee'          : data['assignee'].get('displayName') if data.get('assignee') else ''
					})
			except:
				pass
			finally:
				u.close()
		try:
			with open('%s/releasetickets.tmp' % self.path, 'w') as f:
				f.write(json.dumps(ticketdata, sort_keys=True))
			os.rename('%s/releasetickets.tmp' % self.path, '%s/releasetickets.json' % self.path)
		except:
			pass




	def complete_db(self, last):
		print 'Trying to fill the database'
		reviewers = {}
		# Add reviewer
		for i in xrange(last):
			if not i:
				continue
			print '\r#%i' % i,
			sys.stdout.flush()
			rev = {}
			req = { 'id' : i }
			reviewers[str(req['id'])] = rev
			self.get_reviewer(req, rev)
			self.get_approved(req, rev)
		print ''
		self.save_reviewer(reviewers)



	def server_alive(self):
		pid = None
		try:
			with open('%s/bbprf.pid' % self.path) as f:
				pid = int(f.read())
		except:
			pass
		if not pid:
			return False
		try:
			os.kill(pid, signal.SIG_DFL)
		except OSError, exc:
			if exc.errno == errno.ESRCH:
				# The specified PID does not exist
				return False
		return True


	def run(self):
		while True:
			try:
				self.worker()
			except:
				pass
			if not self.server_alive():
				exit()
			time.sleep(60)


# Make sure to spawn a worker
if sys.argv[1:] == []:
	os.system('python %s worker' % os.path.abspath(__file__))
	#os.spawnl(os.P_NOWAIT, 'python', [os.path.abspath(__file__), 'worker'])

if __name__ == "__main__":
	if sys.argv[1:] == ['complete-db']:
		w = Worker()
		w.complete_db(177)
		exit()
	if sys.argv[1:] == ['worker']:
		start_worker()
	else:
		with open('bbprf.pid', 'w') as f:
			f.write('%s' % os.getpid())
		app.run(debug=True)
