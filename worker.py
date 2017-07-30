#!/bin/env python
# -*- coding: utf-8 -*-

from data import PullRequest, ReleaseTicket
from dateutil.parser import parse
import config
import json
import logging
import redis
import sys
import urllib2

log = logging.getLogger("worker")
log.setLevel(logging.INFO)
log.addHandler(logging.StreamHandler(sys.stderr))

try:
    r = redis.StrictRedis(host='localhost', db=0)
except AttributeError:
    r = redis.Redis(host='localhost', db=0)

apiurl = 'https://bitbucket.org/api/2.0/repositories/%s/pullrequests' \
         % config.REPOSITORY
jiraapi = 'https://opencast.jira.com/rest/api/2/'


def get_release_tickets():
    url = jiraapi + 'search?jql=' \
          + 'summary ~ "Merge the result of the current peer review to" '\
          + 'AND resolution %3D Unresolved'
    url = url.replace(' ', '%20')
    u = urllib2.urlopen(urllib2.Request(url))
    keys = []
    try:
        data = json.loads(u.read())
        for issue in data.get('issues', []):
            keys.append(issue.get('key'))
    except Exception:
        pass
    return keys


def update_release_tickets():
    # Finally try to get the release tickets:
    releasetickets = get_release_tickets()
    log.info('Release tickets: %s' % releasetickets)
    # Delete old keys
    for key in r.keys('ticket_*'):
        if not key.split('_', 1)[-1] in releasetickets:
            r.delete(key)
    for t in releasetickets:
        url = jiraapi + 'issue/%s?expand=changelog' % t
        u = urllib2.urlopen(urllib2.Request(url))
        try:
            data = json.loads(u.read())
            # try to find out when the last person was assigned:
            for h in data['changelog']['histories'][::-1]:
                if [True for i in h['items'] if i['field'] == 'assignee']:
                    lastchanged = h['created']
                    break
            data = data['fields']
            rt = ReleaseTicket()
            rt.url = 'https://opencast.jira.com/browse/%s' % t,
            rt.version = (data['fixVersions']+[{}])[0].get('name', ''),
            rt.last_changed = lastchanged,
            rt.assignee = (data.get('assignee') or {}).get('displayName', '')
            r.set('ticket_%s' % t, rt.json())
        finally:
            u.close()


def get_reviewer(pr):
    '''Find reviewer in comments of Bitbucket pull request and update the pull
    request object passed to this function-

    :param pr: Pull request object to update
    '''
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

    # Make sure reviews are sorted by date
    comments.sort(key=lambda r: r.get('created_on'), reverse=True)

    # Start with last comment to get the last person taking up the job as
    # reviewer
    for c in comments:
        if '//review//' in c['content']['raw']:
            pr.reviewer_name = c['user']['display_name']
            pr.reviewer_user = c['user']['username']
            pr.review_start = c['updated_on']
            log.info('Found reviewer for %s: %s' % (pr.id, pr.reviewer_name))
            return

    pr.reviewer_name = None
    pr.reviewer_user = None
    log.info('Found no reviewer for %s' % pr.id)


def get_approved(pr):
    '''Request detailed pull request data and check if a pull request was
    approved by a participant.

    :param pr: PullRequest object
    '''
    url = '%s/%s' % (apiurl, pr.id)

    u = urllib2.urlopen(urllib2.Request(url))
    try:
        data = json.loads(u.read())
    finally:
        u.close()

    pr.approved_by = [p['user']['username']
                      for p in data['participants']
                      if p['approved']]
    pr.approved_by_reviewer = pr.reviewer_user in pr.approved_by
    if pr.approved_by:
        log.info('Pull Request #%s approved by: %s' % (pr.id, pr.approved_by))


def update_pull_request(req, force=False):
    '''Update a pull request in the redis database based on an entry of
    Bitbucket's list of open pull requests.

    :param req: Pull request data
    :param force: Update even if it seems up to date
    '''
    pr = PullRequest(r.get('pr_%s' % req['id']))

    log.debug(req['source'])
    pr.author_name = req['author'].get('display_name')
    pr.author_user = req['author'].get('username')
    pr.created_date = parse(req['created_on']).strftime('%Y-%m-%d')
    pr.created = req['created_on']
    pr.destination = req['destination']['branch']['name']
    pr.id = req['id']
    pr.source_branch = req['source']['branch']['name']
    pr.source_repo = (req['source'].get('repository') or {}).get('full_name')
    pr.title = req['title']
    pr.url = req['links']['html']['href']
    pr.state = req['state'].lower()

    # Check for reviewer if the pr was updated since last time
    if force or pr.last_updated != req.get('updated_on'):
        pr.last_updated = req.get('updated_on')
        get_reviewer(pr)

    # Update the approved state in any case
    get_approved(pr)

    # Store it in redis
    if pr.state == 'open':
        r.set('pr_%s' % pr.id, pr.json())
    else:
        r.set('done_pr_%s' % pr.id, pr.json())


def get_pull_requests():
    requests = []
    nexturl = '%s?pagelen=50' % apiurl

    while nexturl:
        log.debug('Requesting data from %s' % nexturl)
        try:
            u = urllib2.urlopen(urllib2.Request(nexturl))
            data = json.loads(u.read())
            requests += data.get('values', [])
            nexturl = data.get('next')
            u.close()
        except Exception as e:
            sys.stderr.write('Error: Could not get list of pull requests')
            sys.stderr.write(' --> %s' % e)
    return requests


def update_pull_requests(requests):
    '''Go through list of open pull requests retrieved from BitBucket and
    update the database with the new data.

    :param requests: Lift of open pull requests (parsed JSON)
    '''
    # Get active pull requests from database
    old_pr = set(r.keys('pr_*'))
    new_pr = set()

    # Add reviewer
    for req in requests:
        update_pull_request(req)
        new_pr.add('pr_%s' % req['id'])

    # Set old PRs to inactive
    for key in (old_pr - new_pr):
        r.rename(key, 'done_%s' % key)


def main():
    requests = get_pull_requests()
    update_pull_requests(requests)
    update_release_tickets()


def update_pullrequest_id(i, force=False):
    log.info('Updating pull request #%i' % i)
    u = urllib2.urlopen(urllib2.Request('%s/%s' % (apiurl, i)))
    req = json.loads(u.read())
    u.close()
    update_pull_request(req, force)


def complete_db():
    i = 1
    try:
        while True:
            update_pullrequest_id(i)
            i += 1
    except:
        pass


if __name__ == "__main__":
    if sys.argv[1:] == ['complete-db']:
        complete_db()
    elif sys.argv[1:] == []:
        main()
    else:
        update_pullrequest_id(int(sys.argv[1]), True)
