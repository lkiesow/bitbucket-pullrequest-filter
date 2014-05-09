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
from dateutil.parser import parse
import config

apiurl = 'https://bitbucket.org/api/2.0/repositories/%s/pullrequests' % config.REPOSITORY

def start_daemon():
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
		self.stdout_path = '%s/bbprf-worker.log' % self.path
		self.stderr_path = '%s/bbprf-worker.error' % self.path
		self.pidfile_path =  '%s/bbprf-worker.pid' % self.path
		self.pidfile_timeout = 0


	def get_reviewer(self, req, rev):

		id = str(req['id'])
		url = '%s/%s/comments' % (apiurl, id)
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
				print 'Found reviewer for %s: %s' % (id, n)
				rev['name'] = n
				rev['user'] = u
				req['reviewer'] = n
				req['reviewer_user'] = u
				break

		if not rev.get('user'):
			rev['active'] = True
			req['active'] = True
			return

		# Check if a pull request is active or on hold. If no //hold// can be
		# found, it's active by default.
		for c in comments[::-1]:
			# Only the official reviewer can put a pull request on hold. Ignore
			# all other comments.
			if rev['user'] != c['user']['username']:
				continue
			if '//resume//' in c['content']['raw']:
				break
			if '//hold//' in c['content']['raw']:
				active = False
				rev['active'] = False
				req['active'] = False
				break

		rev['active'] = True
		req['active'] = True



	def get_approved(self, req, rev):
		id = str(req['id'])
		url = '%s/%s' % (apiurl, id)

		u = urllib2.urlopen(urllib2.Request(url))
		try:
			data = json.loads(u.read())
		finally:
			u.close()

		req['approved'] = [ p['user']['username'] for p in data['participants'] if p['approved'] ]
		rev['approved'] = req['approved']
		req['approved_by_reviewer'] = req.get('reviewer_user') in rev['approved']
		rev['approved_by_reviewer'] = req['approved_by_reviewer']
		if req['approved']:
			print 'Pull Request #%s was approved by: %s' %(id, req['approved'])


	def load_reviewer(self):
		try:
			with open(config.REVIEWERS, 'r') as f:
				reviewers = json.loads(f.read())
		except:
			return {}
		return reviewers


	def save_reviewer(self, reviewers):
		try:
			with open(config.REVIEWERS, 'w') as f:
				f.write(json.dumps(reviewers, sort_keys=True))
		except:
			pass


	def worker(self):
		requests = []
		reviewers = self.load_reviewer()

		nexturl = '%s?pagelen=25' % apiurl

		while nexturl:
			#print 'Requesting data from %s' % nexturl
			try:
				u = urllib2.urlopen(urllib2.Request(nexturl))
				data = json.loads(u.read())
				requests += data.get('values') or []
				nexturl = data.get('next')
				u.close()
			except Exception as e:
				sys.stderr.write('Error: Could not get list of pull requests')
				sys.stderr.write(' --> %s' % e.message)

		# Add reviewer
		for req in requests:
			rev = reviewers.get(str(req['id'])) or {}
			req['active'] = True

			if req.get('updated_on') != rev.get('last_updated'):
				reviewers[str(req['id'])] = rev
				rev['last_updated'] = req.get('updated_on')
				self.get_reviewer(req, rev)

			elif rev.get('name'):
				req['reviewer']      = rev['name']
				req['reviewer_user'] = rev['user']
				req['active']        = rev['active']

			# Update the approved state in any case
			try:
				self.get_approved(req, rev)
			except:
				req['approved']              = rev['approved']
				req['approved_by_reviewer'] = rev['approved_by_reviewer']

			req['created_on_fmt'] = parse(req['created_on']).strftime('%Y-%m-%d')
		self.save_reviewer(reviewers)


		# Sort by id
		requests.sort(key=lambda r: r.get('id'))

		try:
			with open('%s.tmp' % config.PULLREQUESTS, 'w') as f:
				f.write(json.dumps(requests, sort_keys=True))
			os.rename('%s.tmp' % config.PULLREQUESTS, config.PULLREQUESTS)
		except Exception as e:
			sys.stderr.write('Error: Could not save pullrequests')
			sys.stderr.write(' --> %s' % e.message)

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
					'url'               : 'https://opencast.jira.com/browse/MH-%i' % t,
					'version'           : data['fixVersions'][0]['name'] if data['fixVersions'] else '',
					'last-changed'      : parse(lastchanged).strftime('%Y-%m-%d %H:%M:%S'),
					'since-last-change' : (datetime.datetime.now(pytz.utc) - parse(lastchanged)).days,
					'assignee'          : data['assignee'].get('displayName') if data.get('assignee') else ''
					})
			except Exception as e:
				sys.stderr.write('Error: Could not get release ticket (MH-%s)' % t)
				sys.stderr.write(' --> %s' % e.message)
			finally:
				u.close()
		try:
			with open('%s.tmp' % config.RELEASETICKETS, 'w') as f:
				f.write(json.dumps(ticketdata, sort_keys=True))
			os.rename('%s.tmp' % config.RELEASETICKETS, config.RELEASETICKETS)
		except Exception as e:
			sys.stderr.write('Error: Could not write releasetickets')
			sys.stderr.write(' --> %s' % e.message)




	def complete_db(self):
		print 'Getting pull requests id range'
		url = '%s?pagelen=1' % apiurl
		u = urllib2.urlopen(urllib2.Request(url))
		data = json.loads(u.read())
		u.close()
		last = data['values'][0]['id']

		print 'Getting data for reviews 0 to %s' % last
		reviewers = {}
		# Add reviewer
		for i in xrange(int(last)):
			if not i:
				continue
			rev = {}
			req = { 'id' : i }
			reviewers[str(req['id'])] = rev
			self.get_reviewer(req, rev)
			self.get_approved(req, rev)
		self.save_reviewer(reviewers)


	def run(self):
		while True:
			try:
				self.worker()
			except:
				pass
			time.sleep(60)


if __name__ == "__main__":
	if sys.argv[1:] == ['complete-db']:
		w = Worker()
		w.complete_db()
		exit()
	if sys.argv[1:] == ['daemon']:
		start_daemon()
	else:
		w = Worker()
		w.worker()
		exit()
