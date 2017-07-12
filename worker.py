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
import redis
from data import PullRequest, ReleaseTicket

try:
    r = redis.StrictRedis(host='localhost', db=0)
except AttributeError:
    r = redis.Redis(host='localhost', db=0)

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


    def get_reviewer(self, pr):

        url = '%s/%s/comments' % (apiurl, pr.id)
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
        comments.sort(key=lambda r: r.get('created_on'))

        pr.reviewer_name = None
        pr.reviewer_user = None

        # Start with last comment to get the last person taking up the job as
        # reviewer
        for c in comments[::-1]:
            if '//review//' in c['content']['raw']:
                pr.reviewer_name = c['user']['display_name']
                pr.reviewer_user = c['user']['username']
                pr.review_start  = c['updated_on']
                print 'Found reviewer for %s: %s' % (pr.id, pr.reviewer_name)
                break

        pr.active = True

        # We can stop here if there is no reviewer
        if not pr.reviewer_user:
            print 'Found no reviewer for %s' % pr.id
            return

        # Check if a pull request is active or on hold. If no //hold// can be
        # found, it's active by default.
        for c in comments[::-1]:
            # Only the official reviewer can put a pull request on hold. Skip all
            # other comments.
            if pr.reviewer_user != c['user']['username']:
                continue
            if '//resume//' in c['content']['raw']:
                break
            if '//hold//' in c['content']['raw']:
                pr.active = False
                break


    def update_pullrequest(self, req, force=False):
        pr = PullRequest(r.get('pr_%s' % req['id']))

        pr.author_name          = req['author'].get('display_name')
        pr.author_user          = req['author']['username']
        pr.created_date         = parse(req['created_on']).strftime('%Y-%m-%d')
        pr.created              = req['created_on']
        pr.destination          = req['destination']['branch']['name']
        pr.id                   = req['id']
        pr.source_branch        = req['source']['branch']['name']
        pr.source_repo          = (req['source'].get('repository') or {}).get('full_name')
        pr.title                = req['title']
        pr.url                  = req['links']['html']['href']
        pr.state                = req['state'].lower()

        # Check for reviewer if the pr was updated since last time
        if force or pr.last_updated != req.get('updated_on'):
            pr.last_updated = req.get('updated_on')
            self.get_reviewer(pr)

        # Update the approved state in any case
        try:
            self.get_approved(pr)
        except:
            pass

        # Store it in the redis db
        if pr.state == 'open':
            r.set('pr_%s' % pr.id, pr.json())
        else:
            r.set('done_pr_%s' % pr.id, pr.json())


    def get_approved(self, pr):
        url = '%s/%s' % (apiurl, pr.id)

        u = urllib2.urlopen(urllib2.Request(url))
        try:
            data = json.loads(u.read())
        finally:
            u.close()

        pr.approved_by = [ p['user']['username'] for p in data['participants'] if p['approved'] ]
        pr.approved_by_reviewer = pr.reviewer_user in pr.approved_by
        if pr.approved_by:
            print 'Pull Request #%s was approved by: %s' %(pr.id, pr.approved_by)

    def get_release_tickets(self):
        url = 'https://opencast.jira.com/rest/api/2/search' \
              + '?jql=summary%20~%20%22Merge%20the%20result%20of%20the%20current%20peer%20review%20to%22%20AND%20status%20%3D%20Open'
        u = urllib2.urlopen(urllib2.Request(url))
        keys = []
        try:
            data = json.loads(u.read())
            for issue in data.get('issues', []):
                keys.append(issue.get('key'))
        except Exception:
            pass
        return keys


    def worker(self):
        requests = []

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
                sys.stderr.write(' --> %s' % e)

        # Get active pull requests from database
        active_pr = set(r.keys('pr_*'))

        # Add reviewer
        for req in requests:
            self.update_pullrequest(req)
            # Remove still active PR from list
            try:
                active_pr.remove('pr_%s' % req['id'])
            except:
                pass

        # Set old PRs to inactive
        for key in active_pr:
            r.rename(key, 'done_%s' % key)


        # Finally try to get the release tickets:
        releasetickets = self.get_release_tickets()
        # Delete old keys
        for key in r.keys('ticket_*'):
            if not key.split('_', 1)[-1] in releasetickets:
                r.delete(key)
        for t in releasetickets:
            nexturl = 'https://opencast.jira.com/rest/api/2/issue/%s?expand=changelog' % t
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
                rt = ReleaseTicket(
                        url='https://opencast.jira.com/browse/%s' % t,
                        version=data['fixVersions'][0]['name'] if data['fixVersions'] else '',
                        last_changed=lastchanged,
                        assignee=data['assignee'].get('displayName') if data.get('assignee') else ''
                    )
                r.set('ticket_%s' % t, rt.json())
            except Exception as e:
                sys.stderr.write('Error: Could not get release ticket (MH-%s)' % t)
                sys.stderr.write(' --> %s' % e.message)
            finally:
                u.close()


    def update_pullrequest_id(self, i, force=False):
        u = urllib2.urlopen(urllib2.Request('%s/%s' % (apiurl, i)))
        req = json.loads(u.read())
        u.close()
        self.update_pullrequest(req, force)


    def complete_db(self):
        i = 1
        try:
            while True:
                print 'Pull Request #%i' % i
                self.update_pullrequest_id(i)
                i += 1
        except:
            pass


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
        try:
            w.update_pullrequest_id(int(sys.argv[1]), True)
        except:
            w.worker()
        exit()
